# 백엔드 API

Android 앱이 호출하는 FastAPI 서버. 업로드된 이미지를 `best_crop_model.onnx`(EfficientNet-B3)로
추론하고 결과를 PostgreSQL에 적재한다. 서버 코드는 별도 디렉토리에서 운영하며, 본 디렉토리는 스펙 문서다.

## 기술 스택

- Python FastAPI + uvicorn
- onnxruntime (서버 측 추론, `../ai/model/best_crop_model.onnx`)
- SQLAlchemy (async) + PostgreSQL 16

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST  | `/analyze`                     | 이미지 업로드(multipart) → ONNX 추론 → DB 저장 |
| GET   | `/fields`                      | 전체 구역 + 최신 분석 결과 |
| GET   | `/status/{field_id}`           | 특정 구역 상태·신뢰도 |
| GET   | `/images`                      | 촬영 이미지 목록 (`field_id`, `limit`, `offset`) |
| GET   | `/history`                     | 구역별 분석 이력 시계열 |
| GET   | `/notifications`               | 위험 알림 목록 |
| PATCH | `/notifications/{id}/read`     | 알림 읽음 처리 |
| POST  | `/admin/run-daily-capture`     | 하루 1회 촬영 트리거 (테스트용) |
| GET   | `/health`                      | 헬스 체크 |

> 앱(`ApiService.java`)이 실제 사용하는 엔드포인트: `fields`, `analyze`, `images`, `notifications`, `notifications/{id}/read`

### `/analyze` 요청/응답 예시

```
POST /analyze   (multipart/form-data)
  field_id: "A1"
  image: <file>

200 OK
{
  "disease_type": "Tomato: Early Blight",
  "confidence": 0.914,
  "is_healthy": false,
  "field_id": "A1"
}
```

## DB 스키마 (4 tables)

```sql
CREATE TABLE fields (
    id        SERIAL PRIMARY KEY,
    name      TEXT,              -- 구역명 (A1~B4)
    location  TEXT,
    status    TEXT DEFAULT 'healthy'   -- healthy / warning / danger
);

CREATE TABLE images (
    id          SERIAL PRIMARY KEY,
    field_id    INT REFERENCES fields(id),
    image_path  TEXT,
    captured_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE analysis_results (
    id           SERIAL PRIMARY KEY,
    image_id     INT REFERENCES images(id),
    field_id     INT REFERENCES fields(id),
    disease_type TEXT,
    confidence   FLOAT,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notifications (
    id         SERIAL PRIMARY KEY,
    field_id   INT REFERENCES fields(id),
    message    TEXT,
    is_read    BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```
