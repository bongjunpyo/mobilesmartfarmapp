import os
import shutil
import yaml
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
import kagglehub
from ultralytics import YOLO

# ── 경로 설정 ──────────────────────────────────────────────
YOLO_DIR = Path('./yolo_dataset')
RUNS_DIR = Path('./runs')
RESULT_IMG = './smartfarm_result.png'

# ── 0. 클래스 정의 (23개) ─────────────────────────────────
CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy',
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy',
    'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
    'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight',
    'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot',
    'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus',
    'Tomato___healthy',
]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}
print(f'클래스 수: {len(CLASS_NAMES)}')


# ── 1. 데이터셋 다운로드 ──────────────────────────────────
downloaded_root = kagglehub.dataset_download('vipoooool/new-plant-diseases-dataset')
dataset_path = Path(downloaded_root) / 'New Plant Diseases Dataset(Augmented)'

if not dataset_path.is_dir():
    raise FileNotFoundError(
        f"'{dataset_path}' 없음. '{downloaded_root}' 내용: {os.listdir(downloaded_root)}"
    )
print('데이터셋 경로:', dataset_path)


# ── 2. YOLO 디렉토리 구조 생성 ────────────────────────────
BASE_DIR = dataset_path / 'New Plant Diseases Dataset(Augmented)'
split_map = {'train': 'train', 'valid': 'val'}

for dst_split in split_map.values():
    (YOLO_DIR / dst_split / 'images').mkdir(parents=True, exist_ok=True)
    (YOLO_DIR / dst_split / 'labels').mkdir(parents=True, exist_ok=True)

for src_split, dst_split in split_map.items():
    src_dir = BASE_DIR / src_split
    count = 0
    if not src_dir.is_dir():
        print(f'Warning: {src_dir} 없음, 건너뜀')
        continue
    for class_dir in src_dir.iterdir():
        if not class_dir.is_dir() or class_dir.name not in CLASS_TO_IDX:
            continue
        class_id = CLASS_TO_IDX[class_dir.name]
        for img_path in class_dir.glob('*.jpg'):
            dst_img = YOLO_DIR / dst_split / 'images' / img_path.name
            dst_lbl = YOLO_DIR / dst_split / 'labels' / (img_path.stem + '.txt')
            shutil.copy(img_path, dst_img)
            dst_lbl.write_text(f'{class_id} 0.5 0.5 1.0 1.0\n')
            count += 1
    print(f'{dst_split}: {count}장 완료')


# ── 3. data.yaml 생성 ─────────────────────────────────────
data_config = {
    'path': str(YOLO_DIR.resolve()),
    'train': 'train/images',
    'val': 'val/images',
    'nc': len(CLASS_NAMES),
    'names': CLASS_NAMES,
}
with open(YOLO_DIR / 'data.yaml', 'w') as f:
    yaml.dump(data_config, f, allow_unicode=True)
print('data.yaml 생성 완료')


# ── 4. YOLOv8 학습 ────────────────────────────────────────
# GPU 없으면 device='cpu' 로 변경
model = YOLO('yolov8s.pt')
model.train(
    data=str(YOLO_DIR / 'data.yaml'),
    epochs=30,
    imgsz=224,
    batch=32,
    lr0=1e-4,
    weight_decay=0.01,
    optimizer='AdamW',
    project=str(RUNS_DIR),
    name='smartfarm',
    exist_ok=True,
    device='mps',
    flipud=0.2,
    fliplr=0.5,
    degrees=15,
    hsv_s=0.3,
    hsv_v=0.3,
)


# ── 5. 슬라이딩 윈도우 추론 ──────────────────────────────
def slice_image(image, tile_size=640, overlap=0.2):
    h, w = image.shape[:2]
    stride = int(tile_size * (1 - overlap))
    tiles = []
    for y in range(0, h, stride):
        for x in range(0, w, stride):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            tiles.append((image[y1:y2, x1:x2], x1, y1))
    return tiles


@dataclass
class Det:
    x1: float; y1: float; x2: float; y2: float
    conf: float; cls_id: int; cls_name: str


def infer_on_tiles(model, image, tile_size=640, overlap=0.2, conf=0.25):
    dets = []
    for tile, ox, oy in slice_image(image, tile_size, overlap):
        for r in model(tile, conf=conf, verbose=False):
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                dets.append(Det(
                    x1=x1+ox, y1=y1+oy, x2=x2+ox, y2=y2+oy,
                    conf=float(box.conf[0]),
                    cls_id=int(box.cls[0]),
                    cls_name=model.names[int(box.cls[0])],
                ))
    return dets


def apply_nms(dets, iou_threshold=0.5):
    if not dets:
        return []
    boxes = np.array([[d.x1, d.y1, d.x2, d.y2] for d in dets], dtype=np.float32)
    scores = np.array([d.conf for d in dets], dtype=np.float32)
    cls_ids = np.array([d.cls_id for d in dets])
    keep = []
    for cid in np.unique(cls_ids):
        mask = cls_ids == cid
        idx = np.where(mask)[0]
        picked = cv2.dnn.NMSBoxes(
            boxes[mask].tolist(), scores[mask].tolist(),
            score_threshold=0.0, nms_threshold=iou_threshold,
        )
        if len(picked) > 0:
            keep.extend(idx[picked.flatten()])
    return [dets[i] for i in keep]


def draw_results(image, dets):
    out = image.copy()
    colors = {}
    for d in dets:
        if d.cls_id not in colors:
            np.random.seed(d.cls_id)
            colors[d.cls_id] = tuple(np.random.randint(50, 230, 3).tolist())
        c = colors[d.cls_id]
        cv2.rectangle(out, (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2)), c, 2)
        cv2.putText(out, f'{d.cls_name.split("___")[-1][:15]} {d.conf:.2f}',
                    (int(d.x1), int(d.y1)-6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 2)
    return out


def run_smartfarm_detection(image_path,
                            model_path='./runs/smartfarm/weights/best.pt',
                            tile_size=640, overlap=0.2, conf=0.25, iou=0.5):
    mdl = YOLO(model_path)
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]
    tiles = slice_image(image, tile_size, overlap)
    print(f'원본: {w}x{h} | 타일: {len(tiles)}')

    raw_dets = infer_on_tiles(mdl, image, tile_size, overlap, conf)
    final_dets = apply_nms(raw_dets, iou)
    print(f'Raw: {len(raw_dets)} → NMS 후: {len(final_dets)}')

    for cls, cnt in Counter(d.cls_name for d in final_dets).most_common():
        print(f'  {cls}: {cnt}건')

    result_img = draw_results(image_rgb, final_dets)
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    axes[0].imshow(image_rgb); axes[0].set_title('원본'); axes[0].axis('off')
    axes[1].imshow(result_img); axes[1].set_title(f'탐지 결과 ({len(final_dets)}건)'); axes[1].axis('off')
    plt.tight_layout()
    plt.savefig(RESULT_IMG, dpi=150)
    plt.show()
    return final_dets


# 추론 실행 시 주석 해제
# dets = run_smartfarm_detection('./greenhouse.jpg')
