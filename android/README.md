# Android 앱

비닐하우스 구역별 식물 병해를 모니터링하는 안드로이드 클라이언트.
온디바이스 추론이 아니라 **FastAPI 백엔드(`/analyze`)에 이미지를 올려 서버 측 ONNX 추론 결과를 받아오는** 서버 연동 구조다.

## 환경

- Android Studio (Groovy Gradle)
- Java
- minSdk 24 (Android 7.0) / 백엔드 통신 기준 `http://10.0.2.2:8000/` (에뮬레이터 → 호스트 localhost)

## 앱 구조

```
app/src/main/java/com/example/smartfarm/
├── SplashActivity.java              # 스플래시 → MainActivity
├── MainActivity.java                # BottomNavigation (구역 현황 / 사진 기록)
├── network/
│   ├── ApiClient.java               # Retrofit 인스턴스 (BASE_URL = 10.0.2.2:8000)
│   └── ApiService.java              # REST 엔드포인트 정의
├── model/                           # DTO (Field, AnalyzeResponse, ImageItem, NotificationItem, LatestAnalysis)
├── repository/PlantRepository.java  # API 호출 래퍼
├── worker/
│   ├── CameraWorker.java            # WorkManager 14:00 자동 촬영 → /analyze 업로드
│   └── BootReceiver.java            # 부팅 시 스케줄 재등록
└── ui/
    ├── farm/         FarmFragment + ZoneAdapter        # 구역 현황 카드 + 구역 상세 BottomSheet
    ├── image/        ImageFragment + ImageAdapter      # 사진 기록 갤러리 + 상세 BottomSheet
    └── notification/ NotificationFragment + NotificationAdapter  # 위험 알림 목록
```

## 백엔드 연동 API (`ApiService`)

| 메서드 | 엔드포인트 | 화면 |
|--------|-----------|------|
| GET   | `fields`                       | 구역 현황 (Farm) |
| POST  | `analyze` (multipart)          | 이미지 업로드 → 분석 |
| GET   | `images?field_id&limit&offset` | 사진 기록 (Image) |
| GET   | `notifications`                | 알림 |
| PATCH | `notifications/{id}/read`      | 알림 읽음 처리 |

> `BASE_URL`은 `ApiClient.java`에서 변경. 실기기 테스트 시 호스트 PC의 LAN IP로 교체.

## 주요 의존성 (`app/build.gradle`)

```groovy
implementation 'com.squareup.retrofit2:retrofit:2.9.0'        // REST
implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
implementation 'com.squareup.okhttp3:logging-interceptor:4.12.0'
implementation 'com.github.bumptech.glide:glide:4.16.0'       // 이미지 로딩
implementation 'androidx.work:work-runtime:2.9.0'             // 14:00 자동 촬영
implementation 'androidx.camera:camera-camera2:1.3.1'         // CameraX
```

## 온디바이스 추론 (선택)

`PlantDiseaseClassifier.java`는 백엔드 없이 ONNX Runtime으로 **단말에서 직접** 추론하는 대안 유틸이다.
현재 앱(`app/`)에는 연결돼 있지 않으며, 오프라인 추론이 필요할 때 아래처럼 통합한다.

### 1. 파일 복사
```
android/PlantDiseaseClassifier.java  →  app/src/main/java/.../PlantDiseaseClassifier.java
ai/model/best_crop_model.onnx        →  app/src/main/assets/best_crop_model.onnx
```

### 2. 의존성 추가
```gradle
implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'
```

### 3. 패키지명 변경 후 사용
```java
PlantDiseaseClassifier classifier = new PlantDiseaseClassifier(context); // onCreate
PlantDiseaseClassifier.Result result = classifier.predict(bitmap);
result.label;       // "Tomato: Early Blight"
result.confidence;  // 0.0 ~ 1.0
result.isHealthy;   // true / false
classifier.close(); // onDestroy
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

> 모델 정확도: Best Val Accuracy **95.30%** (`../ai/model/best_crop_model.onnx`)
