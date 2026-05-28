# Android 앱

## 환경

- Android Studio
- Java + Groovy (Gradle)
- minSdk: 24 (Android 7.0)

## AI 통합 파일

| 파일 | 설명 |
|------|------|
| `PlantDiseaseClassifier.java` | 추론 클래스 (복사해서 바로 사용) |
| `../ai/model/best_crop_model.onnx` | 학습된 ONNX 모델 (EfficientNet-B3, val acc 96.5%) |
| `../ai/test_images/` | 테스트용 이미지 33장 |

## AI 통합 방법

### 1. 파일 복사
```
android/PlantDiseaseClassifier.java  →  app/src/main/java/.../PlantDiseaseClassifier.java
ai/model/best_crop_model.onnx        →  app/src/main/assets/best_crop_model.onnx
```

### 2. build.gradle (app) 의존성 추가
```gradle
implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'
```

### 3. AndroidManifest.xml 권한 추가
```xml
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="32" />
```

### 4. 패키지명 변경
`PlantDiseaseClassifier.java` 첫 줄을 프로젝트 패키지명으로 변경:
```java
package com.example.yourapp;  // 실제 패키지명으로 교체
```

### 5. 코드에서 사용
```java
// 초기화 (Activity onCreate에서 한 번만)
PlantDiseaseClassifier classifier = new PlantDiseaseClassifier(context);

// 추론 (Bitmap이 있을 때)
PlantDiseaseClassifier.Result result = classifier.predict(bitmap);

result.label;       // "Tomato: Early Blight"
result.confidence;  // 0.0 ~ 1.0  (예: 0.914 = 91.4%)
result.isHealthy;   // true / false

// 해제 (Activity onDestroy에서)
classifier.close();
```

## 테스트 이미지 에뮬레이터에 넣기
```bash
adb push ai/test_images/ /sdcard/Pictures/test_images/
```

## 지원 클래스 (23종)
- Potato: Early Blight / Late Blight / Healthy
- Tomato: Bacterial Spot / Early Blight / Late Blight / Leaf Mold / Septoria / Spider Mites / Target Spot / Yellow Curl Virus / Mosaic / Healthy
- Pepper: Bacterial Spot / Healthy
- Apple: Scab / Black Rot / Cedar Rust / Healthy
- Corn: Cercospora / Common Rust / Northern Blight / Healthy

## 주요 기능 (구현 예정)

- 카메라 촬영 (5개 구역 선택)
- Bluetooth 페어링 & 사진 수신
- AI 분석 (온디바이스 ONNX Runtime)
- 질병 감지 시 Push Notification
- 구역별 색상/아이콘 시각화
- 분석 히스토리 조회

## 의존성 (build.gradle)

```groovy
// ONNX 온디바이스 추론
implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'

// REST API
implementation 'com.squareup.retrofit2:retrofit:2.9.0'
implementation 'com.squareup.retrofit2:converter-gson:2.9.0'

// 이미지 로딩
implementation 'com.github.bumptech.glide:glide:4.16.0'
```
