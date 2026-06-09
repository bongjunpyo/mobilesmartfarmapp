"""
best_plant_model.pth로 질병/건강 잎 테스트 + GradCAM 시각화
- 저장된 최고 정확도 모델 로드
- 데이터셋에서 질병 잎 / 건강 잎 각 N장 선택
- GradCAM으로 '어느 부분을 보고 판단했는지' 열지도 시각화
- 예측 결과(정/오답) + 근거 영역을 한 장의 이미지로 저장
"""
import math
import random
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b3

SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)
np.random.seed(SEED)

# GradCAM은 backward 계산이 필요하므로 CPU 사용 (MPS backward 호환성)
DEVICE = torch.device("cpu")
print(f"Device: {DEVICE}  (GradCAM backward 안정성을 위해 CPU 사용)")

IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
EFFNET_PATH = Path("./best_crop_model.pth")
SAMPLES_PER_TYPE = 6  # 질병/건강 각 N장

TARGET_CLASSES = {
    "Potato___Early_blight": "Potato/EarlyBlight",
    "Potato___Late_blight": "Potato/LateBlight",
    "Potato___healthy": "Potato/Healthy",
    "Tomato___Bacterial_spot": "Tomato/BacterialSpot",
    "Tomato___Early_blight": "Tomato/EarlyBlight",
    "Tomato___Late_blight": "Tomato/LateBlight",
    "Tomato___Leaf_Mold": "Tomato/LeafMold",
    "Tomato___Septoria_leaf_spot": "Tomato/Septoria",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Tomato/SpiderMites",
    "Tomato___Target_Spot": "Tomato/TargetSpot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/YellowCurl",
    "Tomato___Tomato_mosaic_virus": "Tomato/Mosaic",
    "Tomato___healthy": "Tomato/Healthy",
    "Pepper,_bell___Bacterial_spot": "Pepper/BacterialSpot",
    "Pepper,_bell___healthy": "Pepper/Healthy",
    "Apple___Apple_scab": "Apple/Scab",
    "Apple___Black_rot": "Apple/BlackRot",
    "Apple___Cedar_apple_rust": "Apple/CedarRust",
    "Apple___healthy": "Apple/Healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Corn/Cercospora",
    "Corn_(maize)___Common_rust_": "Corn/CommonRust",
    "Corn_(maize)___Northern_Leaf_Blight": "Corn/NorthernBlight",
    "Corn_(maize)___healthy": "Corn/Healthy",
}
CLASS_NAMES = list(TARGET_CLASSES.keys())
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASS_NAMES)}
IDX_TO_SHORT = {i: v for i, (_, v) in enumerate(TARGET_CLASSES.items())}
HEALTHY_CLASSES = frozenset(c for c in CLASS_NAMES if "healthy" in c.lower())


# ── GradCAM ─────────────────────────────────────────────────────
class GradCAM:
    """EfficientNet-B3 마지막 ConvBN 블록 기준 GradCAM"""

    def __init__(self, model, target_layer):
        self.model = model
        self._activations = None
        self._gradients = None
        self._handles = [
            target_layer.register_forward_hook(self._fwd_hook),
            target_layer.register_full_backward_hook(self._bwd_hook),
        ]

    def _fwd_hook(self, _m, _i, output):
        self._activations = output.detach()

    def _bwd_hook(self, _m, _gi, grad_output):
        self._gradients = grad_output[0].detach()

    def remove(self):
        for h in self._handles:
            h.remove()

    def __call__(self, x, class_idx=None):
        """CAM 반환. x: (1, C, H, W), 반환: (H', W') 범위 [0, 1]"""
        self.model.eval()
        logits = self.model(x)
        if class_idx is None:
            class_idx = int(logits.argmax(dim=1))
        self.model.zero_grad()
        logits[0, class_idx].backward()

        # 채널 방향 가중 평균
        w = self._gradients[0].mean(dim=(1, 2))           # (C,)
        cam = (w[:, None, None] * self._activations[0]).sum(0)  # (H', W')
        cam = torch.relu(cam).cpu().numpy()
        cam -= cam.min()
        if cam.max() > 0:
            cam /= cam.max()
        return cam, class_idx


# ── 전처리 / 시각화 헬퍼 ────────────────────────────────────────
_tf = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])


