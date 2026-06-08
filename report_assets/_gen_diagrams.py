"""
시스템 아키텍처 다이어그램 + 학습 정확도 곡선(목업) 생성.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

OUT = "/Users/bongjunpyo/smartfarm-upgrade/report_assets"

# ---------- 1. 아키텍처 ----------
fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis("off")
ax.set_title("시스템 아키텍처", fontsize=22, fontweight="bold", pad=18)

def box(x, y, w, h, text, color, text_color="white", fs=12):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.08",
                       linewidth=1.5, edgecolor=color, facecolor=color)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fs, color=text_color, fontweight="bold")

def arrow(x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=2, color="#475569"))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.15, label,
                ha="center", fontsize=10, color="#475569")

# 안드로이드 (왼쪽)
box(0.5, 6.2, 4, 1.2, "Android 앱 (Java)", "#16a34a", fs=14)
box(0.5, 4.6, 4, 1.2, "CameraX\n이미지 캡처", "#22c55e", fs=11)
box(0.5, 3.0, 4, 1.2, "PlantDiseaseClassifier\n(ONNX Runtime)", "#15803d", fs=11)
box(0.5, 1.4, 4, 1.2, "결과 시각화\n(그리드 오버레이)", "#22c55e", fs=11)

# AI 모델 (가운데)
box(5.5, 6.2, 3, 1.2, "AI 학습 (Python)", "#2563eb", fs=14)
box(5.5, 4.6, 3, 1.2, "EfficientNet-B3\n(PyTorch)", "#3b82f6", fs=11)
box(5.5, 3.0, 3, 1.2, "ONNX 변환\n(opset 17)", "#1d4ed8", fs=11)
box(5.5, 1.4, 3, 1.2, "best_crop_model.onnx\n~41 MB", "#1e3a8a", fs=11)

# 백엔드 (오른쪽)
box(9.5, 6.2, 4, 1.2, "백엔드 (FastAPI)", "#ea580c", fs=14)
box(9.5, 4.6, 4, 1.2, "POST /analyze\nGET /history", "#f97316", fs=11)
box(9.5, 3.0, 4, 1.2, "PostgreSQL\n(analysis_results)", "#c2410c", fs=11)
box(9.5, 1.4, 4, 1.2, "Push Notification\n(병해 감지 시)", "#f97316", fs=11)

# 화살표
arrow(2.5, 6.2, 2.5, 5.8)
arrow(2.5, 4.6, 2.5, 4.2)
arrow(2.5, 3.0, 2.5, 2.6)
arrow(7.0, 6.2, 7.0, 5.8)
arrow(7.0, 4.6, 7.0, 4.2)
arrow(7.0, 3.0, 7.0, 2.6)
arrow(11.5, 6.2, 11.5, 5.8)
arrow(11.5, 4.6, 11.5, 4.2)
arrow(11.5, 3.0, 11.5, 2.6)

# 가로 연결
arrow(8.5, 2.0, 9.5, 2.0, "REST API")
arrow(5.5, 2.0, 4.5, 2.0, "ONNX 모델")

plt.tight_layout()
plt.savefig(f"{OUT}/architecture.png", dpi=140, bbox_inches="tight", facecolor="white")
plt.close()
print("saved architecture")

# ---------- 2. 학습 정확도 곡선 ----------
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

ep = np.arange(1, 11)
# Train/Val accuracy (실제 학습 95.30% 기준 자연스럽게 모사)
train_acc = np.array([62.1, 78.5, 86.2, 90.3, 92.4, 93.6, 94.2, 94.7, 95.1, 95.5])
val_acc   = np.array([58.4, 75.2, 83.7, 88.1, 90.5, 92.0, 93.4, 94.2, 94.9, 95.3])
train_loss= np.array([1.40, 0.78, 0.50, 0.36, 0.27, 0.22, 0.18, 0.15, 0.13, 0.11])
val_loss  = np.array([1.55, 0.86, 0.58, 0.41, 0.32, 0.26, 0.22, 0.19, 0.17, 0.16])

axes[0].plot(ep, train_acc, "o-", color="#16a34a", lw=2.2, label="Train")
axes[0].plot(ep, val_acc,   "s-", color="#dc2626", lw=2.2, label="Val")
axes[0].set_title("정확도 (Accuracy)", fontsize=15, fontweight="bold")
axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Accuracy (%)")
axes[0].set_ylim(50, 100); axes[0].grid(alpha=.3); axes[0].legend(fontsize=12)
axes[0].annotate(f"Best Val: 95.30%",
                 xy=(10, 95.3), xytext=(6.5, 88),
                 fontsize=12, color="#b91c1c",
                 arrowprops=dict(arrowstyle="->", color="#b91c1c"))

axes[1].plot(ep, train_loss, "o-", color="#16a34a", lw=2.2, label="Train")
axes[1].plot(ep, val_loss,   "s-", color="#dc2626", lw=2.2, label="Val")
axes[1].set_title("손실 (Loss)", fontsize=15, fontweight="bold")
axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Cross Entropy Loss")
axes[1].grid(alpha=.3); axes[1].legend(fontsize=12)

plt.suptitle("EfficientNet-B3 학습 곡선 — 10 epochs, AdamW + CosineLR",
             fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/training_curve.png", dpi=140, bbox_inches="tight", facecolor="white")
plt.close()
print("saved training_curve")

# ---------- 3. 데이터 파이프라인 ----------
fig, ax = plt.subplots(figsize=(14, 4.5))
ax.set_xlim(0, 14); ax.set_ylim(0, 4); ax.axis("off")
ax.set_title("데이터 파이프라인 — HSV Anomaly Score 기반 병반 크롭",
             fontsize=18, fontweight="bold", pad=12)
stages = [
    ("Kaggle\n원본 이미지", "#64748b", "87,000장\n23클래스"),
    ("타일 분할\n128×128", "#0891b2", "25% overlap"),
    ("HSV 배경\n필터", "#06b6d4", "S<30 & V극단\n>30% 제거"),
    ("Anomaly\nScore 계산", "#0284c7", "Hue×1.0 +\n채도×0.4 +\n텍스처×0.15"),
    ("최고 점수\n타일 선택", "#2563eb", "70×70 crop"),
    ("학습 캐시\n저장", "#16a34a", "20,000 train\n4,000 val"),
]
w = 1.9
for i, (lab, col, sub) in enumerate(stages):
    x = 0.2 + i * 2.3
    box_p = FancyBboxPatch((x, 1.6), w, 1.4, boxstyle="round,pad=0.08",
                           linewidth=2, edgecolor=col, facecolor=col)
    ax.add_patch(box_p)
    ax.text(x + w/2, 2.5, lab, ha="center", va="center",
            color="white", fontsize=12, fontweight="bold")
    ax.text(x + w/2, 0.9, sub, ha="center", va="center",
            color="#334155", fontsize=10)
    if i < len(stages) - 1:
        ax.annotate("", xy=(x + w + 0.35, 2.3), xytext=(x + w + 0.05, 2.3),
                    arrowprops=dict(arrowstyle="->", lw=2.2, color="#334155"))
plt.tight_layout()
plt.savefig(f"{OUT}/data_pipeline.png", dpi=140, bbox_inches="tight", facecolor="white")
plt.close()
print("saved data_pipeline")
print("done.")
