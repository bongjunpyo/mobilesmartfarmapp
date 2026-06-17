# SmartFarm — 비닐하우스 식물 병해 진단 시스템

> EfficientNet-B3 기반 식물 잎 23종 병해 분류 AI 모델 + FastAPI 백엔드 + 안드로이드 모니터링 앱

**과목 산출물**
- 인공지능실습 — `스마트팜_AI_병해진단_최종보고서.docx`
- 모바일 프로그래밍 — `모바일프로그래밍_최종발표.pptx`

> 보고서/발표 파일은 `report_assets/` 스크립트로 생성하며, 대용량 바이너리라 저장소에는 포함하지 않는다.

---

## 팀 구성

| 이름 | 직책 | 담당 |
|------|------|------|
| 봉준표 | 팀장 | AI 모델 학습 (EfficientNet-B3), Android↔AI 연동, 프로젝트 설계 |
| 이동제 | 팀원 | 백엔드 개발, 프론트엔드 수정, DB 수정 |
| 유광현 | 팀원 | DB 구성, FastAPI 연동 |
| 최성옥 | 팀원 | 앱 개발, 모니터링 화면 구현 |

> 모바일 프로그래밍 발표 PPT는 별도 팀(봉준표·이동제·윤준영) 산출물로 함께 보관됨.

---

## 시스템 아키텍처

> 데이터 흐름·계층별 책임 상세: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

```
┌──────────────────┐      multipart      ┌─────────────────────┐      ONNX      ┌──────────────────┐
│  Android 앱      │   ───────────────▶ │  FastAPI 백엔드      │ ──────────────▶ │ EfficientNet-B3  │
│  (Java)          │  /analyze          │  (uvicorn)          │  onnxruntime   │  (best_crop.onnx)│
│  구역·기록·알림  │ ◀─────────────────  │  9 endpoints        │ ◀──────────────  │  23 classes      │
└──────────────────┘   disease_type     └──────────┬──────────┘  softmax       └──────────────────┘
                       confidence                  │
                                                   ▼
                                         ┌─────────────────────┐
                                         │  PostgreSQL DB      │
                                         │  4 tables           │
                                         │  fields/images/     │
                                         │  analysis/notifs    │
                                         └─────────────────────┘
```

> 추론은 **서버사이드**(앱이 이미지를 `/analyze`로 전송 → 백엔드가 ONNX 추론)가 기본 경로다.
> 온디바이스 추론(`android/PlantDiseaseClassifier.java` + onnxruntime-android)은 대체/실험 경로로만 남겨 둔다.

---

## 프로젝트 구조

```
mobilesmartfarmapp/
├── ai/                                 # AI 모듈 (Python)
│   ├── README.md                       # 전체 파이프라인 문서
│   ├── requirements.txt
│   ├── model/                          # best_crop_model.onnx (~41 MB) + README
│   ├── preprocessing/                  # 전처리·학습·검증 스크립트 5종
│   │   ├── precompute_crops.py                 # HSV Anomaly 70×70 크롭 (최종)
│   │   ├── yolo_crop_efficientnet_accuracy.py  # EfficientNet-B3 학습
│   │   ├── yolo_crop_quality_check.py          # YOLO 화질 검증 (실험)
│   │   ├── yolo_crop_visualization.py          # YOLO 타일 시각화 (실험)
│   │   └── disease_region_test.py              # GradCAM 검증
│   └── test_images/                    # 검증용 잎 이미지 53장 (단일 잎 33 + 광각 wide/ 20)
├── android/                            # Android Studio 프로젝트 (Java + Gradle)
│   ├── README.md                       # 앱 구조 + 빌드/연동
│   ├── PlantDiseaseClassifier.java     # (대체) 온디바이스 ONNX 추론 클래스
│   ├── build.gradle · settings.gradle · gradlew
│   └── app/
│       ├── build.gradle                # Retrofit·CameraX·WorkManager·Glide
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── res/
│           └── java/com/example/smartfarm/
│               ├── SplashActivity.java · MainActivity.java
│               └── network/ · model/ · repository/ · ui/ · worker/
├── backend/                            # FastAPI 백엔드 (별도 디렉토리에서 운영)
│   └── README.md                       # API 스펙 + DB 스키마
├── docs/
│   └── ARCHITECTURE.md                 # 시스템 아키텍처 · 데이터 흐름
├── report_assets/                      # 발표/보고서 생성 스크립트 + 산출 이미지
│   ├── _gen_diagrams.py · _gen_inference.py · _gen_ui_mockup.py
│   ├── _gen_docx.py · _gen_pptx.py
│   └── *.png                           # architecture/training_curve/data_pipeline/ui_* 등
└── README.md

# 보고서(.docx)·발표(.pptx)는 report_assets 스크립트로 생성하며 git 미추적 (대용량 바이너리)
```

---

## 기술 스택

