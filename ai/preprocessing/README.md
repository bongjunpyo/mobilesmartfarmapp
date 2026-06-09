# 전처리 · 학습 · 검증 스크립트

작물 질병 분류 파이프라인의 전 단계 스크립트. 상세 설명은 `../README.md` 4~6절 참조.

## 스크립트 목록

| 파일 | 단계 | 설명 |
|------|------|------|
| `precompute_crops.py` | 전처리 (최종) | HSV Anomaly Score 기반 병반 70×70 크롭 캐시 생성 |
| `yolo_crop_efficientnet_accuracy.py` | 학습 | EfficientNet-B3 학습 → `best_crop_model.pth` |
| `disease_region_test.py` | 검증 | GradCAM 판단 근거 열지도 시각화 |
| `yolo_crop_quality_check.py` | 실험 | YOLO 기반 크롭 PSNR 화질 검증 |
| `yolo_crop_visualization.py` | 실험 | YOLO 타일 선택 과정 시각화 |

> `yolo_crop_*.py` 2개는 1차 실험(YOLO 의존)이며, 최종 채택은 HSV 방식(`precompute_crops.py`)이다.

## 실행 순서

```bash
pip install -r ../requirements.txt        # Kaggle 인증(~/.kaggle/kaggle.json) 필요

python precompute_crops.py                 # crop_cache/ 생성 (.gitignore 제외)
python yolo_crop_efficientnet_accuracy.py  # best_crop_model.pth + 학습 곡선
python disease_region_test.py              # disease_region_test.png
```

## 출력물

| 스크립트 | 출력 |
|----------|------|
| `precompute_crops.py` | `crop_cache/{train,val}/{class}/*.jpg`, `metadata.json`, 샘플 시각화 |
| `yolo_crop_efficientnet_accuracy.py` | `best_crop_model.pth`, 학습 곡선 PNG |
| `disease_region_test.py` | `disease_region_test.png` |
| `yolo_crop_quality_check.py` | `yolo_crop_quality_check.png` |
| `yolo_crop_visualization.py` | `yolo_crop_visualization.png` |

> `crop_cache/` 와 PNG 산출물은 용량 문제로 `.gitignore` 처리됨.
