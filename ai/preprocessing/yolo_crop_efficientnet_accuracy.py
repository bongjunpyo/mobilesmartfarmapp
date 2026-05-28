"""
색상+텍스처 크롭 캐시 → EfficientNet-B3 정확도 분석
- precompute_crops.py 로 사전 저장된 70×70 크롭 사용 (YOLO 불필요)
- CosineAnnealingLR, 20,000장, 10 epochs
"""
import copy
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import EfficientNet_B3_Weights, efficientnet_b3
from tqdm.auto import tqdm

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {DEVICE}")

IMG_SIZE   = 224
BATCH_SIZE = 32
NUM_EPOCHS = 10
MAX_TRAIN  = 20000
MAX_VAL    = 4000
CACHE_DIR  = Path("./crop_cache")
SAVE_PATH  = Path("./best_crop_model.pth")

MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]

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
CLASS_TO_IDX = {c: i for i, c in enumerate(TARGET_CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(TARGET_CLASSES)}


# ── Dataset (캐시에서 로드) ──────────────────────────────────────
class CropCacheDataset(Dataset):
    EXT = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

    def __init__(self, split, transform=None, max_total=None):
        self.transform = transform
        self.samples = []
        split_dir = CACHE_DIR / split

        if not split_dir.exists():
            raise FileNotFoundError(
                f"캐시 없음: {split_dir}\n"
                "먼저 precompute_crops.py 를 실행하세요."
            )

        for cls in TARGET_CLASSES:
            cls_dir = split_dir / cls
            if not cls_dir.exists():
                continue
            for p in cls_dir.iterdir():
                if p.suffix in self.EXT:
                    self.samples.append((p, CLASS_TO_IDX[cls]))

        if max_total and len(self.samples) > max_total:
            rng = np.random.default_rng(SEED)
            idx = rng.choice(len(self.samples), size=max_total, replace=False)
            self.samples = [self.samples[i] for i in sorted(idx.tolist())]

        print(f"  {split:5s}: {len(self.samples):,}장")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        p, lbl = self.samples[idx]
        # 저장된 70×70 크롭을 224×224로 업스케일
        img = Image.open(p).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.BICUBIC)
        if self.transform:
            img = self.transform(img)
        return img, lbl


# ── 모델 ────────────────────────────────────────────────────────
def create_effnet():
    m = efficientnet_b3(weights=EfficientNet_B3_Weights.DEFAULT)
    m.classifier[1] = nn.Sequential(
        nn.Dropout(0.3, inplace=True),
        nn.Linear(m.classifier[1].in_features, len(TARGET_CLASSES)),
    )
    return m


