"""Verify the four frozen checkpoints by predicting and evaluating a fixed CPU sample."""

import argparse
from collections import Counter
import csv
import math
from pathlib import Path
import random
import sys

from evaluate_helmet import CLASSES, EVALUATION, ULTRALYTICS, check_manifests, digest, write_json


SAMPLE_SIZE = 24
SAMPLE_SEED = 42
MODELS = ("v8n", "v8s", "v8m", "v5su")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, default=Path("manifests"))
    parser.add_argument("--weights", type=Path, required=True, help="Root containing v8n/best.pt, v8s/best.pt, v8m/best.pt and v5su/best.pt")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import torch
    import ultralytics

    if ultralytics.__version__ != ULTRALYTICS:
        raise RuntimeError(f"Install ultralytics=={ULTRALYTICS}, found {ultralytics.__version__}")
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    root = args.data_root.resolve()
    frozen = check_manifests(root, args.manifests.resolve())
    paths = random.Random(SAMPLE_SEED).sample(frozen["test_clean"], SAMPLE_SIZE)
    counts = Counter()
    for path in paths:
        labels = (root / "labels" / f"{path.stem}.txt").read_text().splitlines()
        counts.update(int(line.split()[0]) for line in labels)
    expected = tuple(counts[c] for c in CLASSES)
    if min(expected) <= 0:
        raise RuntimeError("Sample must contain both classes")

    summary_path = Path(__file__).resolve().parents[1] / "results" / "helmet_test_summary.csv"
    with summary_path.open(encoding="utf-8-sig", newline="") as stream:
        hashes = {row["model"]: row["checkpoint_sha256"] for row in csv.DictReader(stream) if row["split"] == "test_clean"}
    weights = {key: (args.weights / key / "best.pt").resolve() for key in MODELS}
    for key, weight in weights.items():
        if digest(weight) != hashes[key]:
            raise ValueError(f"SHA-256 differs for {key}: {weight}")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sample_path = output / "smoke_images.txt"
    sample_path.write_text("\n".join(map(str, paths)) + "\n", encoding="utf-8")
    config = output / "smoke.yaml"
    write_json(config, {"path": str(root), "train": "train.txt", "val": "val_clean.txt",
                        "test": str(sample_path), "names": CLASSES})
    metrics = {}
    options = {**EVALUATION, "device": "cpu", "batch": 4, "workers": 0,
               "plots": False, "save_txt": False, "save_conf": False, "verbose": False}
    for key, weight in weights.items():
        model = ultralytics.YOLO(str(weight))
        if model.names != CLASSES or model.task != "detect":
            raise ValueError(f"Invalid class mapping or task for {key}")
        prediction = model.predict(str(paths[0]), device="cpu", imgsz=640, conf=.25, verbose=False)[0]
        results = model.val(data=str(config), save_dir=str(output / key), **options)
        scores = dict(zip(("precision", "recall", "map50", "map50_95"), map(float, results.mean_results())))
        if (tuple(results.nt_per_class) != expected or tuple(results.ap_class_index) != tuple(CLASSES)
                or not all(math.isfinite(v) and 0 <= v <= 1 for v in scores.values()) or scores["map50"] <= 0):
            raise RuntimeError(f"Incomplete smoke evaluation for {key}")
        metrics[key] = {**scores, "checkpoint_sha256": hashes[key], "first_image_boxes": len(prediction.boxes)}

    write_json(output / "smoke_summary.json", {
        "scope": "CPU pipeline check on a fixed 24-image subset of test_clean. Not benchmark or report metrics.",
        "device": "cpu", "seed": SAMPLE_SEED, "images": [p.stem for p in paths], "labels": dict(counts),
        "python": sys.version.split()[0], "torch": str(torch.__version__),
        "ultralytics": ultralytics.__version__, "models": metrics,
    })
    print(f"Verified inference and smoke evaluation of {len(metrics)} checkpoints on {len(paths)} images")


if __name__ == "__main__":
    main()
