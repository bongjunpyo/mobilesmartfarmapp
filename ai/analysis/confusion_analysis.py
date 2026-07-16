"""best_crop_model.onnx 오분류 분석.

ai/test_images/ 의 라벨 있는 이미지 전체를 onnxruntime CPU로 추론해
혼동행렬·클래스별 지표·오분류 목록을 analysis/ 아래에 저장한다.

전처리는 학습 스크립트(yolo_crop_efficientnet_accuracy.py)와 동일:
224×224 BICUBIC 리사이즈 → [0,1] → ImageNet MEAN/STD 정규화.

실행:
    ~/venv/bin/python confusion_analysis.py
"""

import csv
import re
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent          # ai/analysis/
AI_DIR = BASE_DIR.parent                            # ai/
MODEL_PATH = AI_DIR / "model" / "best_crop_model.onnx"
IMAGE_DIR = AI_DIR / "test_images"

IMG_SIZE = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# precompute_crops.py 의 TARGET_CLASSES 와 동일한 순서 (모델 출력 인덱스)
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

# 테스트 이미지 파일명 접두어 → 정답 클래스
PREFIX_TO_CLASS = {
    "AppleCedarRust": "Apple___Cedar_apple_rust",
    "AppleScab": "Apple___Apple_scab",
    "CornCommonRust": "Corn_(maize)___Common_rust_",
    "PotatoEarlyBlight": "Potato___Early_blight",
    "PotatoHealthy": "Potato___healthy",
    "TomatoEarlyBlight": "Tomato___Early_blight",
    "TomatoHealthy": "Tomato___healthy",
    "TomatoYellowCurlVirus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
}


# ── 전처리 · 추론 ───────────────────────────────────────────────
def preprocess(path):
    img = Image.open(path).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.BICUBIC)
    x = np.asarray(img, dtype=np.float32) / 255.0
    x = (x - MEAN) / STD
    return x.transpose(2, 0, 1)[None]  # (1, 3, 224, 224)


def collect_samples():
    samples = []
    for p in sorted(IMAGE_DIR.glob("*.JPG")):
        m = re.match(r"([A-Za-z]+?)\d+$", p.stem)
        if not m or m.group(1) not in PREFIX_TO_CLASS:
            print(f"  스킵 (라벨 미정의): {p.name}")
            continue
        samples.append((p, PREFIX_TO_CLASS[m.group(1)]))
    return samples


def run_inference(samples):
    sess = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
    rows = []
    for path, true_cls in samples:
        logits = sess.run(["output"], {"input": preprocess(path)})[0][0]
        exp = np.exp(logits - logits.max())
        probs = exp / exp.sum()
        pred_idx = int(probs.argmax())
        rows.append({
            "file": path.name,
            "true": true_cls,
            "pred": TARGET_CLASSES[pred_idx],
            "conf": float(probs[pred_idx]),
            "true_conf": float(probs[TARGET_CLASSES.index(true_cls)]),
        })
    return rows


# ── 집계 ────────────────────────────────────────────────────────
def per_class_metrics(rows):
    """precision/recall/F1. precision 분모는 해당 클래스로 예측된 전체 건수."""
    classes = sorted({r["true"] for r in rows} | {r["pred"] for r in rows},
                     key=TARGET_CLASSES.index)
    metrics = []
    for cls in classes:
        tp = sum(1 for r in rows if r["true"] == cls and r["pred"] == cls)
        fn = sum(1 for r in rows if r["true"] == cls and r["pred"] != cls)
        fp = sum(1 for r in rows if r["true"] != cls and r["pred"] == cls)
        support = tp + fn
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics.append({"class": cls, "support": support, "predicted": tp + fp,
                        "precision": precision, "recall": recall, "f1": f1})
    return classes, metrics


def confusion_matrix(rows, classes):
    idx = {c: i for i, c in enumerate(classes)}
    cm = np.zeros((len(classes), len(classes)), dtype=int)
    for r in rows:
        cm[idx[r["true"]], idx[r["pred"]]] += 1
    return cm


# ── 산출물 저장 ─────────────────────────────────────────────────
def save_confusion_png(cm, classes, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    short = [c.replace("___", "\n") for c in classes]
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(classes)), short, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(classes)), short, fontsize=8)
    for i in range(len(classes)):
        for j in range(len(classes)):
            if cm[i, j]:
                color = "white" if cm[i, j] > cm.max() * 0.6 else "black"
                ax.text(j, i, cm[i, j], ha="center", va="center", color=color)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix — test_images ({cm.sum()} images, ONNX CPU)")
    fig.colorbar(im, shrink=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_metrics_csv(metrics, out_path):
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        w.writeheader()
        for m in metrics:
            w.writerow({**m, "precision": f"{m['precision']:.4f}",
                        "recall": f"{m['recall']:.4f}", "f1": f"{m['f1']:.4f}"})


def save_report_md(rows, metrics, out_path):
    total = len(rows)
    correct = sum(1 for r in rows if r["true"] == r["pred"])
    wrong = [r for r in rows if r["true"] != r["pred"]]
    lines = [
        "# 오분류 분석 결과 (자동 생성)",
        "",
        f"- 모델: `model/best_crop_model.onnx` (onnxruntime CPU)",
        f"- 대상: `test_images/` 라벨 이미지 {total}장",
        f"- 전체 정확도: **{correct}/{total} ({correct / total:.1%})**",
        "",
        "## 클래스별 지표",
        "",
        "| 클래스 | support | 예측 건수 | precision | recall | F1 |",
        "|---|---|---|---|---|---|",
    ]
    for m in metrics:
        lines.append(
            f"| {m['class']} | {m['support']} | {m['predicted']} "
            f"| {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} |")
    lines += ["", "## 오분류 사례", ""]
    if wrong:
        lines += ["| 파일 | 정답 | 예측 | 예측 확신도 | 정답 확률 |", "|---|---|---|---|---|"]
        for r in wrong:
            lines.append(f"| {r['file']} | {r['true']} | {r['pred']} "
                         f"| {r['conf']:.2f} | {r['true_conf']:.2f} |")
    else:
        lines.append("오분류 없음.")
    lines += ["", "## 전체 예측 로그", "",
              "| 파일 | 정답 | 예측 | 확신도 | 정오 |", "|---|---|---|---|---|"]
    for r in rows:
        mark = "O" if r["true"] == r["pred"] else "X"
        lines.append(f"| {r['file']} | {r['true']} | {r['pred']} | {r['conf']:.2f} | {mark} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    samples = collect_samples()
    print(f"라벨 이미지 {len(samples)}장 추론 시작 (CPU)")
    rows = run_inference(samples)

    classes, metrics = per_class_metrics(rows)
    cm = confusion_matrix(rows, classes)

    save_confusion_png(cm, classes, BASE_DIR / "confusion_matrix.png")
    save_metrics_csv(metrics, BASE_DIR / "class_metrics.csv")
    save_report_md(rows, metrics, BASE_DIR / "RESULTS.md")

    correct = sum(1 for r in rows if r["true"] == r["pred"])
    print(f"정확도: {correct}/{len(rows)} ({correct / len(rows):.1%})")
    print("산출물: confusion_matrix.png / class_metrics.csv / RESULTS.md")
    for r in rows:
        if r["true"] != r["pred"]:
            print(f"  오분류: {r['file']}  {r['true']} → {r['pred']} ({r['conf']:.2f})")


if __name__ == "__main__":
    main()