def load_image(img_path):
    pil = Image.open(img_path).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    return _tf(pil).unsqueeze(0), np.array(pil)


def apply_gradcam_overlay(img_rgb, cam, alpha=0.45):
    hm = cv2.resize(cam, (img_rgb.shape[1], img_rgb.shape[0]))
    hm = np.uint8(255 * hm)
    hm_color = cv2.applyColorMap(hm, cv2.COLORMAP_JET)
    hm_rgb = cv2.cvtColor(hm_color, cv2.COLOR_BGR2RGB)
    overlay = (img_rgb * (1 - alpha) + hm_rgb * alpha).astype(np.uint8)
    return overlay


def collect_samples(data_dir, n):
    """질병/건강 잎 각 n장을 다양한 클래스에서 균형 있게 수집"""
    EXT = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
    available = [c for c in CLASS_NAMES if (data_dir / c).exists()]
    disease_cls = [c for c in available if c not in HEALTHY_CLASSES]
    healthy_cls = [c for c in available if c in HEALTHY_CLASSES]

    def sample_from(cls_list, total):
        out = []
        per = max(1, math.ceil(total / max(1, len(cls_list))))
        for cls in cls_list:
            imgs = [p for p in (data_dir / cls).iterdir() if p.suffix in EXT]
            random.shuffle(imgs)
            for p in imgs[:per]:
                out.append((p, cls))
                if len(out) >= total:
                    return out
        return out[:total]

    return sample_from(disease_cls, n), sample_from(healthy_cls, n)


