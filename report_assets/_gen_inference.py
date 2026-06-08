"""
ONNX 모델로 test_images의 8장을 추론하고
'AI 진단 결과 갤러리' 한 장 + '그리드 오버레이' 한 장을 생성한다.
"""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import onnxruntime as ort
import matplotlib.pyplot as plt
import matplotlib.patches as patches
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = "/Users/bongjunpyo/smartfarm-upgrade"
MODEL = f"{ROOT}/ai/model/best_crop_model.onnx"
IMGDIR = f"{ROOT}/ai/test_images"
OUT = f"{ROOT}/report_assets"

CLASSES = [
    "Potato: Early Blight", "Potato: Late Blight", "Potato: Healthy",
    "Tomato: Bacterial Spot", "Tomato: Early Blight", "Tomato: Late Blight",
    "Tomato: Leaf Mold", "Tomato: Septoria Leaf Spot",
    "Tomato: Spider Mites", "Tomato: Target Spot",
    "Tomato: Yellow Leaf Curl Virus", "Tomato: Mosaic Virus",
    "Tomato: Healthy", "Pepper: Bacterial Spot", "Pepper: Healthy",
    "Apple: Apple Scab", "Apple: Black Rot", "Apple: Cedar Apple Rust",
    "Apple: Healthy",
    "Corn: Cercospora / Gray Leaf Spot",
    "Corn: Common Rust", "Corn: Northern Leaf Blight",
    "Corn: Healthy",
]
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def preprocess(img: Image.Image):
    img = img.convert("RGB").resize((224, 224), Image.BICUBIC)
    arr = np.asarray(img).astype(np.float32) / 255.0
    arr = (arr - MEAN) / STD
    arr = arr.transpose(2, 0, 1)[None, ...]
    return arr.astype(np.float32)

def softmax(x):
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()

print(">>> ONNX session...")
sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
inp_name = sess.get_inputs()[0].name

picks = [
    "TomatoEarlyBlight1.JPG",
    "TomatoYellowCurlVirus1.JPG",
    "TomatoHealthy1.JPG",
    "PotatoEarlyBlight1.JPG",
    "PotatoHealthy1.JPG",
    "AppleScab1.JPG",
    "AppleCedarRust1.JPG",
    "CornCommonRust1.JPG",
]

# ---------- 1. 갤러리 ----------
fig, axes = plt.subplots(2, 4, figsize=(16, 9))
fig.suptitle("AI 진단 결과 — test_images / EfficientNet-B3 ONNX",
             fontsize=16, fontweight="bold")
for ax, fname in zip(axes.flat, picks):
    p = os.path.join(IMGDIR, fname)
    img = Image.open(p)
    arr = preprocess(img)
    logits = sess.run(None, {inp_name: arr})[0][0]
    probs = softmax(logits)
    idx = int(probs.argmax())
    label = CLASSES[idx]
    conf = float(probs[idx])
    healthy = "Healthy" in label
    border = "#22c55e" if healthy else "#ef4444"
    ax.imshow(img)
    ax.axis("off")
    rect = patches.Rectangle((0, 0), img.width - 1, img.height - 1,
                             linewidth=6, edgecolor=border, facecolor="none")
    ax.add_patch(rect)
    title = f"{label}\n{conf*100:.1f}%"
    ax.set_title(title, fontsize=10,
                 color="#15803d" if healthy else "#b91c1c",
                 fontweight="bold")
plt.tight_layout()
out1 = f"{OUT}/inference_gallery.png"
plt.savefig(out1, dpi=140, bbox_inches="tight", facecolor="white")
plt.close()
print("saved:", out1)

# ---------- 2. 그리드 오버레이 ----------
target = os.path.join(IMGDIR, "TomatoEarlyBlight1.JPG")
img = Image.open(target).convert("RGB")
w, h = img.size
GS = 10
cell_w, cell_h = w // GS, h // GS
overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)
disease_n = 0
total_n = 0
for r in range(GS):
    for c in range(GS):
        x, y = c * cell_w, r * cell_h
        cw = w - x if c == GS - 1 else cell_w
        ch = h - y if r == GS - 1 else cell_h
        cell = img.crop((x, y, x + cw, y + ch))
        arr = preprocess(cell)
        logits = sess.run(None, {inp_name: arr})[0][0]
        probs = softmax(logits)
        idx = int(probs.argmax())
        label = CLASSES[idx]
        conf = float(probs[idx])
        total_n += 1
        if "Healthy" in label:
            color = (50, 200, 50, 70)
        else:
            disease_n += 1
            alpha = int(80 + conf * 120)
            color = (220, 50, 50, alpha)
        draw.rectangle([x, y, x + cw, y + ch], fill=color)
for r in range(GS + 1):
    draw.line([(0, r * cell_h), (w, r * cell_h)], fill=(255, 255, 255, 120), width=1)
for c in range(GS + 1):
    draw.line([(c * cell_w, 0), (c * cell_w, h)], fill=(255, 255, 255, 120), width=1)
result = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
axes[0].imshow(img); axes[0].set_title("원본 이미지", fontsize=14, fontweight="bold")
axes[0].axis("off")
axes[1].imshow(result)
ratio = disease_n / total_n
axes[1].set_title(
    f"그리드 추론 오버레이 (10×10)\n병해 {disease_n}/{total_n} 셀 ({ratio*100:.0f}%) — 빨강=병해, 초록=건강",
    fontsize=12, fontweight="bold")
axes[1].axis("off")
plt.tight_layout()
out2 = f"{OUT}/grid_overlay.png"
plt.savefig(out2, dpi=140, bbox_inches="tight", facecolor="white")
plt.close()
print("saved:", out2)
print("done.")
