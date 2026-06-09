"""
YOLO 병반 크롭 과정 시각화
- 각 타일의 배경 비율(BG%) 색상 표시
  · 빨간 = 30% 초과 → 필터 제거
  · 초록 = 선택된 병반 구역 (최고 conf)
  · 노란 = 통과했지만 미선택
- 선택된 70×70 크롭 결과 나란히 표시
"""
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

YOLO_PATH_CANDIDATES = [
    Path("./runs/detect/smartfarm/weights/best.pt"),
    Path("./runs/smartfarm/weights/best.pt"),
    Path("./runs/detect/runs/smartfarm/weights/best.pt"),
    Path("./yolov8s.pt"),
]
CROP_SIZE = 70
YOLO_CONF = 0.10
TILE_SIZE = 128
TILE_OVERLAP = 0.25
BG_THRESH = 0.30
MAX_SAMPLES = 8

COLOR_REMOVED  = (220, 50,  50,  140)  # 빨간 반투명 — 제거
COLOR_SELECTED = (50,  200, 50,  180)  # 초록 반투명 — 선택
COLOR_PASSED   = (240, 200, 30,  100)  # 노란 반투명 — 통과/미선택
BORDER_SEL     = (50,  220, 50)        # 선택 박스 테두리
BORDER_REM     = (220, 50,  50)        # 제거 박스 테두리


def pick_yolo_path():
    for p in YOLO_PATH_CANDIDATES:
        if p.exists():
            return p
    return None


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


def bg_ratio(tile_bgr):
    hsv = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    return float(((s < 30) & (v < 60) | (s < 30) & (v > 200)).mean())


def analyze_image(img_bgr, yolo_model):
    """
    모든 타일을 분석해 상태(제거/선택/통과) + YOLO conf 반환.
    반환: list of dict {x1,y1,x2,y2, bg_pct, conf, status}
    """
    tiles = slice_image(img_bgr, TILE_SIZE, TILE_OVERLAP)
    tile_info = []

    for tile, x1, y1, x2, y2 in tiles:
        bg = bg_ratio(tile)
        best_conf = 0.0
        if bg <= BG_THRESH:
            for r in yolo_model(tile, conf=YOLO_CONF, verbose=False):
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    c = float(box.conf[0])
                    if c > best_conf:
                        best_conf = c
        tile_info.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "bg_pct": bg * 100,
            "conf": best_conf,
            "removed": bg > BG_THRESH,
        })

    # 통과 타일 중 conf 최고 → 선택
    passed = [t for t in tile_info if not t["removed"]]
    if passed:
        best = max(passed, key=lambda t: t["conf"])
        best["selected"] = True
    else:
        # 전체 제거 fallback: conf 무관하게 재계산
        for t in tile_info:
            t["removed"] = False
            tile = img_bgr[t["y1"]:t["y2"], t["x1"]:t["x2"]]
            best_conf = 0.0
            for r in yolo_model(tile, conf=YOLO_CONF, verbose=False):
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    c = float(box.conf[0])
                    if c > best_conf:
                        best_conf = c
            t["conf"] = best_conf
        best = max(tile_info, key=lambda t: t["conf"])
        best["selected"] = True

    for t in tile_info:
        if t.get("selected"):
            t["status"] = "selected"
        elif t["removed"]:
            t["status"] = "removed"
        else:
            t["status"] = "passed"

    return tile_info


