# Android 앱

## 환경

- Android Studio
- Java + Groovy (Gradle)
- minSdk: 26 (Android 8.0)

## 주요 기능 (구현 예정)

- 카메라 촬영 (5개 구역 선택)
- Bluetooth 페어링 & 사진 수신
- AI 분석 (온디바이스 TFLite 또는 API 호출)
- 질병 감지 시 Push Notification
- 구역별 색상/아이콘 시각화
- 분석 히스토리 조회

## 의존성 (build.gradle)

```groovy
// TFLite 온디바이스 추론
implementation 'org.tensorflow:tensorflow-lite:2.13.0'
implementation 'org.tensorflow:tensorflow-lite-support:0.4.4'

// REST API
implementation 'com.squareup.retrofit2:retrofit:2.9.0'
implementation 'com.squareup.retrofit2:converter-gson:2.9.0'

// 이미지 로딩
implementation 'com.github.bumptech.glide:glide:4.16.0'
```
