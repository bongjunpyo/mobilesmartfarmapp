"""
YOLO 탐지 기반 나뭇잎 병반 크롭 → 70x70 화질 확인
- 128px 슬라이딩 윈도우로 이미지를 구역으로 분할
- YOLO confidence가 가장 높은 구역 = 병반 부위로 판단
- 그 구역(128x128)을 70x70으로 리사이즈
- 원본 구역 vs 70x70 화질 비교 (PSNR)
"""
import math
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from PIL import Image

# 한글 폰트
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

YOLO_PATH_CANDIDATES = [
    Path("./runs/detect/smartfarm/weights/best.pt"),
    Path("./runs/smartfarm/weights/best.pt"),
    Path("./runs/detect/runs/smartfarm/weights/best.pt"),
    Path("./yolov8s.pt"),
]
CROP_SIZE = 70
YOLO_CONF = 0.10        # 병반 구역 탐지 임계값
TILE_SIZE = 128         # 병반 단위 탐지를 위해 작은 타일 사용
TILE_OVERLAP = 0.25
MAX_SAMPLES = 8
MAX_CROPS_PER_IMAGE = 3


def pick_yolo_path():
    for p in YOLO_PATH_CANDIDATES:
        if p.exists():
            return p
    return None


def slice_image(image, tile_size=128, overlap=0.25):
    """이미지를 tile_size 크기 타일로 분할, 각 타일과 오프셋 반환"""
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


def is_background(tile_bgr, s_thresh=30, v_low=60, v_high=200):
    """
    채도(S) + 명도(V) 조합으로 배경 타일 판별.
    - 어두운 배경: S < s_thresh AND V < v_low
    - 밝은(흰) 배경: S < s_thresh AND V > v_high
    픽셀 단위로 비율을 계산해 50% 이상이 배경이면 True 반환.
    """
    hsv = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    dark_bg  = (s < s_thresh) & (v < v_low)
    bright_bg = (s < s_thresh) & (v > v_high)
    bg_ratio = (dark_bg | bright_bg).mean()
    return bg_ratio > 0.30


