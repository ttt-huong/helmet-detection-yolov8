"""Evaluate the four frozen helmet checkpoints and measure batch-1 latency."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import time


ULTRALYTICS = "8.4.202"
CLASSES = {0: "helmet", 1: "bare_head"}
SPLITS = {
    "test": (1517, (1878, 22558), "29765cc1b50f4f4a779a4166f5cba0c0fd5caf8a2b6725c62873f3ed22f0baaa"),
    "test_clean": (1087, (1744, 8866), "f123acb538133f5ebd60eb4f47ff92a87dd86ab588b2a10c61ba0e94f285b155"),
    "test_clean_site": (628, (1744, 334), "3baba09a45a21181f5f6ca090a8e82c8090692ae24195b80995c7f245d2abfdf"),
}
SPLIT_NOTES = {
    "test": "Original SHWD split, reference only due to possible overlap with training.",
    "test_clean": "Primary filtered test split.",
    "test_clean_site": "Filtered numeric/part2 source subset, not a verified construction-only set.",
}
COMMON = {"device": 0, "imgsz": 640, "iou": 0.7, "max_det": 300, "quantize": None,
          "augment": False, "classes": None, "single_cls": False, "agnostic_nms": False, "compile": False}
EVALUATION = {**COMMON, "split": "test", "batch": 16, "conf": 0.001, "rect": True,
              "plots": True, "save_txt": True, "save_conf": True, "save_json": False}
SPEED = {**COMMON, "batch": 1, "conf": 0.25, "rect": False, "verbose": False, "save": False}
SPEED_SEED, SPEED_IMAGES, WARMUP, SPEED_REPEATS = 42, 100, 20, 3


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_manifests(root, manifests):
    for name in ("train", "val_clean"):
        if not (root / f"{name}.txt").is_file():
            raise FileNotFoundError(f"Missing prepared {name}.txt in {root}")
    result = {}
    for split, (count, _, sha256) in SPLITS.items():
        frozen = manifests / f"{split}.txt"
        if digest(frozen) != sha256:
            raise ValueError(f"Frozen manifest hash differs: {frozen}")
        ids = frozen.read_text(encoding="utf-8-sig").split()
        paths = [Path(line) for line in (root / f"{split}.txt").read_text(encoding="utf-8").splitlines()]
        if len(set(ids)) != count or [path.stem for path in paths] != ids:
            raise ValueError(f"Prepared manifest has different IDs or ordering: {split}")
        for path in paths:
            if path.parent != root / "images" or not path.is_file():
                raise ValueError(f"Missing or misplaced image: {path}")
            if not (root / "labels" / f"{path.stem}.txt").is_file():
                raise ValueError(f"Missing prepared labels: {path.stem}")
        result[split] = paths
    return result


def evaluate_split(model, split, paths, data_yaml, destination):
    import numpy as np

    expected_ids = {path.stem for path in paths}
    seen = []

    def check_validation(validator):
        evaluated_ids = {Path(path).stem for path in validator.dataloader.dataset.im_files}
        if evaluated_ids != expected_ids or validator.seen != len(paths):
            raise RuntimeError(f"Validator did not evaluate exactly the frozen {split} images")
        seen.append(validator.seen)
        np.savetxt(destination / "confusion_matrix.csv", validator.confusion_matrix.matrix, delimiter=",", fmt="%d",
                   header="Rows predicted, columns ground truth. Order: helmet,bare_head,background")

    model.add_callback("on_val_end", check_validation)
    try:
        metrics = model.val(data=str(data_yaml), save_dir=str(destination), **EVALUATION)
    finally:
        model.callbacks["on_val_end"].remove(check_validation)
    if seen != [len(paths)] or tuple(metrics.nt_per_class) != SPLITS[split][1]:
        raise RuntimeError(f"Validation count or ground-truth class counts changed for {split}")
    if list(metrics.ap_class_index) != list(CLASSES):
        raise RuntimeError(f"Unexpected evaluated class IDs for {split}: {metrics.ap_class_index}")
    names = ("precision", "recall", "map50", "map50_95")
    scores = dict(zip(names, (float(x) for x in metrics.mean_results())))
    per_class = [{"class_id": i, "class_name": CLASSES[i], "instances": int(metrics.nt_per_class[i]),
                  **dict(zip(names, (float(x) for x in metrics.class_result(position))))}
                 for position, i in enumerate(metrics.ap_class_index)]
    for score in (scores, *per_class):
        if not all(0 <= score[name] <= 1 for name in names):
            raise RuntimeError(f"Invalid metric for {split}: {score}")
    required_plots = [destination / "confusion_matrix.png", *destination.glob("*PR_curve.png")]
    if len(required_plots) < 2 or not all(file.is_file() and file.stat().st_size for file in required_plots):
        raise RuntimeError(f"Missing PR curve or confusion matrix: {destination}")
    predictions = sum(1 for file in destination.glob("labels/**/*.txt") if file.stat().st_size)
    if scores["map50"] > 0 and not predictions:
        raise RuntimeError(f"Prediction files missing despite nonzero AP: {destination}")
    write_csv(destination / "per_class.csv", per_class)
    write_json(destination / "metrics.json", {**scores, "images": seen[0], "images_with_predictions": predictions})
    return scores


def benchmark(model, key, images, torch):
    import numpy as np

    for _, image in images[:WARMUP]:
        model.predict(source=image, **SPEED)
    raw = []
    for repeat in range(1, SPEED_REPEATS + 1):
        for path, image in images:
            torch.cuda.synchronize(0)
            start = time.perf_counter_ns()
            prediction = model.predict(source=image, **SPEED)[0]
            torch.cuda.synchronize(0)
            elapsed = (time.perf_counter_ns() - start) / 1e6
            raw.append({"model": key, "repeat": repeat, "image_id": path.stem, "pipeline_ms": elapsed,
                        **{f"{stage}_ms": float(prediction.speed[stage])
                           for stage in ("preprocess", "inference", "postprocess")}})
    times = np.asarray([row["pipeline_ms"] for row in raw])
    if len(times) != SPEED_IMAGES * SPEED_REPEATS or not np.all(np.isfinite(times) & (times > 0)):
        raise RuntimeError(f"Invalid speed samples: {key}")
    average = float(times.mean())
    stats = {"model": key, "samples": len(times), "mean_ms": average, "median_ms": float(np.median(times)),
             "p95_ms": float(np.percentile(times, 95)), "fps_sequential": 1000 / average}
    return raw, stats


def plot_tradeoff(output, summary, speed_summary):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    primary_scores = {row["model"]: row["map50_95"] for row in summary if row["split"] == "test_clean"}
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    for speed in speed_summary:
        model = speed["model"]
        point = speed["fps_sequential"], primary_scores[model]
        ax.scatter(*point)
        ax.annotate(model, point, xytext=(6, 4), textcoords="offset points")
    ax.set(xlabel="Sequential FPS (batch 1)", ylabel="mAP@0.5:0.95", title="Accuracy and speed on test_clean")
    ax.margins(x=0.13, y=0.2)
    ax.grid(alpha=0.25)
    fig.savefig(output / "accuracy_speed.png", dpi=160)
    plt.close(fig)


def run(args):
    import cv2
    import torch
    import ultralytics
    from ultralytics.utils.torch_utils import get_flops, get_num_params

    if ultralytics.__version__ != ULTRALYTICS:
        raise RuntimeError(f"Install ultralytics=={ULTRALYTICS}, found {ultralytics.__version__}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU 0 is required")
    torch.ones(1, device="cuda:0").sum().item()
    root = args.data_root.resolve()
    splits = check_manifests(root, args.manifests.resolve())
    checkpoints = {key: getattr(args, key).resolve() for key in ("v8n", "v8s", "v8m", "v5su")}
    for path in checkpoints.values():
        if path.name != "best.pt" or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Supply each model's trusted best.pt: {path}")
    hashes = {key: digest(path) for key, path in checkpoints.items()}
    if len(set(hashes.values())) != len(checkpoints):
        raise ValueError("Each model must have a distinct best.pt checkpoint")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sample_paths = random.Random(SPEED_SEED).sample(splits["test_clean"], SPEED_IMAGES)
    metadata = {
        "status": "running", "ultralytics": ULTRALYTICS, "python": sys.version, "torch": str(torch.__version__),
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0), "backend": "native PyTorch FP32",
        "checkpoint_sha256": hashes, "class_names": CLASSES, "split_notes": SPLIT_NOTES,
        "manifest_sha256": {key: value[2] for key, value in SPLITS.items()}, "evaluation": EVALUATION,
        "precision_recall_rule": "Ultralytics picks the maximum smoothed mean F1 operating point per run/split.",
        "confusion_matrix_rule": "Confidence 0.001 and matching IoU 0.45 in Ultralytics 8.4.202.",
        "raw_predictions": "YOLO normalized xywh + confidence. Missing file means zero detections for that image.",
        "speed": {**SPEED, "warmup": WARMUP, "seed": SPEED_SEED, "repeats": SPEED_REPEATS,
                  "split": "test_clean", "image_ids": [path.stem for path in sample_paths],
                  "scope": "Synchronized single-image predict calls on predecoded BGR arrays. Includes preprocess, "
                           "inference, NMS and Python overhead. Excludes decoding, video I/O, drawing and saving."},
    }
    write_json(output / "protocol.json", metadata)
    for split in splits:
        write_json(output / f"{split}.yaml", {"path": str(root), "train": "train.txt", "val": "val_clean.txt",
                                            "test": f"{split}.txt", "names": CLASSES})

    summary = []
    for key, path in checkpoints.items():
        model = ultralytics.YOLO(str(path))  # Input must be a trusted project checkpoint.
        if model.names != CLASSES or model.task != "detect":
            raise ValueError(f"Unexpected task or class mapping: {key}")
        parameters = get_num_params(model.model)
        gflops = get_flops(model.model, imgsz=COMMON["imgsz"]) or None
        for split, paths in splits.items():
            destination = output / "evaluation" / key / split
            print(f"Evaluating {key} on {split} ({len(paths)} images)", flush=True)
            scores = evaluate_split(model, split, paths, output / f"{split}.yaml", destination)
            summary.append({"model": key, "split": split, "images": len(paths), **scores, "parameters": parameters,
                            "gflops_640": gflops, "checkpoint_sha256": hashes[key], "note": SPLIT_NOTES[split]})
            write_csv(output / "summary.csv", summary)
        del model
        torch.cuda.empty_cache()

    # Validation runs first so any image repairs have already happened before loading the shared sample.
    images = [(path, cv2.imread(str(path))) for path in sample_paths]
    if any(image is None for _, image in images):
        raise RuntimeError("A selected speed benchmark image could not be decoded")
    raw_speed, speed_summary = [], []
    for key, path in checkpoints.items():
        print(f"Benchmarking {key} on GPU 0", flush=True)
        model = ultralytics.YOLO(str(path))
        raw, stats = benchmark(model, key, images, torch)
        raw_speed.extend(raw)
        speed_summary.append(stats)
        write_csv(output / "speed_raw.csv", raw_speed)
        write_csv(output / "speed_summary.csv", speed_summary)
        del model
        torch.cuda.empty_cache()
    if len(summary) != 12 or len(speed_summary) != 4 or len(raw_speed) != 1200:
        raise RuntimeError("Incomplete evaluation or speed output")
    plot_tradeoff(output, summary, speed_summary)
    metadata["status"] = "complete"
    write_json(output / "protocol.json", metadata)
    print(f"Verified 12 evaluations and 1,200 timed predictions under {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True, help="Prepared writable YOLO dataset root")
    parser.add_argument("--manifests", type=Path, required=True, help="Original frozen manifests, e.g. transfer/stage01")
    for key in ("v8n", "v8s", "v8m", "v5su"):
        parser.add_argument(f"--{key}", type=Path, required=True, help=f"Trusted {key} best.pt")
    parser.add_argument("--output", type=Path, required=True, help="New evaluation directory")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