# ── 메인 ────────────────────────────────────────────────────────
def main():
    if not EFFNET_PATH.exists():
        raise FileNotFoundError(
            f"모델 없음: {EFFNET_PATH}\n"
            "먼저 plant_disease_preprocessing.py 를 실행해 모델을 학습하세요."
        )

    import kagglehub
    dataset_root = Path(kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset"))
    base = dataset_root / "New Plant Diseases Dataset(Augmented)" / "New Plant Diseases Dataset(Augmented)"
    val_dir = base / "valid"

    # 모델 로드
    model = efficientnet_b3(weights=None)
    model.classifier[1] = nn.Sequential(
        nn.Dropout(0.3, inplace=True),
        nn.Linear(model.classifier[1].in_features, len(CLASS_NAMES)),
    )
    state = torch.load(EFFNET_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(DEVICE).eval()
    print(f"모델 로드 완료: {EFFNET_PATH}")

    # GradCAM: 마지막 특징 블록(features[-1])에 훅
    gradcam = GradCAM(model, model.features[-1])

    # 샘플 수집
    disease_samples, healthy_samples = collect_samples(val_dir, SAMPLES_PER_TYPE)
    print(f"질병 잎: {len(disease_samples)}장 | 건강 잎: {len(healthy_samples)}장")

    all_samples = (
        [("disease", p, c) for p, c in disease_samples]
        + [("healthy", p, c) for p, c in healthy_samples]
    )

    # ── 각 이미지 분석 ────────────────────────────────────────
    results = []
    for sample_type, img_path, true_cls in all_samples:
        x, img_rgb = load_image(img_path)
        x = x.to(DEVICE).requires_grad_(True)

        with torch.enable_grad():
            cam, pred_idx = gradcam(x)

        with torch.no_grad():
            probs = torch.softmax(model(x), 1)[0]
        top3 = probs.topk(3)
        top3_pairs = [(IDX_TO_SHORT[i.item()], v.item()) for i, v in zip(top3.indices, top3.values)]

        pred_cls = CLASS_NAMES[pred_idx]
        pred_is_healthy = pred_cls in HEALTHY_CLASSES
        true_is_healthy = true_cls in HEALTHY_CLASSES
        is_correct = (pred_is_healthy == true_is_healthy)

        overlay = apply_gradcam_overlay(img_rgb, cam)

        results.append({
            "type": sample_type,
            "path": img_path,
            "true_short": TARGET_CLASSES.get(true_cls, true_cls),
            "pred_short": IDX_TO_SHORT[pred_idx],
            "conf": probs[pred_idx].item(),
            "top3": top3_pairs,
            "pred_label": "건강" if pred_is_healthy else "질병",
            "correct": is_correct,
            "img_rgb": img_rgb,
            "overlay": overlay,
        })
        mark = "✓" if is_correct else "✗"
        print(f"  {mark} [{sample_type:7s}] {img_path.name:30s} "
              f"→ {IDX_TO_SHORT[pred_idx]:20s} ({probs[pred_idx]*100:5.1f}%)")

    gradcam.remove()

    # ── 시각화 ────────────────────────────────────────────────
    disease_res = [r for r in results if r["type"] == "disease"]
    healthy_res = [r for r in results if r["type"] == "healthy"]
    max_rows = max(len(disease_res), len(healthy_res))

    # 열 구성: [질병원본, 질병GradCAM, 건강원본, 건강GradCAM]
    fig, axes = plt.subplots(max_rows, 4, figsize=(16, max_rows * 3.5))
    if max_rows == 1:
        axes = np.expand_dims(axes, 0)

    col_headers = ["질병 잎 — 원본", "GradCAM (질병 잎)", "건강 잎 — 원본", "GradCAM (건강 잎)"]
    for ci, hdr in enumerate(col_headers):
        axes[0][ci].annotate(
            hdr, xy=(0.5, 1.18), xycoords="axes fraction",
            ha="center", fontsize=9, fontweight="bold",
            annotation_clip=False,
        )

    def render_pair(row, col_off, r):
        is_correct = r["correct"]
        edge = "#2ECC71" if is_correct else "#E74C3C"

        ax_orig = axes[row][col_off]
        ax_orig.imshow(r["img_rgb"])
        ax_orig.set_title(
            f"GT: {r['true_short']}\n{r['path'].name}",
            fontsize=7,
        )
        ax_orig.axis("off")
        for sp in ax_orig.spines.values():
            sp.set_edgecolor(edge); sp.set_linewidth(2.5)

        ax_cam = axes[row][col_off + 1]
        ax_cam.imshow(r["overlay"])
        verdict = "✓ 정답" if is_correct else "✗ 오답"
        ax_cam.set_title(
            f"{verdict} → {r['pred_label']}\n{r['pred_short']} ({r['conf']*100:.1f}%)",
            fontsize=7,
            color=edge,
        )
        ax_cam.axis("off")
        for sp in ax_cam.spines.values():
            sp.set_edgecolor(edge); sp.set_linewidth(2.5)

    for row in range(max_rows):
        if row < len(disease_res):
            render_pair(row, 0, disease_res[row])
        else:
            axes[row][0].axis("off"); axes[row][1].axis("off")
        if row < len(healthy_res):
            render_pair(row, 2, healthy_res[row])
        else:
            axes[row][2].axis("off"); axes[row][3].axis("off")

    legend_patches = [
        mpatches.Patch(color="#2ECC71", label="예측 정답"),
        mpatches.Patch(color="#E74C3C", label="예측 오답"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=2,
               fontsize=9, bbox_to_anchor=(0.5, -0.005))

    correct_n = sum(1 for r in results if r["correct"])
    total_n = len(results)
    fig.suptitle(
        "GradCAM — 모델이 어느 영역을 보고 질병 / 건강을 판단하는가\n"
        f"(빨간·노란=고활성 판단 근거 영역 | 파란=저활성 영역)   "
        f"정답률: {correct_n}/{total_n} ({correct_n/max(1,total_n)*100:.1f}%)",
        fontsize=12, fontweight="bold",
    )

    plt.tight_layout()
    out_path = "./disease_region_test.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n{out_path} 저장 완료")

    # ── 요약 ─────────────────────────────────────────────────
    print(f"\n[결과 요약]")
    print(f"  질병 잎  : {len(disease_res)}장  "
          f"정답 {sum(r['correct'] for r in disease_res)}장")
    print(f"  건강 잎  : {len(healthy_res)}장  "
          f"정답 {sum(r['correct'] for r in healthy_res)}장")
    print(f"  전체     : {correct_n}/{total_n}  "
          f"({correct_n/max(1,total_n)*100:.1f}%)")
    print(f"\n  GradCAM 해석:")
    print(f"    빨간/노란 영역 → 모델이 집중한 핵심 판단 근거")
    print(f"    파란 영역      → 판단에 거의 영향을 주지 않은 부분")
    print(f"    정상적이라면, 질병 잎에서는 반점/변색 부위가")
    print(f"    건강 잎에서는 전체 잎 영역이 고활성이어야 합니다.")


if __name__ == "__main__":
    main()
