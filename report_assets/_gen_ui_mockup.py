"""
Pillow로 안드로이드 앱 화면 목업 4종 + 합본 1장 생성.
실제 앱은 미구현이므로 발표용 와이어프레임 스타일.
"""
import os
from PIL import Image, ImageDraw, ImageFont
import onnxruntime as ort
import numpy as np

ROOT = "/Users/bongjunpyo/smartfarm-upgrade"
OUT = f"{ROOT}/report_assets"

# AppleGothic
FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

def F(sz, bold=False):
    return ImageFont.truetype(FONT_PATH, sz)

W, H = 412, 869   # Pixel 5 viewport 느낌

PRIMARY = "#16a34a"
PRIMARY_DARK = "#15803d"
DANGER = "#dc2626"
BG = "#f8fafc"
CARD = "#ffffff"
TEXT = "#0f172a"
MUTED = "#64748b"
BORDER = "#e2e8f0"

def base_frame(title="스마트팜 진단"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # status bar
    d.rectangle([0, 0, W, 28], fill="#0f172a")
    d.text((16, 6), "9:41", fill="white", font=F(14))
    d.text((W - 70, 6), "100%", fill="white", font=F(13))
    # app bar
    d.rectangle([0, 28, W, 92], fill=PRIMARY)
    d.text((20, 50), title, fill="white", font=F(22))
    d.text((W - 60, 56), "⚙", fill="white", font=F(20))
    return img, d

# ----------- 1. 메인 (구역 선택) -----------
img, d = base_frame("스마트팜 진단")
d.text((20, 110), "오늘 비닐하우스 상태", fill=TEXT, font=F(16))
d.text((20, 134), "마지막 점검: 2026-06-07 09:12", fill=MUTED, font=F(12))

zones = [
    ("A구역 (토마토)", "정상",  PRIMARY,  "98% 건강"),
    ("B구역 (감자)",  "주의",  "#f59e0b","Early Blight 의심 12%"),
    ("C구역 (사과)",  "병해",  DANGER,   "Cedar Rust 감지 38%"),
    ("D구역 (옥수수)","정상",  PRIMARY,  "99% 건강"),
    ("E구역 (피망)",  "정상",  PRIMARY,  "96% 건강"),
]
y = 168
for name, state, color, desc in zones:
    d.rounded_rectangle([16, y, W - 16, y + 78], 14, fill=CARD, outline=BORDER, width=1)
    d.ellipse([28, y + 18, 64, y + 54], fill=color)
    d.text((36, y + 26), state[0], fill="white", font=F(18))
    d.text((80, y + 14), name, fill=TEXT, font=F(16))
    d.text((80, y + 38), desc, fill=MUTED, font=F(12))
    d.text((W - 50, y + 30), "›", fill=MUTED, font=F(22))
    y += 92

# FAB
d.ellipse([W - 86, H - 110, W - 26, H - 50], fill=PRIMARY)
d.text((W - 78, H - 100), "📷", fill="white", font=F(28))

# bottom nav
d.rectangle([0, H - 60, W, H], fill=CARD, outline=BORDER, width=1)
for i, (icon, lab) in enumerate([("🏠","홈"),("📷","촬영"),("📊","히스토리"),("⚙","설정")]):
    cx = (W // 4) * i + W // 8
    c = PRIMARY if i == 0 else MUTED
    d.text((cx - 8, H - 50), icon, fill=c, font=F(18))
    d.text((cx - 16, H - 24), lab, fill=c, font=F(11))

img.save(f"{OUT}/ui_main.png")
print("saved ui_main")

# ----------- 2. 촬영 화면 -----------
img2 = Image.new("RGB", (W, H), "#0f172a")
d = ImageDraw.Draw(img2)
d.rectangle([0, 0, W, 28], fill="#000")
d.text((16, 6), "9:42", fill="white", font=F(14))
d.text((20, 50), "C구역 사과 촬영", fill="white", font=F(20))
d.text((20, 78), "잎이 화면 중앙에 오도록 맞춰주세요", fill="#cbd5e1", font=F(13))
# 카메라 미리보기 영역 (테스트 이미지 합성)
preview_h = 540
# 실제 테스트 이미지를 카메라 미리보기처럼
src = Image.open(f"{ROOT}/ai/test_images/AppleCedarRust1.JPG").convert("RGB")
src.thumbnail((W - 40, preview_h - 40))
px = (W - src.width) // 2
py = 110 + (preview_h - src.height) // 2
# dark backdrop
d.rectangle([20, 110, W - 20, 110 + preview_h], fill="#000")
img2.paste(src, (px, py))
# overlay frame
d2 = ImageDraw.Draw(img2)
margin = 40
fx0, fy0 = margin, 110 + 90
fx1, fy1 = W - margin, 110 + preview_h - 90
for i in range(4):
    pts = [
        (fx0, fy0, fx0 + 24, fy0),
        (fx0, fy0, fx0, fy0 + 24),
        (fx1, fy0, fx1 - 24, fy0),
        (fx1, fy0, fx1, fy0 + 24),
        (fx0, fy1, fx0 + 24, fy1),
        (fx0, fy1, fx0, fy1 - 24),
        (fx1, fy1, fx1 - 24, fy1),
        (fx1, fy1, fx1, fy1 - 24),
    ]
for x0, y0, x1, y1 in pts:
    d2.line([(x0, y0), (x1, y1)], fill=PRIMARY, width=4)

# 셔터
d2.ellipse([W//2 - 38, H - 130, W//2 + 38, H - 54], outline="white", width=4)
d2.ellipse([W//2 - 30, H - 122, W//2 + 30, H - 62], fill="white")
# 보조 버튼
d2.text((40, H - 105), "🔄\n전환", fill="white", font=F(13))
d2.text((W - 80, H - 105), "🖼\n갤러리", fill="white", font=F(13))

img2.save(f"{OUT}/ui_camera.png")
print("saved ui_camera")

# ----------- 3. 분석 진행 -----------
img3, d3 = base_frame("AI 분석 중")
d3.text((20, 130), "온디바이스 추론 (ONNX Runtime)", fill=MUTED, font=F(13))
# 이미지
sample = Image.open(f"{ROOT}/ai/test_images/TomatoEarlyBlight1.JPG").convert("RGB")
sample.thumbnail((W - 80, 360))
img3.paste(sample, ((W - sample.width) // 2, 180))
# 프로그레스
y0 = 180 + sample.height + 30
d3.rounded_rectangle([40, y0, W - 40, y0 + 14], 7, fill=BORDER)
d3.rounded_rectangle([40, y0, 40 + int((W - 80) * 0.7), y0 + 14], 7, fill=PRIMARY)
d3.text((40, y0 + 26), "EfficientNet-B3 추론 중...  70%", fill=TEXT, font=F(13))
# 단계
steps = [
    ("✓", "이미지 전처리 (224×224)", PRIMARY),
    ("✓", "HSV Anomaly Score 계산",  PRIMARY),
    ("●", "EfficientNet-B3 추론",   "#3b82f6"),
    ("○", "결과 시각화",             MUTED),
]
ys = y0 + 60
for ico, lab, c in steps:
    d3.text((40, ys), ico, fill=c, font=F(18))
    d3.text((72, ys + 2), lab, fill=TEXT, font=F(14))
    ys += 34

img3.save(f"{OUT}/ui_analyzing.png")
print("saved ui_analyzing")

# ----------- 4. 결과 화면 -----------
img4, d4 = base_frame("진단 결과")
# 결과 배지
d4.rounded_rectangle([16, 110, W - 16, 175], 14, fill="#fef2f2", outline=DANGER, width=2)
d4.text((30, 124), "⚠  병해 감지", fill=DANGER, font=F(18))
d4.text((30, 150), "Tomato : Early Blight", fill=TEXT, font=F(15))
d4.text((W - 100, 138), "95.5%", fill=DANGER, font=F(22))

# 이미지 (그리드 오버레이 미리 만든 거 활용)
gov = Image.open(f"{OUT}/grid_overlay.png").convert("RGB")
# 오른쪽 절반만 사용
right = gov.crop((gov.width // 2, 50, gov.width, gov.height - 30))
right.thumbnail((W - 40, 320))
img4.paste(right, ((W - right.width) // 2, 190))

# 통계 카드
y0 = 190 + right.height + 16
d4.rounded_rectangle([16, y0, (W // 2) - 4, y0 + 80], 12, fill=CARD, outline=BORDER, width=1)
d4.text((28, y0 + 12), "병해 셀 비율", fill=MUTED, font=F(12))
d4.text((28, y0 + 32), "49%", fill=DANGER, font=F(26))
d4.rounded_rectangle([(W // 2) + 4, y0, W - 16, y0 + 80], 12, fill=CARD, outline=BORDER, width=1)
d4.text((W // 2 + 16, y0 + 12), "정상 셀 비율", fill=MUTED, font=F(12))
d4.text((W // 2 + 16, y0 + 32), "51%", fill=PRIMARY, font=F(26))

# 권장 행동
y1 = y0 + 92
d4.rounded_rectangle([16, y1, W - 16, y1 + 90], 12, fill="#fffbeb", outline="#f59e0b", width=1)
d4.text((28, y1 + 10), "💡 권장 조치", fill="#92400e", font=F(13))
d4.text((28, y1 + 32), "1. 감염 잎 즉시 제거", fill=TEXT, font=F(12))
d4.text((28, y1 + 50), "2. 살균제 (만코제브) 살포", fill=TEXT, font=F(12))
d4.text((28, y1 + 68), "3. 3일 후 재진단 권장",     fill=TEXT, font=F(12))

# bottom nav
d4.rectangle([0, H - 60, W, H], fill=CARD, outline=BORDER, width=1)
for i, (icon, lab) in enumerate([("🏠","홈"),("📷","촬영"),("📊","히스토리"),("⚙","설정")]):
    cx = (W // 4) * i + W // 8
    c = PRIMARY if i == 2 else MUTED
    d4.text((cx - 8, H - 50), icon, fill=c, font=F(18))
    d4.text((cx - 16, H - 24), lab, fill=c, font=F(11))

img4.save(f"{OUT}/ui_result.png")
print("saved ui_result")

# ----------- 5. 4장 합본 -----------
combo = Image.new("RGB", (W * 4 + 60, H + 60), "#f1f5f9")
labels = ["① 메인 (구역 목록)", "② 촬영 화면", "③ AI 분석", "④ 진단 결과"]
files = ["ui_main.png", "ui_camera.png", "ui_analyzing.png", "ui_result.png"]
dc = ImageDraw.Draw(combo)
for i, (lab, f) in enumerate(zip(labels, files)):
    x = 12 + i * (W + 12)
    p = Image.open(f"{OUT}/{f}").convert("RGB")
    combo.paste(p, (x, 50))
    dc.text((x + 10, 14), lab, fill=TEXT, font=F(22))
combo.save(f"{OUT}/ui_combined.png")
print("saved ui_combined")
print("done.")
