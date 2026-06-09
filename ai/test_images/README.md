# 테스트 이미지

모델 추론 검증용 작물 잎 이미지. Kaggle `new-plant-diseases-dataset` 검증셋에서 선별.

## 구성

| 분류 | 장수 | 파일 |
|------|------|------|
| Apple Cedar Rust | 4 | `AppleCedarRust1~4.JPG` |
| Apple Scab | 3 | `AppleScab1~3.JPG` |
| Corn Common Rust | 3 | `CornCommonRust1~3.JPG` |
| Potato Early Blight | 5 | `PotatoEarlyBlight1~5.JPG` |
| Potato Healthy | 2 | `PotatoHealthy1~2.JPG` |
| Tomato Early Blight | 6 | `TomatoEarlyBlight1~6.JPG` |
| Tomato Healthy | 4 | `TomatoHealthy1~4.JPG` |
| Tomato Yellow Curl Virus | 6 | `TomatoYellowCurlVirus1~6.JPG` |
| 광각 샘플 | — | `wide/` |

> `wide/` 는 단일 잎이 아닌 넓은 화각 이미지로, 그리드 추론(`predictGrid`) 검증용.

## 활용

```bash
# 추론 갤러리 / 그리드 오버레이 생성
python ../../report_assets/_gen_inference.py

# Android 에뮬레이터로 전송
adb push . /sdcard/Pictures/SmartFarm_Test/
```

해당 이미지는 `.gitignore` 화이트리스트(`!ai/test_images/**/*.JPG`)로 추적된다.
