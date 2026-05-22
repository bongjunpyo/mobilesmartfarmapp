# 백엔드 API

## 기술 스택

- Python FastAPI 또는 Node.js
- PostgreSQL

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | /analyze | 이미지 분석 & 결과 저장 |
| GET | /history | 분석 히스토리 조회 |
| GET | /status/{field_id} | 특정 구역 상태 조회 |

## DB 스키마

```sql
CREATE TABLE analysis_results (
    id          SERIAL PRIMARY KEY,
    image_path  TEXT,
    field_id    INT,
    disease_type TEXT,
    confidence  FLOAT,
    timestamp   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fields (
    id       SERIAL PRIMARY KEY,
    name     TEXT,
    location TEXT,
    status   TEXT DEFAULT 'healthy'
);

CREATE TABLE notifications (
    id        SERIAL PRIMARY KEY,
    field_id  INT REFERENCES fields(id),
    message   TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```