| 영역 | 사용 기술 |
|------|----------|
| AI | Python 3.14, PyTorch (Apple MPS), torchvision, kagglehub, onnxruntime |
| 모델 | EfficientNet-B3 (ImageNet pretrained → 23-class transfer learning) |
| 전처리 | HSV Anomaly Score (Hue 이탈 × 1.0 + 채도 분산 × 0.4 + 텍스처 × 0.15) |
| 백엔드 | Python FastAPI, uvicorn, SQLAlchemy (async) |
| DB | PostgreSQL 16 — fields · images · analysis_results · notifications |
| 모바일 | Android Studio, Java, CameraX, WorkManager, Retrofit/OkHttp, Glide, Material Design |
| 통신 | REST API, multipart/form-data, Push Notification |

---

## AI 모델 학습 결과

| 항목 | 값 |
|------|----|
| 데이터셋 | Kaggle [New Plant Diseases Dataset](https://www.kaggle.com/datasets/vipoooool/new-plant-diseases-dataset) (87,000장) |
| 클래스 | 23종 (감자 3 / 토마토 10 / 피망 2 / 사과 4 / 옥수수 4) |
| 모델 | EfficientNet-B3 + Dropout(0.3) + Linear(1536 → 23) |
| 학습 | AdamW (lr 1e-4) · CosineLR · 10 epoch · batch 32 |
| Train / Val | 20,000장 / 4,000장 (HSV 전처리 통과분) |
| **Best Val Accuracy** | **95.30%** |
| Val Loss | 0.16 |
| Train/Val Gap | 0.2%p (과적합 없음) |
| 배포 모델 | `best_crop_model.onnx` (ONNX opset 17, ~41 MB) |

---

## 백엔드 API

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/analyze` | 이미지 업로드 → ONNX 추론 → DB 저장 |
| GET | `/fields` | 전체 구역 + 최신 분석 결과 조회 |
| GET | `/status/{field_id}` | 특정 구역 상태와 신뢰도 조회 |
| GET | `/images` | 촬영 이미지 목록 (사진 기록 화면용) |
| GET | `/history` | 구역별 분석 이력 시계열 |
| GET | `/notifications` | 위험 알림 목록 |
| PATCH | `/notifications/{id}/read` | 알림 읽음 처리 |
| POST | `/admin/run-daily-capture` | 하루 1회 촬영 트리거 (테스트용) |
| GET | `/health` | 헬스 체크 |

---

## 앱 주요 화면

1. **Splash** — SmartFarm 브랜딩 (`SplashActivity`, 런처 진입점)
2. **구역 현황** — 정상/위험/주의 카운트 + 카드뷰 (A1~B4)
3. **사진 기록** — 날짜·구역·질병 태그 필터링 갤러리
4. **알림** — 위험 임계치 초과 시 자동 누적

> 14:00 자동 촬영은 `worker/` 의 WorkManager(`CameraWorker`)가 처리하며, 부팅 후 `BootReceiver` 가 재등록한다.

---

## 빠른 시작

### AI 학습

```bash
cd ai
pip install -r requirements.txt

# 1) HSV 기반 70×70 크롭 캐시 생성
python preprocessing/precompute_crops.py

# 2) EfficientNet-B3 학습
python preprocessing/yolo_crop_efficientnet_accuracy.py

# 3) GradCAM 시각화 검증
python preprocessing/disease_region_test.py
```

### Android 앱

```
1) Android Studio 에서 android/ 열기
2) network/ApiClient.java 의 BASE_URL 을 백엔드 주소로 설정 (에뮬레이터 기본 http://10.0.2.2:8000/)
3) 실기기/에뮬레이터에서 실행 → Splash → 구역 현황
```

추론은 백엔드 `/analyze` 를 호출하는 서버사이드 방식이 기본이다.
온디바이스 ONNX 추론을 쓰려면 `android/PlantDiseaseClassifier.java` 와
`onnxruntime-android` 의존성을 추가한다 — 자세한 내용은 [`android/README.md`](android/README.md) 참고.

### 보고서/PPT 재생성

```bash
~/venv/bin/python report_assets/_gen_inference.py    # 추론 시각화
~/venv/bin/python report_assets/_gen_diagrams.py     # 다이어그램
~/venv/bin/python report_assets/_gen_docx.py         # 최종보고서.docx 빌드
~/venv/bin/python report_assets/_gen_pptx.py         # 발표.pptx 빌드
```

---

## 산출물

| 파일 | 과목 | 설명 |
|------|------|------|
| `스마트팜_AI_병해진단_최종보고서.docx` | 인공지능실습 | AI 중심 11장 챕터, 12개 그림 (캡처 9장 + 학습·추론·ERD) |
| `모바일프로그래밍_최종발표.pptx` | 모바일 프로그래밍 | 앱 중심 16 슬라이드, 실제 캡처 4종 + 사용 시나리오 |
| `ai/model/best_crop_model.onnx` | — | 학습 완료 모델 (Val Acc 95.30%) |

> `.docx` / `.pptx` 는 git 에 포함하지 않으며 `report_assets/` 스크립트로 재생성한다.

---

## 라이선스

본 프로젝트는 학교 과제 산출물입니다. 데이터셋은 Kaggle 원 라이선스(CC BY-SA 4.0)를 따릅니다.
