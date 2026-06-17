# 보고서 · 발표 자료 생성

보고서(.docx)·발표(.pptx)와 그에 들어가는 다이어그램/추론 갤러리/UI 목업 이미지를 생성하는 스크립트 모음.

## 생성 스크립트

| 파일 | 산출물 | 설명 |
|------|--------|------|
| `_gen_diagrams.py` | `architecture.png`, `training_curve.png`, `data_pipeline.png` | 시스템 아키텍처·학습 곡선·데이터 파이프라인 도식 |
| `_gen_inference.py` | `inference_gallery.png`, `grid_overlay.png` | ONNX 모델로 test_images 추론 → 진단 갤러리·그리드 오버레이 |
| `_gen_ui_mockup.py` | `ui_*.png`, `ui_combined.png` | 앱 화면 와이어프레임 목업 (발표 자료용) |
| `_gen_docx.py` | `../스마트팜_AI_병해진단_최종보고서.docx` | AI 중심 최종보고서 |
| `_gen_pptx.py` | `../모바일프로그래밍_최종발표.pptx` | 16:9 최종 발표 슬라이드 |

## 실행

```bash
# AppleGothic 폰트 사용 (macOS)
python _gen_diagrams.py
python _gen_inference.py     # ai/model/best_crop_model.onnx 필요
python _gen_ui_mockup.py
python _gen_docx.py          # → 상위 디렉토리에 .docx
python _gen_pptx.py          # → 상위 디렉토리에 .pptx
```

## 산출물 정책

| 항목 | git 추적 |
|------|----------|
| 다이어그램·UI 목업 PNG (`architecture.png` 등) | O (`.gitignore` 화이트리스트) |
| `inference_gallery.png` (~2.9 MB) | X (대용량 제외) |
| `legacy_docx_img/` | X |
| `.docx` / `.pptx` (각 ~5 MB) | X (대용량 바이너리 제외) |

> 보고서/발표 파일은 스크립트로 언제든 재생성 가능하므로 저장소에 포함하지 않는다.
