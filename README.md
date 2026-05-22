# 비닐하우스 농장 질병 감지 AI 앱

모바일 카메라를 통한 실시간 잎 질병 감지 및 구역별 시각화 시스템

## 팀 구성

| 역할 | 인원 | 담당 |
|------|------|------|
| Android Developer | 2명 | UI/UX, 카메라/Bluetooth, 알림, API 클라이언트 |
| AI/ML Engineer | 1명 | 데이터 전처리, CNN 모델 학습, TFLite 변환 |

## 프로젝트 구조

```
greenhouse-disease-detection/
├── ai/                    # AI/ML (Python)
│   ├── preprocessing/     # 데이터 전처리 & 모델 학습
│   ├── inference/         # TFLite 변환 & 추론
│   └── models/            # 학습된 가중치 (gitignore)
├── android/               # Android 앱 (Java)
├── backend/               # REST API
└── docs/                  # 문서 & 설계도
```

## 기술 스택

- **모바일**: Android Studio, Java
- **AI**: Python, PyTorch (EfficientNet-B3), YOLOv8, TFLite
- **백엔드**: Python FastAPI / Node.js, PostgreSQL
- **통신**: Bluetooth, REST API

## AI 모델 성능

| 모델 | 학습 결과 |
|------|-----------|
| YOLOv8s | mAP50 = 0.994 (30 epochs) |
| EfficientNet-B3 | Val Acc > 98% (10 epochs) |

- 데이터셋: [New Plant Diseases Dataset](https://www.kaggle.com/datasets/vipoooool/new-plant-diseases-dataset)
- 클래스: 23종 (Potato, Tomato, Pepper, Apple, Corn 질병 + 정상)

## 빠른 시작

### AI 환경 설정
```bash
cd ai
pip install -r requirements.txt
python preprocessing/plant_disease_preprocessing.py
```

### 모델 변환 (TFLite)
```bash
python inference/convert_to_tflite.py
```

## 개발 일정

| 주차 | 주요 작업 |
|------|-----------|
| 1주 | 프로젝트 셋업, 기본 UI, AI 데이터 수집 |
| 2주 | 카메라/Bluetooth, API/DB 설계, 모델 학습 |
| 3주 | 통합 테스트, 버그 수정, 문서화 |

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | /analyze | 이미지 분석 & 결과 저장 |
| GET | /history | 분석 히스토리 조회 |
| GET | /status/:field | 구역별 상태 조회 |
