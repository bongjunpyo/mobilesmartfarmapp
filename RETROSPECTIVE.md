# RETROSPECTIVE — mobilesmartfarmapp (SmartFarm AI 병해진단)

## 목표

작물 잎 이미지에서 23개 병해/정상 클래스를 분류하는 모델을 만들고, 안드로이드 앱에
온디바이스(ONNX)로 탑재한다. 데이터셋은 Kaggle `new-plant-diseases-dataset` (약 87,000장).

## 기술 선택 이유

- **HSV Anomaly Score 크롭 → EfficientNet-B3**: 초기에는 YOLO로 병반 구역을 탐지하려 했으나
  (`yolo_crop_*` 실험 스크립트에 흔적), YOLO 의존성과 라벨링 부담을 없애기 위해 HSV 기반
  이상 점수로 병반 후보를 오려내는 방식으로 전환 (커밋 `85a2105` "replace old pipeline with
  color+texture crop + EfficientNet-B3 96.5% val acc").
- **EfficientNet-B3**: 정확도/파라미터 균형이 좋고 224² 입력에 적합. [확인 필요: B3 vs B0/B1
  비교를 실제로 돌렸는지, 아니면 정확도 우선으로 바로 B3 채택했는지]
- **ONNX**: 안드로이드 온디바이스 추론을 위해 `.pth` → `.onnx` 변환 (opset 17).

## 막힌 점과 해결

| 막힌 점 | 해결 |
|---|---|
| YOLO 기반 병반 탐지의 라벨링·의존성 부담 | HSV anomaly score 크롭으로 전환 — 라벨 없이 병반 후보 추출 |
| grid inference 기능 도입 시 회귀 발생 추정 | `5394ebb` Revert 후 `5a7edbb` Reapply — 되돌렸다 재적용한 이력 (원인은 [확인 필요]) |
| 검증 정확도(95.30%)와 실제 이미지 성능 괴리 | **이번 분석에서 정량화** — test_images 33장 실측 69.7%, Potato Early Blight recall 0.20 |

## 이번 분석에서 새로 드러난 것

`ai/analysis/confusion_analysis.py` 결과, 검증셋 고정확도가 실사용 성능을 과대평가하고 있었다.
핵심 원인 가설은 **train/serve 전처리 불일치** — 학습은 70×70 크롭, 추론 테스트는 잎 전체 리사이즈.
Early blight의 동심원 병반이 축소 시 뭉개져 다른 갈반병과 혼동된다. (상세: `ai/analysis/README.md`)

## 다시 한다면

1. **학습·서비스 전처리를 처음부터 통일**한다. 크롭으로 학습했으면 추론도 같은 크롭
   파이프라인을 태워야 검증 정확도가 실사용과 일치한다.
2. 검증셋뿐 아니라 **배포와 같은 조건의 holdout(잎 전체 이미지)을 상시 트래킹**한다.
   95%라는 숫자에 안심하지 않는다.
3. 병해→healthy 오답(놓친 병)을 별도 지표로 관리하고 recall 가중 손실을 초기부터 적용한다.
4. Revert/Reapply 같은 되돌림 이력은 커밋 메시지에 원인을 남긴다 — 사후 회고에서 추적 불가.
