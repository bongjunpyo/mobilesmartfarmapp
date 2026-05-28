"""
색상+텍스처 분석으로 병반 구역 탐지 → 70x70 크롭 사전 저장
- YOLO 없이 HSV 기반 이상 점수(Hue 이탈 + 채도 분산 + 텍스처)로 최적 타일 선택
- 결과를 ~/crop_cache/{train,val}/{class}/ 에 저장
- 완료 후 샘플 시각화 저장
"""
import json
import time
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from tqdm.auto import tqdm

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

TILE_SIZE    = 128
TILE_OVERLAP = 0.25
BG_THRESH    = 0.30
CROP_SIZE    = 70
CACHE_DIR    = Path("./crop_cache")

TARGET_CLASSES = [
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
]
EXT = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


# ── 타일 분할 ───────────────────────────────────────────────────
def slice_image(image, tile_size=128, overlap=0.25):
    h, w = image.shape[:2]
    stride = max(1, int(tile_size * (1 - overlap)))
    tiles = []
    for y in range(0, h, stride):
        for x in range(0, w, stride):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            tiles.append((image[y1:y2, x1:x2], x1, y1, x2, y2))
    return tiles


# ── 배경 필터 ───────────────────────────────────────────────────
def is_background(tile_bgr):
    hsv = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    ratio = (((s < 30) & (v < 60)) | ((s < 30) & (v > 200))).mean()
    return ratio > BG_THRESH


# ── 병반 이상 점수 ──────────────────────────────────────────────
def anomaly_score(tile_bgr):
    """
    건강한 잎(H≈75) 대비 얼마나 다른가를 세 가지 지표로 측정.
    점수가 높을수록 병반일 가능성 높음.

    ① Hue 이탈  : 녹색(H=75)에서 멀어질수록 갈변/녹 반점
    ② 채도 분산 : 경계가 생기면 채도가 불균일해짐
    ③ 텍스처    : 반점/병변으로 표면 복잡도 증가
    """
    hsv = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s = hsv[:, :, 0], hsv[:, :, 1]

    # ① Hue 이탈 (0~90 범위, 높을수록 녹색에서 멀어짐)
    hue_dev = np.abs(h - 75.0)
    hue_dev = np.minimum(hue_dev, 180.0 - hue_dev)
    score_hue = float(hue_dev.mean())

    # ② 채도 분산 (sqrt 으로 단위 스케일 조정)
    score_sat = float(np.sqrt(s.var() + 1e-6))

    # ③ 텍스처 (Laplacian 분산, clip 으로 이상치 억제)
    gray = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2GRAY)
    score_tex = float(np.clip(np.sqrt(cv2.Laplacian(gray, cv2.CV_64F).var() + 1e-6), 0, 120))

    return score_hue * 1.0 + score_sat * 0.4 + score_tex * 0.15


