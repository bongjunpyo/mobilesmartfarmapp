# 오분류 분석 (Misclassification Analysis)

`best_crop_model.onnx`(EfficientNet-B3, Val Acc 95.30%)가 실제 `test_images/`에서
어떤 병끼리 혼동하는지, 그 원인이 무엇인지 분석한다.

## 실행

```bash
~/venv/bin/python confusion_analysis.py
```

의존성: `onnxruntime`, `numpy`, `Pillow`, `matplotlib` (PyTorch 불필요).
입력 전처리는 학습 스크립트(`../preprocessing/yolo_crop_efficientnet_accuracy.py`)와 동일 —
224×224 BICUBIC 리사이즈 → [0,1] → ImageNet MEAN/STD 정규화.

## 산출물

| 파일 | 내용 |
|---|---|
| `confusion_matrix.png` | 혼동행렬 히트맵 |
| `class_metrics.csv` | 클래스별 support/precision/recall/F1 |
| `RESULTS.md` | 전체 예측 로그 + 오분류 사례 표 (자동 생성) |

## 결과 요약

- 대상: `test_images/` 라벨 이미지 **33장** (8개 클래스에 분포)
- 전체 정확도: **23/33 = 69.7%**

Val Accuracy 95.30% 대비 큰 폭으로 떨어진다. 검증셋(crop_cache의 70×70 크롭)과
test_images(원본 잎 전체)의 **분포가 다르기 때문**이며, 이 격차 자체가 핵심 발견이다.

### 클래스별 recall (support ≥ 1)

| 클래스 | recall | 관찰 |
|---|---|---|
| Potato Early Blight | 0.20 (1/5) | **가장 심각** — 4장이 서로 다른 클래스로 흩어짐 |
| Apple Scab | 0.33 (1/3) | Cedar rust·healthy로 혼동 |
| Tomato Early Blight | 0.50 (3/6) | Bacterial spot·mosaic virus로 혼동 |
| Tomato Healthy | 0.75 (3/4) | 1장이 Apple healthy로 |
| Cedar apple rust | 1.00 (4/4) | — |
| Corn Common Rust | 1.00 (3/3) | — |
| Potato Healthy | 1.00 (2/2) | — |
| Tomato Yellow Leaf Curl Virus | 1.00 (6/6) | — |

## 어떤 병끼리 혼동되는가 + 원인 가설

**1. Potato Early Blight → Pepper/Apple 계열로 붕괴 (recall 0.20)**
- `PotatoEarlyBlight4`는 Pepper Bacterial spot으로 **확신도 0.91**, `PotatoEarlyBlight3`는
  Apple healthy로 0.77. 높은 확신도의 오답 = 모델이 자신 있게 틀리는 상태.
- 가설: 학습은 잎에서 병반만 오려낸 **70×70 HSV-anomaly 크롭**으로 이뤄졌는데, test 이미지는
  **잎 전체를 224로 리사이즈**한다. Early blight의 동심원(target) 병반이 전체 잎 축소 시
  뭉개져, 갈색 반점이라는 저수준 색상 신호만 남아 다른 갈반병과 섞인다.

**2. Apple Scab ↔ Cedar apple rust / healthy**
- Scab의 어두운 병반과 Cedar rust의 주황 병반은 색이 다르지만, `AppleScab3`은 healthy로
  0.49(낮은 확신도)로 갈려 병반이 작을 때 배경 잎에 묻히는 문제로 보인다.

**3. Tomato Early Blight → Bacterial spot / mosaic virus**
- 토마토 잎의 반점성 병해끼리 서로 근접. `TomatoEarlyBlight6`이 Bacterial spot으로 0.90 —
  반점 크기·분포가 유사한 병해 간 경계가 학습 크롭 단위에서 흐려짐.

**4. healthy 클래스로의 오답**
- Potato/Tomato의 병든 잎이 healthy로 넘어가는 사례 존재 → false negative(놓친 병).
  농업 적용에서 가장 비용이 큰 오류 유형이므로 우선 개선 대상.

## 개선 방향

1. **train/serve 전처리 일치**: 서비스가 잎 전체 이미지를 받는다면, 학습도 크롭이 아닌
   잎 전체(또는 동일 크롭 파이프라인을 추론에도 적용)로 맞춘다. 현재 최대 격차 원인.
2. 반점성 병해(Early blight/Bacterial spot/Septoria)에 **hard-negative 위주 증강**.
3. healthy로의 false negative를 줄이기 위해 병해 클래스에 **recall 가중 손실** 적용.
4. test_images 표본이 33장으로 작으므로, 검증셋 홀드아웃으로 지표를 재확인 후 결론 확정.
