# AI 모듈

> 스마트팜 질병 감지 시스템 — 작물 질병 분류 AI  
> 작성자: 봉준표 | 최종 수정: 2026-05-29

---

## 목차

1. [파이프라인 개요](#1-파이프라인-개요)
2. [디렉토리 구조](#2-디렉토리-구조)
3. [환경 설정](#3-환경-설정)
4. [전처리](#4-전처리)
   - 4.1 [1차: YOLO 기반 병반 탐지 (실험)](#41-1차-yolo-기반-병반-탐지-실험)
   - 4.2 [2차: HSV Anomaly Score 기반 탐지 (최종)](#42-2차-hsv-anomaly-score-기반-탐지-최종)
5. [모델 학습](#5-모델-학습)
6. [모델 검증 (GradCAM)](#6-모델-검증-gradcam)
7. [학습 결과](#7-학습-결과)
8. [분류 클래스 (23개)](#8-분류-클래스-23개)
9. [Android 연동](#9-android-연동)

---

## 1. 파이프라인 개요

```
Kaggle 데이터셋 다운로드  (87,000장 / 23클래스)
        │
        ▼
[1차 실험] YOLO 기반 병반 구역 탐지
  yolo_crop_quality_check.py    ← PSNR 화질 검증
  yolo_crop_visualization.py   ← 타일 선택 과정 시각화
        │
        ▼ (YOLO 의존성 제거 → HSV 방식으로 전환)
        │
[최종 채택] HSV Anomaly Score 기반 병반 탐지
  precompute_crops.py           ← 70×70 크롭 캐시 생성
        │
        ▼
EfficientNet-B3 학습
  yolo_crop_efficientnet_accuracy.py
        │
        ▼
  best_crop_model.pth  →  best_crop_model.onnx  (~41 MB)
        │
        ▼
GradCAM 검증
  disease_region_test.py        ← 판단 근거 열지도 시각화
        │
        ▼
Android 연동
  ../android/PlantDiseaseClassifier.java
```

---

## 2. 디렉토리 구조

```
ai/
├── README.md
├── requirements.txt
├── model/
│   └── best_crop_model.onnx          # 학습된 ONNX 모델 (~41 MB)
├── preprocessing/
│   ├── precompute_crops.py           # HSV 기반 전처리 (최종)
│   ├── yolo_crop_quality_check.py    # YOLO 기반 화질 검증 (실험)
│   ├── yolo_crop_visualization.py    # YOLO 타일 시각화 (실험)
│   ├── yolo_crop_efficientnet_accuracy.py  # EfficientNet-B3 학습
│   └── disease_region_test.py        # GradCAM 검증
└── test_images/                      # 테스트용 이미지 33장
    ├── AppleCedarRust1~4.JPG
    ├── AppleScab1~3.JPG
    ├── CornCommonRust1~3.JPG
    ├── PotatoEarlyBlight1~5.JPG
    ├── PotatoHealthy1~2.JPG
    ├── TomatoEarlyBlight1~6.JPG
    ├── TomatoHealthy1~4.JPG
    ├── TomatoYellowCurlVirus1~6.JPG
    └── wide/
```

---

## 3. 환경 설정

```bash
pip install -r requirements.txt
```

**requirements.txt 주요 패키지**

| 패키지 | 용도 |
|--------|------|
| `torch` / `torchvision` | EfficientNet-B3 학습 (Apple MPS) |
| `ultralytics` | YOLOv8s 탐지 (실험용) |
| `opencv-python` | HSV 분석, 타일 분할 |
| `kagglehub` | 데이터셋 자동 다운로드 |
| `onnxruntime` | ONNX 추론 검증 |

**Kaggle 인증** — `~/.kaggle/kaggle.json` 필요

```json
{"username": "...", "key": "..."}
```

**디바이스**: Apple Silicon MPS (`torch.device("mps")`)  
**데이터셋**: `kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset")` 자동 캐시

---

## 4. 전처리

### 4.1 1차: YOLO 기반 병반 탐지 (실험)

> 파일: `preprocessing/yolo_crop_quality_check.py` · `yolo_crop_visualization.py`

학습된 YOLOv8s 모델(`best.pt`, mAP50=0.994)로 128×128 슬라이딩 윈도우 타일별 confidence를 측정해 병반 구역을 선택한다.

**처리 흐름**

```
이미지 입력
  → slice_image(tile=128, overlap=25%)   # 타일 분할
  → is_background() 필터                 # HSV 기반 배경 제거 (BG > 30%)
  → YOLOv8s 추론 (conf=0.10)
  → confidence 최고 타일 선택
  → 70×70 리사이즈 (cv2.INTER_CUBIC)
  → PSNR 화질 검증 (≥30dB = 고화질)
```

**타일 색상 의미 (yolo_crop_visualization)**

| 색상 | 의미 |
|------|------|
| 🟢 초록 | 선택된 병반 구역 (confidence 최고) |
| 🟡 노란 | 배경 필터 통과, 미선택 |
| 🔴 빨간 | 배경으로 판별되어 제거 |

**실행**

```bash
# YOLO 가중치 경로: runs/detect/runs/smartfarm/weights/best.pt
python preprocessing/yolo_crop_quality_check.py
# 출력: yolo_crop_quality_check.png (PSNR 분석 시각화)

python preprocessing/yolo_crop_visualization.py
# 출력: yolo_crop_visualization.png (타일 선택 과정 시각화)
```

---

### 4.2 2차: HSV Anomaly Score 기반 탐지 (최종)

> 파일: `preprocessing/precompute_crops.py`

YOLO 의존성을 제거하고 HSV 색공간의 이상 점수로 병반 구역을 선택한다.  
건강한 잎(H≈75, 녹색)에서 얼마나 벗어났는지를 3가지 지표로 측정한다.

**Anomaly Score 계산**

| 지표 | 수식 | 가중치 | 병반 시 특징 |
|------|------|--------|-------------|
| Hue 이탈 | `mean(|H − 75|)` | ×1.0 | 갈변·녹반점으로 Hue 편차 증가 |
| 채도 분산 | `√Var(S)` | ×0.4 | 경계 생성 시 채도 불균일 |
| 텍스처 | `√Var(Laplacian)`, clip=120 | ×0.15 | 병변으로 표면 복잡도 증가 |

```
Anomaly Score = Hue이탈×1.0 + 채도분산×0.4 + 텍스처×0.15
```

**처리 흐름**

```
이미지 입력
  → slice_image(tile=128, overlap=25%)
  → is_background() 필터 (S<30 & (V<60 or V>200) > 30%)
  → anomaly_score() 계산
  → 최고 점수 타일 선택 → 70×70 크롭 저장
  → crop_cache/{train,val}/{class}/ 저장
  → metadata.json (박스 좌표 + score)
```

**실행**

```bash
python preprocessing/precompute_crops.py
# 출력:
#   crop_cache/train/{class}/*.jpg  (20,000장)
#   crop_cache/val/{class}/*.jpg    (4,000장)
#   crop_cache/metadata.json
#   precompute_crops_sample.png     (샘플 시각화)
```

> **참고**: crop_cache/ 디렉토리는 `.gitignore`에 포함됨 (용량 문제)

---

## 5. 모델 학습

> 파일: `preprocessing/yolo_crop_efficientnet_accuracy.py`

`precompute_crops.py`로 생성한 crop_cache를 입력으로 EfficientNet-B3를 학습한다.

**모델 구조**

```
EfficientNet-B3 (ImageNet pretrained)
  └─ classifier
       ├─ Dropout(p=0.3)
       └─ Linear(1536 → 23)
```

**학습 설정**

| 항목 | 값 |
|------|----|
| Optimizer | AdamW (lr=1e-4, weight_decay=0.01) |
| Scheduler | CosineAnnealingLR (T_max=10, eta_min=1e-6) |
| Loss | CrossEntropyLoss (클래스 불균형 역수 가중치) |
| Epochs | 10 |
| Batch Size | 32 |
| Train 샘플 | 20,000장 |
| Val 샘플 | 4,000장 |
| 입력 크기 | 224×224 (70×70 크롭 BICUBIC 업스케일) |

**Augmentation (Train)**

```python
RandomHorizontalFlip(0.5)
RandomVerticalFlip(0.2)
RandomRotation(15)
ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1)
Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
```

**실행**

```bash
# crop_cache/ 생성 후 실행
python preprocessing/yolo_crop_efficientnet_accuracy.py
# 출력:
#   best_crop_model.pth               (최고 val accuracy 모델)
#   yolo_crop_efficientnet_accuracy.png (학습 곡선)
```

---

## 6. 모델 검증 (GradCAM)

> 파일: `preprocessing/disease_region_test.py`

GradCAM (Gradient-weighted Class Activation Mapping)으로 모델이 어느 영역을 보고 질병/건강을 판단하는지 검증한다.

- **타깃 레이어**: `model.features[-1]` (EfficientNet-B3 마지막 특징 블록)
- **입력**: `best_crop_model.pth` + Kaggle 검증 데이터
- **출력**: 질병 잎 / 건강 잎 각 6장 × (원본 + GradCAM 오버레이)

```
빨간·노란 영역  →  모델이 집중한 핵심 판단 근거 (고활성)
파란 영역       →  판단에 거의 영향 없음 (저활성)
초록 테두리     →  정답  |  빨간 테두리 →  오답
```

**실행**

```bash
python preprocessing/disease_region_test.py
# 출력: disease_region_test.png
```

---

## 7. 학습 결과

| 지표 | 값 |
|------|----|
| Best Val Accuracy | **95.30%** |
| 학습 Epoch | 10 |
| 모델 파일 | `best_crop_model.pth` |
| ONNX 변환 | `model/best_crop_model.onnx` (~41 MB) |

**ONNX 변환 명령 (참고)**

```python
import torch
from torchvision.models import efficientnet_b3
import torch.nn as nn

model = efficientnet_b3(weights=None)
model.classifier[1] = nn.Sequential(
    nn.Dropout(0.3, inplace=True),
    nn.Linear(model.classifier[1].in_features, 23),
)
model.load_state_dict(torch.load("best_crop_model.pth", map_location="cpu"))
model.eval()

dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy, "model/best_crop_model.onnx",
                  input_names=["input"], output_names=["output"],
                  opset_version=17)
```

---

## 8. 분류 클래스 (23개)

| 작물 | 클래스 수 | 클래스 목록 |
|------|----------|------------|
| 감자 (Potato) | 3 | Early Blight / Late Blight / Healthy |
| 토마토 (Tomato) | 10 | Bacterial Spot / Early Blight / Late Blight / Leaf Mold / Septoria / Spider Mites / Target Spot / YLCV / Mosaic / Healthy |
| 피망 (Pepper) | 2 | Bacterial Spot / Healthy |
| 사과 (Apple) | 4 | Apple Scab / Black Rot / Cedar Apple Rust / Healthy |
| 옥수수 (Corn) | 4 | Cercospora / Common Rust / Northern Leaf Blight / Healthy |

---

## 9. Android 연동

> 파일: `../android/PlantDiseaseClassifier.java`  
> 모델: `model/best_crop_model.onnx` → `app/src/main/assets/`

**의존성 추가 (build.gradle)**

```groovy
implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'
```

**사용 예시**

```java
// 초기화
PlantDiseaseClassifier classifier = new PlantDiseaseClassifier(context);

// 단일 추론
PlantDiseaseClassifier.Result r = classifier.predict(bitmap);
// r.label       → "Tomato: Early Blight"
// r.confidence  → 0.955  (95.5%)
// r.isHealthy   → false

// 그리드 추론 (20×20 격자로 병반 위치 파악)
PlantDiseaseClassifier.GridResult g = classifier.predictGrid(bitmap, 20);
Bitmap overlay = g.drawOverlay(bitmap);   // 병해=빨강, 건강=초록 오버레이
float ratio = g.diseaseRatio();           // 병해 셀 비율

// 해제
classifier.close();
```

**테스트 이미지 에뮬레이터 전송**

```bash
adb push ai/test_images/ /sdcard/Pictures/SmartFarm_Test/
```