# ── main ────────────────────────────────────────────────────────
def main():
    train_tf = transforms.Compose([
        transforms.RandomHorizontalFlip(0.5),
        transforms.RandomVerticalFlip(0.2),
        transforms.RandomRotation(15),
        transforms.ColorJitter(0.3, 0.3, 0.3, 0.1),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    val_tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    print("[Dataset 로드]")
    train_ds = CropCacheDataset("train", train_tf, MAX_TRAIN)
    val_ds   = CropCacheDataset("val",   val_tf,   MAX_VAL)

    # 클래스 가중치
    dist = defaultdict(int)
    for _, lbl in train_ds.samples:
        dist[lbl] += 1
    counts = np.array([dist.get(i, 1) for i in range(len(TARGET_CLASSES))], dtype=np.float32)
    inv = 1.0 / counts
    loss_w = torch.tensor(inv / inv.sum() * len(TARGET_CLASSES)).to(DEVICE)

    model     = create_effnet().to(DEVICE)
    criterion = nn.CrossEntropyLoss(weight=loss_w)
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=1e-6)

    train_loader = DataLoader(train_ds, BATCH_SIZE, shuffle=True,  num_workers=0, drop_last=True)
    val_loader   = DataLoader(val_ds,   BATCH_SIZE, shuffle=False, num_workers=0)

    history  = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": [], "lr": []}
    best_acc = 0.0
    best_wts = copy.deepcopy(model.state_dict())

    print(f"\n[EfficientNet-B3 학습]")
    print(f"  epochs={NUM_EPOCHS}  batch={BATCH_SIZE}  lr=1e-4 → CosineAnnealing → 1e-6")
    print(f"  train={len(train_ds):,}장  val={len(val_ds):,}장\n")

    for epoch in range(NUM_EPOCHS):
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1}/{NUM_EPOCHS}  lr={current_lr:.2e}  " + "─"*30)
        history["lr"].append(current_lr)

        for phase in ["train", "val"]:
            loader = train_loader if phase == "train" else val_loader
            model.train() if phase == "train" else model.eval()

            loss_sum, correct, n = 0.0, 0, 0
            for x, y in tqdm(loader, desc=f"  {phase}", leave=False):
                x, y = x.to(DEVICE), y.to(DEVICE)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == "train"):
                    out  = model(x)
                    loss = criterion(out, y)
                    if phase == "train":
                        loss.backward()
                        optimizer.step()
                loss_sum += loss.item() * x.size(0)
                correct  += (out.argmax(1) == y).sum().item()
                n        += x.size(0)

            acc        = correct / max(1, n)
            epoch_loss = loss_sum / max(1, n)
            print(f"  {phase:5s}  loss={epoch_loss:.4f}  acc={acc:.4f}  ({correct}/{n})")
            history[f"{phase}_loss"].append(epoch_loss)
            history[f"{phase}_acc"].append(acc)

            if phase == "val" and acc > best_acc:
                best_acc = acc
                best_wts = copy.deepcopy(model.state_dict())
                torch.save(best_wts, SAVE_PATH)
                print(f"  ★ best 저장 (val_acc={best_acc:.4f})")

        scheduler.step()

    model.load_state_dict(best_wts)

    # ── 학습 곡선 ────────────────────────────────────────────────
    ep = range(1, NUM_EPOCHS + 1)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].plot(ep, [v*100 for v in history["train_acc"]], "o-", label="Train")
    axes[0].plot(ep, [v*100 for v in history["val_acc"]],   "s--", label="Val")
    axes[0].set_title(f"Accuracy  (Best Val: {best_acc*100:.2f}%)")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Accuracy (%)")
    axes[0].set_xticks(list(ep)); axes[0].legend(); axes[0].grid(True, alpha=0.4)

    axes[1].plot(ep, history["train_loss"], "o-", label="Train")
    axes[1].plot(ep, history["val_loss"],   "s--", label="Val")
    axes[1].set_title("Loss")
    axes[1].set_xlabel("Epoch")
    axes[1].set_xticks(list(ep)); axes[1].legend(); axes[1].grid(True, alpha=0.4)

    axes[2].plot(ep, [lr*1e4 for lr in history["lr"]], "^-", color="purple")
    axes[2].set_title("Learning Rate (×10⁻⁴)")
    axes[2].set_xlabel("Epoch"); axes[2].set_ylabel("LR × 10⁻⁴")
    axes[2].set_xticks(list(ep)); axes[2].grid(True, alpha=0.4)

    fig.suptitle(
        f"EfficientNet-B3  |  색상+텍스처 크롭 70×70 → 224×224  |  {NUM_EPOCHS} Epochs\n"
        f"CosineAnnealingLR  |  Best Val Accuracy: {best_acc*100:.2f}%",
        fontsize=12, fontweight="bold",
    )
    plt.tight_layout()
    out_path = "./yolo_crop_efficientnet_accuracy.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\n{'='*50}")
    print("[최종 결과]")
    for i, (ta, va) in enumerate(zip(history["train_acc"], history["val_acc"]), 1):
        mark = " ★" if abs(va - best_acc) < 1e-6 else ""
        print(f"  Epoch {i:2d}: train={ta*100:.2f}%  val={va*100:.2f}%{mark}")
    print(f"\n  Best Val Accuracy : {best_acc:.4f}  ({best_acc*100:.2f}%)")
    print(f"  학습 곡선         : {out_path}")
    print(f"  저장 모델         : {SAVE_PATH}")


if __name__ == "__main__":
    main()