# ── 최적 타일 선택 ──────────────────────────────────────────────
def find_best_tile(img_bgr):
    """배경 필터 통과 타일 중 anomaly_score 최고 타일 반환"""
    tiles = slice_image(img_bgr, TILE_SIZE, TILE_OVERLAP)
    best_score, best_region, best_box = -1.0, None, None

    for tile, x1, y1, x2, y2 in tiles:
        if is_background(tile):
            continue
        sc = anomaly_score(tile)
        if sc > best_score:
            best_score = sc
            best_region = tile
            best_box = (x1, y1, x2, y2)

    # 전체 배경 fallback: 중앙 타일 사용
    if best_region is None:
        h, w = img_bgr.shape[:2]
        cy = max(0, h // 2 - TILE_SIZE // 2)
        cx = max(0, w // 2 - TILE_SIZE // 2)
        best_region = img_bgr[cy: cy + TILE_SIZE, cx: cx + TILE_SIZE]
        best_box = (cx, cy, cx + TILE_SIZE, cy + TILE_SIZE)
        best_score = 0.0

    crop_70 = cv2.resize(best_region, (CROP_SIZE, CROP_SIZE),
                         interpolation=cv2.INTER_CUBIC)
    return crop_70, best_box, best_score


# ── 단일 이미지 처리 ────────────────────────────────────────────
def process_image(img_path, out_path):
    img_bgr = cv2.imread(str(img_path))
    if img_bgr is None:
        return None
    crop_70, box, score = find_best_tile(img_bgr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), crop_70)
    return {"box": list(box), "score": round(score, 2)}


# ── 전체 데이터셋 처리 ──────────────────────────────────────────
def process_split(src_dir, dst_split, metadata):
    split_dir = CACHE_DIR / dst_split
    total, saved = 0, 0

    for cls in TARGET_CLASSES:
        cls_src = Path(src_dir) / cls
        if not cls_src.exists():
            continue
        img_paths = [p for p in cls_src.iterdir() if p.suffix in EXT]
        cls_meta = {}

        for img_path in tqdm(img_paths, desc=f"  {cls[:28]:28s}", leave=False):
            out_path = split_dir / cls / img_path.name
            if out_path.exists():
                saved += 1
                total += 1
                continue
            result = process_image(img_path, out_path)
            total += 1
            if result:
                cls_meta[img_path.name] = result
                saved += 1

        if cls_meta:
            metadata[dst_split][cls] = cls_meta

    return total, saved


# ── 샘플 시각화 ─────────────────────────────────────────────────
def save_sample_visualization(n=16):
    """저장된 크롭 중 랜덤 n장을 원본과 나란히 시각화"""
    import random, kagglehub
    dataset_root = Path(kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset"))
    base = dataset_root / "New Plant Diseases Dataset(Augmented)" / "New Plant Diseases Dataset(Augmented)"

    samples = []
    for cls in TARGET_CLASSES:
        crop_dir = CACHE_DIR / "train" / cls
        if not crop_dir.exists():
            continue
        crops = list(crop_dir.iterdir())
        if crops:
            p = random.choice(crops)
            orig = base / "train" / cls / p.name
            if orig.exists():
                samples.append((cls, orig, p))
        if len(samples) >= n:
            break

    rows = (len(samples) + 3) // 4
    fig, axes = plt.subplots(rows, 8, figsize=(20, rows * 3))
    if rows == 1:
        axes = np.expand_dims(axes, 0)

    fig.suptitle(
        "색상+텍스처 분석 크롭 샘플 (원본 | 70×70 크롭)\n"
        "Hue 이탈 + 채도 분산 + 텍스처 점수 기반",
        fontsize=12, fontweight="bold"
    )

    for i, (cls, orig_path, crop_path) in enumerate(samples):
        row, col = divmod(i, 4)
        orig_bgr = cv2.imread(str(orig_path))
        crop_bgr = cv2.imread(str(crop_path))
        if orig_bgr is None or crop_bgr is None:
            continue

        orig_rgb = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

        # 원본에 선택된 박스 표시
        _, box, score = find_best_tile(orig_bgr)
        x1, y1, x2, y2 = box
        orig_vis = orig_rgb.copy()
        cv2.rectangle(orig_vis, (x1, y1), (x2, y2), (255, 60, 60), 2)

        axes[row][col * 2].imshow(orig_vis)
        short = cls.split("___")[-1][:15]
        axes[row][col * 2].set_title(f"{short}\nscore={score:.1f}", fontsize=7)
        axes[row][col * 2].axis("off")

        axes[row][col * 2 + 1].imshow(crop_rgb)
        axes[row][col * 2 + 1].set_title(f"70×70 크롭", fontsize=7)
        axes[row][col * 2 + 1].axis("off")

    plt.tight_layout()
    out = "./precompute_crops_sample.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"샘플 시각화 저장: {out}")


# ── main ────────────────────────────────────────────────────────
def main():
    import kagglehub
    dataset_root = Path(kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset"))
    base = dataset_root / "New Plant Diseases Dataset(Augmented)" / "New Plant Diseases Dataset(Augmented)"
    train_dir = base / "train"
    val_dir   = base / "valid"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {"train": {}, "val": {}}

    print(f"저장 경로: {CACHE_DIR.resolve()}\n")

    print("[Train 처리 중]")
    t0 = time.time()
    tr_total, tr_saved = process_split(train_dir, "train", metadata)
    print(f"  완료: {tr_saved}/{tr_total}장  ({time.time()-t0:.0f}초)\n")

    print("[Val 처리 중]")
    t0 = time.time()
    va_total, va_saved = process_split(val_dir, "val", metadata)
    print(f"  완료: {va_saved}/{va_total}장  ({time.time()-t0:.0f}초)\n")

    meta_path = CACHE_DIR / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"메타데이터 저장: {meta_path}")

    print("\n[샘플 시각화 생성 중]")
    save_sample_visualization(n=16)

    print(f"\n{'='*50}")
    print(f"[완료]")
    print(f"  Train : {tr_saved:,}장  →  {CACHE_DIR/'train'}")
    print(f"  Val   : {va_saved:,}장  →  {CACHE_DIR/'val'}")
    print(f"  메타  : {meta_path}")
    print(f"  시각화: ./precompute_crops_sample.png")


if __name__ == "__main__":
    main()