def find_disease_regions(img_bgr, yolo_model, conf=0.10, tile_size=128, overlap=0.25, max_crops=3):
    """
    1단계: 채도+명도 필터로 배경 타일 제거
    2단계: 남은 타일에서 YOLO confidence 기준 상위 병반 구역 반환
    모든 타일이 배경으로 판별되면 필터 없이 재시도(fallback)
    """
    tiles = slice_image(img_bgr, tile_size, overlap)
    scored = []

    for tile, x1, y1, x2, y2 in tiles:
        # 배경 타일 제거
        if is_background(tile):
            continue
        best_conf = 0.0
        for r in yolo_model(tile, conf=conf, verbose=False):
            if r.boxes is None:
                continue
            for box in r.boxes:
                c = float(box.conf[0])
                if c > best_conf:
                    best_conf = c
        scored.append((best_conf, x1, y1, x2, y2))

    # 모든 타일이 배경으로 필터링된 경우 필터 없이 재시도
    if not scored:
        for tile, x1, y1, x2, y2 in tiles:
            best_conf = 0.0
            for r in yolo_model(tile, conf=conf, verbose=False):
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    c = float(box.conf[0])
                    if c > best_conf:
                        best_conf = c
            scored.append((best_conf, x1, y1, x2, y2))

    # confidence 높은 순 정렬
    scored.sort(key=lambda s: s[0], reverse=True)

    crops = []
    for best_conf, x1, y1, x2, y2 in scored[:max_crops]:
        region = img_bgr[y1:y2, x1:x2]
        if region.size == 0:
            continue
        crop_rgb = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(region, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_CUBIC)
        crop_70_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        crops.append({
            "box": (x1, y1, x2, y2),
            "conf": best_conf,
            "crop_rgb": crop_rgb,
            "crop_70_rgb": crop_70_rgb,
            "orig_w": x2 - x1,
            "orig_h": y2 - y1,
        })

    if not crops:
        # 탐지 전혀 없으면 이미지 중앙 128×128 크롭
        h, w = img_bgr.shape[:2]
        cy, cx = max(0, h // 2 - tile_size // 2), max(0, w // 2 - tile_size // 2)
        region = img_bgr[cy: cy + tile_size, cx: cx + tile_size]
        crop_rgb = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(region, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_CUBIC)
        crop_70_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        crops.append({
            "box": (cx, cy, cx + tile_size, cy + tile_size),
            "conf": 0.0,
            "crop_rgb": crop_rgb,
            "crop_70_rgb": crop_70_rgb,
            "orig_w": tile_size,
            "orig_h": tile_size,
        })

    return crops


def psnr(orig_rgb, resized_70_rgb):
    """크롭 원본을 70×70 경유 후 원본 크기로 복원, PSNR 계산"""
    h, w = orig_rgb.shape[:2]
    if h == 0 or w == 0:
        return 0.0
    restored = cv2.resize(
        cv2.cvtColor(resized_70_rgb, cv2.COLOR_RGB2BGR),
        (w, h), interpolation=cv2.INTER_CUBIC,
    )
    restored_rgb = cv2.cvtColor(restored, cv2.COLOR_BGR2RGB)
    mse = np.mean((orig_rgb.astype(np.float32) - restored_rgb.astype(np.float32)) ** 2)
    if mse == 0:
        return 100.0
    return 20 * math.log10(255.0 / math.sqrt(mse))


def sharpness(img_rgb):
    """Laplacian 분산 — 높을수록 선명"""
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def draw_all_tiles(img_rgb, crops, tile_size=128):
    """모든 타일 경계 + 선택된 병반 구역 표시"""
    out = img_rgb.copy()
    # 회색으로 타일 격자
    h, w = out.shape[:2]
    stride = max(1, int(tile_size * (1 - TILE_OVERLAP)))
    for y in range(0, h, stride):
        for x in range(0, w, stride):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            cv2.rectangle(out, (x1, y1), (x2 - 1, y2 - 1), (180, 180, 180), 1)
    # 빨간색으로 선택된 구역(confidence 최고)
    if crops:
        bx1, by1, bx2, by2 = crops[0]["box"]
        cv2.rectangle(out, (bx1, by1), (bx2 - 1, by2 - 1), (255, 60, 60), 2)
        cv2.putText(out, f"conf={crops[0]['conf']:.2f}",
                    (bx1, max(by1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 60, 60), 1)
    return out


def main():
    import kagglehub
    dataset_root = Path(kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset"))
    test_dir = dataset_root / "test" / "test"

    yolo_path = pick_yolo_path()
    if yolo_path is None:
        raise FileNotFoundError("YOLO 가중치를 찾을 수 없습니다.")
    print(f"YOLO: {yolo_path}")
    if yolo_path.name == "yolov8s.pt":
        print("  ⚠ 기본 yolov8s.pt 사용 (학습된 best.pt 미발견)")

    from ultralytics import YOLO as UltralyticsYOLO
    yolo_model = UltralyticsYOLO(str(yolo_path))

    all_imgs = sorted(
        list(test_dir.glob("*.jpg"))
        + list(test_dir.glob("*.JPG"))
        + list(test_dir.glob("*.png"))
    )

    results = []
    for img_path in all_imgs:
        if len(results) >= MAX_SAMPLES:
            break
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        crops = find_disease_regions(
            img_bgr, yolo_model,
            conf=YOLO_CONF, tile_size=TILE_SIZE,
            overlap=TILE_OVERLAP, max_crops=MAX_CROPS_PER_IMAGE,
        )
        results.append({
            "path": img_path,
            "img_rgb": img_rgb,
            "det_img": draw_all_tiles(img_rgb, crops, TILE_SIZE),
            "crops": crops,
        })
        print(f"  [{len(results):>2}/{MAX_SAMPLES}] {img_path.name:35s} | "
              f"병반 구역 최고 conf={crops[0]['conf']:.2f}, "
              f"크롭 크기={crops[0]['orig_w']}×{crops[0]['orig_h']}")

    if not results:
        print("처리할 이미지가 없습니다.")
        return

    # ── 시각화 ────────────────────────────────────────────────
    fig, axes = plt.subplots(len(results), 3, figsize=(12, len(results) * 3.6))
    if len(results) == 1:
        axes = np.expand_dims(axes, 0)

    fig.suptitle(
        f"YOLO 병반 구역 크롭(128px 타일) → 70×70 화질 확인\n"
        f"회색=타일 격자 | 빨간=최고 confidence 병반 구역",
        fontsize=12, fontweight="bold",
    )

    psnr_all = []
    for i, res in enumerate(results):
        crop = res["crops"][0]
        p_val = psnr(crop["crop_rgb"], crop["crop_70_rgb"])
        sharp_orig = sharpness(crop["crop_rgb"])
        sharp_70 = sharpness(crop["crop_70_rgb"])
        psnr_all.append(p_val)

        # 열 0: 원본 + 타일/병반 표시
        axes[i][0].imshow(res["det_img"])
        axes[i][0].set_title(f"원본 + 타일 분할\n{res['path'].name}", fontsize=8)
        axes[i][0].axis("off")

        # 열 1: 병반 구역 원본 (128×128)
        axes[i][1].imshow(crop["crop_rgb"])
        axes[i][1].set_title(
            f"병반 구역 크롭 ({crop['orig_w']}×{crop['orig_h']}px)\n"
            f"선명도={sharp_orig:.1f}  conf={crop['conf']:.2f}",
            fontsize=8,
        )
        axes[i][1].axis("off")

        # 열 2: 70×70 리사이즈
        psnr_color = "#2ECC71" if p_val >= 30 else "#E67E22" if p_val >= 25 else "#E74C3C"
        axes[i][2].imshow(crop["crop_70_rgb"])
        axes[i][2].set_title(
            f"70×70 리사이즈\nPSNR={p_val:.1f}dB  선명도={sharp_70:.1f}",
            fontsize=8, color=psnr_color,
        )
        axes[i][2].axis("off")

    plt.tight_layout()
    out_path = "./yolo_crop_quality_check.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n{out_path} 저장 완료")

    # ── 요약 ─────────────────────────────────────────────────
    print(f"\n[화질 분석 요약]")
    print(f"  분석 이미지  : {len(results)}장")
    print(f"  PSNR 평균    : {np.mean(psnr_all):.2f} dB")
    print(f"  PSNR 최솟값  : {np.min(psnr_all):.2f} dB")
    print(f"  PSNR 최댓값  : {np.max(psnr_all):.2f} dB")

    n_good = sum(1 for v in psnr_all if v >= 30)
    n_ok   = sum(1 for v in psnr_all if 25 <= v < 30)
    n_bad  = sum(1 for v in psnr_all if v < 25)
    print(f"\n  ≥30dB (고화질): {n_good}장")
    print(f"  25~30dB (양호): {n_ok}장")
    print(f"  <25dB  (저화질): {n_bad}장")
    print(f"\n  기준 (128×128 → 70×70 기준):")
    print(f"    ≥30 dB → 육안 구분 거의 불가 (고화질 유지)")
    print(f"    25~30 dB → 약간 저하 (허용 가능)")
    print(f"    <25 dB → 화질 손상 (병반 구역이 너무 작거나 저대비)")
    if n_bad > 0:
        print(f"\n  ⚠ 화질 저하 {n_bad}장: 해당 구역에 뚜렷한 병반이 없거나")
        print(f"    타일 크기 대비 세부 패턴이 단순한 경우입니다.")


if __name__ == "__main__":
    main()
