# AI 모듈

## 환경 설정

```bash
pip install -r requirements.txt
```

Kaggle 인증 필요: `~/.kaggle/kaggle.json`

## preprocessing/

### plant_disease_preprocessing.py
전체 ML 파이프라인 (EfficientNet-B3 + YOLOv8 동시 학습)

```
kagglehub 다운로드
→ PlantDiseaseDataset (PyTorch) + DataLoader
→ YOLO 데이터셋 빌드 (yolo_dataset/)
→ YOLOv8s 학습 (30 epochs, AdamW, mAP50=0.994)
→ EfficientNet-B3 학습 (10 epochs, AdamW, StepLR, 클래스 가중치 보정)
→ best_plant_model.pth 저장
```

**23개 클래스**: Potato(3), Tomato(10), Pepper(2), Apple(4), Corn(4)

**Transforms (Train)**:
- RandomCrop 224, HorizontalFlip, VerticalFlip, Rotation±15°
- ColorJitter (brightness/contrast/saturation 0.3, hue 0.1)
- Normalize(ImageNet mean/std)

### smartfarm_yolo.py
YOLOv8 단독 학습 + 슬라이딩 윈도우 추론

```
slice_image(tile=640, overlap=0.2)
→ infer_on_tiles → apply_nms(IoU=0.5)
→ draw_results → smartfarm_result.png
```

## 학습된 모델 (gitignore)

- `models/best_plant_model.pth` — EfficientNet-B3
- `runs/detect/runs/smartfarm/weights/best.pt` — YOLOv8s

## inference/ (TODO)

- `convert_to_tflite.py` — EfficientNet-B3 → TFLite (Android 온디바이스)
- `api_server.py` — FastAPI 분석 엔드포인트
