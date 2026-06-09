# 시스템 아키텍처

SmartFarm은 **온디바이스 촬영 → 서버 추론 → 구역별 모니터링**으로 이어지는 3계층 구조다.

## 데이터 흐름 (end-to-end)

```
[Android 앱]                  [FastAPI 백엔드]               [AI 모델]
 CameraWorker                  POST /analyze                 best_crop_model.onnx
 14:00 자동 촬영   ─multipart─▶ 이미지 수신 ─onnxruntime─▶  EfficientNet-B3
 (구역 A1~B4)                   softmax → 클래스/신뢰도         23-class logit
       ▲                            │
       │  fields / images           ▼
       │  notifications        [PostgreSQL]
       └───────────────────────  fields · images
          구역 현황/갤러리/알림    analysis_results · notifications
```

1. 앱의 `CameraWorker`(WorkManager)가 매일 14:00 구역별 사진을 찍어 `/analyze`에 업로드한다.
2. 백엔드가 ONNX(EfficientNet-B3)로 추론해 `disease_type`·`confidence`를 산출하고 4개 테이블에 적재한다.
3. 신뢰도가 임계치를 넘는 위험 판정은 `notifications`에 누적된다.
4. 앱은 `GET /fields`(구역 현황), `GET /images`(사진 기록), `GET /notifications`(알림)로 화면을 갱신한다.

## 계층별 책임

| 계층 | 위치 | 핵심 |
|------|------|------|
| AI 모델 | [`ai/`](../ai/README.md) | HSV 병반 크롭 전처리 → EfficientNet-B3 학습 → ONNX 변환 (Val Acc 95.30%) |
| 백엔드 | [`backend/`](../backend/README.md) | FastAPI 9 엔드포인트 + 서버 측 ONNX 추론 + PostgreSQL 4 테이블 |
| 모바일 | [`android/`](../android/README.md) | Retrofit 연동, 구역/갤러리/알림 3화면, 14:00 자동 촬영 |

## 추론 전처리 파이프라인

```
원본 잎 이미지
  → HSV Anomaly Score (Hue 이탈 ×1.0 + 채도 분산 ×0.4 + 텍스처 ×0.15)로 병반 70×70 크롭
  → 224×224 BICUBIC 업스케일
  → Normalize(ImageNet mean/std)
  → EfficientNet-B3 → 23-class softmax
```

## 분류 클래스 (23종)

| 작물 | 클래스 |
|------|--------|
| Potato | Early Blight / Late Blight / Healthy |
| Tomato | Bacterial Spot / Early Blight / Late Blight / Leaf Mold / Septoria / Spider Mites / Target Spot / Yellow Curl Virus / Mosaic / Healthy |
| Pepper | Bacterial Spot / Healthy |
| Apple | Scab / Black Rot / Cedar Rust / Healthy |
| Corn | Cercospora / Common Rust / Northern Blight / Healthy |

## 참고

- 모델 사양·재생성: [`ai/model/README.md`](../ai/model/README.md)
- 전처리·학습·검증 스크립트: [`ai/preprocessing/README.md`](../ai/preprocessing/README.md)
- 발표/보고서 자료 생성: [`report_assets/README.md`](../report_assets/README.md)