def draw_tile_overlay(img_rgb, tile_info):
    """타일별 상태를 반투명 색상으로 오버레이"""
    overlay = img_rgb.copy().astype(np.float32)
    label_img = img_rgb.copy()

    color_map = {
        "removed":  np.array([220, 50,  50],  dtype=np.float32),
        "selected": np.array([50,  200, 50],  dtype=np.float32),
        "passed":   np.array([240, 200, 30],  dtype=np.float32),
    }
    alpha_map = {"removed": 0.40, "selected": 0.45, "passed": 0.25}
    border_map = {
        "removed":  (220, 50,  50),
        "selected": (30,  220, 30),
        "passed":   (200, 170, 20),
    }
    thick_map = {"removed": 1, "selected": 3, "passed": 1}

    for t in tile_info:
        x1, y1, x2, y2 = t["x1"], t["y1"], t["x2"], t["y2"]
        alpha = alpha_map[t["status"]]
        color = color_map[t["status"]]
        overlay[y1:y2, x1:x2] = (
            overlay[y1:y2, x1:x2] * (1 - alpha) + color * alpha
        )

    result = np.clip(overlay, 0, 255).astype(np.uint8)

    for t in tile_info:
        x1, y1, x2, y2 = t["x1"], t["y1"], t["x2"], t["y2"]
        cv2.rectangle(result, (x1, y1), (x2 - 1, y2 - 1),
                      border_map[t["status"]], thick_map[t["status"]])
        # conf 레이블 (선택·통과 타일만)
        if t["status"] != "removed":
            label = f"{t['conf']:.2f}"
            cv2.putText(result, label, (x1 + 3, y2 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.30, border_map[t["status"]], 1)
        # BG% 레이블 (제거 타일)
        else:
            label = f"BG{t['bg_pct']:.0f}%"
            cv2.putText(result, label, (x1 + 2, y1 + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.30, (220, 80, 80), 1)

    return result


def get_selected_crop_70(img_bgr, tile_info):
    sel = next(t for t in tile_info if t["status"] == "selected")
    region = img_bgr[sel["y1"]:sel["y2"], sel["x1"]:sel["x2"]]
    resized = cv2.resize(region, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(resized, cv2.COLOR_BGR2RGB), sel


def main():
    import kagglehub
    dataset_root = Path(kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset"))
    test_dir = dataset_root / "test" / "test"

    yolo_path = pick_yolo_path()
    if yolo_path is None:
        raise FileNotFoundError("YOLO 가중치를 찾을 수 없습니다.")
    print(f"YOLO: {yolo_path}")

    from ultralytics import YOLO as UltralyticsYOLO
    yolo_model = UltralyticsYOLO(str(yolo_path))

    all_imgs = sorted(
        list(test_dir.glob("*.JPG"))
        + list(test_dir.glob("*.jpg"))
        + list(test_dir.glob("*.png"))
    )[:MAX_SAMPLES * 2]

    records = []
    for img_path in all_imgs:
        if len(records) >= MAX_SAMPLES:
            break
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        tile_info = analyze_image(img_bgr, yolo_model)
        overlay = draw_tile_overlay(img_rgb, tile_info)
        crop_70, sel = get_selected_crop_70(img_bgr, tile_info)

        n_removed  = sum(1 for t in tile_info if t["status"] == "removed")
        n_passed   = sum(1 for t in tile_info if t["status"] == "passed")
        records.append({
            "path": img_path,
            "img_rgb": img_rgb,
            "overlay": overlay,
            "crop_70": crop_70,
            "tile_info": tile_info,
            "sel": sel,
            "n_removed": n_removed,
            "n_passed": n_passed,
        })
        print(f"  {img_path.name:35s} | 타일 {len(tile_info)}개: "
              f"제거={n_removed} 통과={n_passed} 선택conf={sel['conf']:.2f}")

    # ── 시각화 ────────────────────────────────────────────────
    fig, axes = plt.subplots(len(records), 3, figsize=(13, len(records) * 3.8))
    if len(records) == 1:
        axes = np.expand_dims(axes, 0)

    fig.suptitle(
        "YOLO 병반 크롭 과정 시각화 (배경 필터 30% 기준)\n"
        "빨간=배경 제거 | 초록=선택된 병반 구역 | 노란=통과·미선택",
        fontsize=12, fontweight="bold",
    )

    for i, rec in enumerate(records):
        sel = rec["sel"]

        # 열 0: 원본
        axes[i][0].imshow(rec["img_rgb"])
        axes[i][0].set_title(f"원본\n{rec['path'].name}", fontsize=8)
        axes[i][0].axis("off")

        # 열 1: 타일 오버레이
        axes[i][1].imshow(rec["overlay"])
        axes[i][1].set_title(
            f"타일 분석 ({len(rec['tile_info'])}개)\n"
            f"제거={rec['n_removed']}  통과={rec['n_passed']}  선택conf={sel['conf']:.2f}",
            fontsize=8,
        )
        axes[i][1].axis("off")

        # 열 2: 선택된 70×70 크롭
        axes[i][2].imshow(rec["crop_70"])
        axes[i][2].set_title(
            f"선택 병반 구역 → 70×70\n"
            f"위치: ({sel['x1']},{sel['y1']})-({sel['x2']},{sel['y2']})  "
            f"BG={sel['bg_pct']:.1f}%",
            fontsize=8,
        )
        axes[i][2].axis("off")

    legend_patches = [
        mpatches.Patch(color=(220/255, 50/255,  50/255),  label="제거 (BG > 30%)"),
        mpatches.Patch(color=(50/255,  200/255, 50/255),  label="선택 (최고 conf)"),
        mpatches.Patch(color=(240/255, 200/255, 30/255),  label="통과·미선택"),
    ]
    fig.legend(handles=legend_patches, loc="lower center",
               ncol=3, fontsize=9, bbox_to_anchor=(0.5, -0.005))

    plt.tight_layout()
    out_path = "./yolo_crop_visualization.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n{out_path} 저장 완료")


if __name__ == "__main__":
    main()
