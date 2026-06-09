# 학습 모델

작물 질병 분류 모델의 ONNX 산출물 디렉토리.

| 파일 | 설명 |
|------|------|
| `best_crop_model.onnx` | EfficientNet-B3 학습 모델 (~41 MB, opset 17) |

## 모델 사양

| 항목 | 값 |
|------|----|
| 아키텍처 | EfficientNet-B3 (ImageNet pretrained) |
| 입력 | `input` — `[1, 3, 224, 224]` (RGB, ImageNet 정규화) |
| 출력 | `output` — `[1, 23]` (클래스 logit) |
| 클래스 수 | 23종 (`../README.md` 8절 참조) |
| Best Val Accuracy | 95.30% |

## 입력 전처리

```
70×70 병반 크롭 → 224×224 BICUBIC 업스케일
→ Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
```

## 재생성

```bash
# 1) crop_cache 생성 → 2) 학습 → 3) ONNX 변환
python ../preprocessing/precompute_crops.py
python ../preprocessing/yolo_crop_efficientnet_accuracy.py   # best_crop_model.pth
# ONNX 변환 스크립트는 ../README.md 7절 참조
```

## 사용처

- Android 온디바이스 추론: `../../android/PlantDiseaseClassifier.java`
- 검증/추론 갤러리 생성: `../../report_assets/_gen_inference.py`
