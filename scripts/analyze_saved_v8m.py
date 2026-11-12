"""Diagnose frozen SHWD test_clean predictions; no inference or training.

Greedy one-to-one same-class matching in descending IoU, adapted from
Tuấn's mahTuqn/Noron scripts/analyze_errors.py (blob 52ad3b18efcc780cecbc3e162727940383a03d5f).
"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import zipfile


CONF, IOU = 0.408, 0.50
NAMES = {0: "helmet", 1: "bare_head"}
SOURCE_CLASSES = {"hat": 0, "dog": 0, "person": 1}
FROZEN = {
    "test_clean.txt": "f123acb538133f5ebd60eb4f47ff92a87dd86ab588b2a10c61ba0e94f285b155",
    "boxes_raw.csv": "f4cc2ffb264ca22eab8f66ed98b364838815dacd9f8e68f5a64975791ac166ab",
    "shwd": "2f6c5c347b778271bc8b27c2d61b731fc5fb8cdb4f45fce583dd2f82e6a46401",
}
AREA_GROUPS = ("<1%", "1–<4%", ">=4%")
SIZE_GROUPS = ("<16 px", ">=16 px")
LIGHT_GROUPS = ("<85", "85–<170", ">=170")


def check_hash(path, expected):
    with path.open("rb") as f:
        actual = hashlib.file_digest(f, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"Unexpected SHA-256 for {path}: {actual}")
    return actual


def xyxy(xc, yc, w, h):
    return (xc-w/2, yc-h/2, xc+w/2, yc+h/2)


def overlap(a, b):
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w*h
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)


def match(gt, preds):
    pairs = []
    for g, (cls, box, _) in enumerate(gt):
        for p, (pred_cls, pred_box, conf) in enumerate(preds):
            if cls == pred_cls and (iou := overlap(box, pred_box)) >= IOU:
                pairs.append((-iou, -conf, g, p))
    used_gt, used_pred = {}, {}
    for neg_iou, _, g, p in sorted(pairs):
        if g not in used_gt and p not in used_pred:
            used_gt[g] = (p, -neg_iou)
            used_pred[p] = (g, -neg_iou)
    return used_gt, used_pred


def read_truth(audit):
    ids_path, truth_path = (audit / f for f in ("test_clean.txt", "boxes_raw.csv"))
    for path in (ids_path, truth_path):
        check_hash(path, FROZEN[path.name])
    ids = ids_path.read_text(encoding="utf-8-sig").split()
    gt, dims = {i: [] for i in ids}, {}
    counts = Counter()
    with truth_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            i = row["id"]
            if i not in gt:
                continue
            cls = SOURCE_CLASSES[row["cls"]]
            w, h = int(row["W"]), int(row["H"])
            x1, y1, x2, y2 = (float(row[k]) for k in ("x1", "y1", "x2", "y2"))
            dims[i] = w, h
            # Match the six-decimal YOLO labels from the frozen evaluator.
            xc, yc, bw, bh = (float(f"{v:.6f}") for v in (
                (x1+x2)/2/w, (y1+y2)/2/h, (x2-x1)/w, (y2-y1)/h))
            gt[i].append((cls, xyxy(xc, yc, bw, bh), float(row["long_px_640"])))
            counts[cls] += 1
    if len(gt) != 1087 or len(ids) != 1087 or set(gt) != set(dims) or counts != {0: 1744, 1: 8866}:
        raise ValueError(f"Unexpected test_clean membership or labels: {len(gt)} images, {counts}")
    return gt, dims


def read_predictions(labels, gt):
    files = {p.stem: p for p in labels.glob("*.txt")}
    metric = json.loads((labels.parent / "metrics.json").read_text(encoding="utf-8"))
    if (set(files) - gt.keys() or len(files) != metric["images_with_predictions"]
            or metric["images"] != len(gt) or abs(metric["map50_95"] - 0.6547521348408601) > 1e-5):
        raise ValueError("Predictions are incomplete or metrics.json is not from the frozen v8m/test_clean run")
    preds = {}
    zero_area_below_threshold = 0
    for i, path in sorted(files.items()):
        boxes = []
        for line in path.read_text(encoding="utf-8").splitlines():
            cls, xc, yc, w, h, conf = map(float, line.split())
            if (not all(map(math.isfinite, (cls, xc, yc, w, h, conf))) or cls not in NAMES
                    or not (0 <= conf <= 1 and 0 <= xc <= 1 and 0 <= yc <= 1 and 0 <= w <= 1 and 0 <= h <= 1)):
                raise ValueError(f"Invalid YOLO prediction in {path}")
            if w == 0 or h == 0:
                if conf >= CONF:
                    raise ValueError(f"Zero-area prediction above analysis threshold in {path}")
                zero_area_below_threshold += 1
                continue
            if conf >= CONF:
                boxes.append((int(cls), xyxy(xc, yc, w, h), conf))
        if not path.stat().st_size:
            raise ValueError(f"Empty prediction file: {path}")
        preds[i] = boxes
    return preds, metric, zero_area_below_threshold


def brightness(path, dims):
    if path is None:
        return {}
    import cv2
    import numpy as np

    def mean_luma(bgr, i):
        w, h = dims[i]
        if bgr is None or bgr.shape[:2] != (h, w):
            raise ValueError(f"Cannot decode image at expected dimensions: {i}")
        return float(bgr.mean(axis=(0, 1)) @ [0.114, 0.587, 0.299])

    if path.is_file():
        check_hash(path, FROZEN["shwd"])
        with zipfile.ZipFile(path) as z:
            members = {}
            for f in z.infolist():
                p = PurePosixPath(f.filename)
                if p.parent.name.lower() == "jpegimages" and p.stem in dims:
                    if p.stem in members:
                        raise ValueError(f"Duplicate image in archive: {p.stem}")
                    members[p.stem] = f
            if members.keys() != dims.keys():
                raise ValueError("SHWD archive does not contain all test_clean images")
            return {i: mean_luma(cv2.imdecode(np.frombuffer(z.read(f), dtype=np.uint8), cv2.IMREAD_COLOR), i)
                    for i, f in members.items()}
    members = [p for p in path.iterdir() if p.stem in dims and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if len(members) != len(dims) or {p.stem for p in members} != dims.keys():
        raise ValueError("Images directory does not contain exactly one image per test_clean ID")
    return {p.stem: mean_luma(cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR), p.stem)
            for p in members}


def area_band(box):
    area = (box[2]-box[0]) * (box[3]-box[1])
    return AREA_GROUPS[0 if area < .01 else 1 if area < .04 else 2]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", type=Path, required=True, help="Directory containing frozen boxes_raw.csv and test_clean.txt")
    p.add_argument("--labels", type=Path, required=True, help="Saved v8m/test_clean/labels; sibling metrics.json required")
    p.add_argument("--images", type=Path, help="Optional frozen SHWD ZIP or directory of original JPEG images")
    p.add_argument("--out", type=Path, required=True, help="New output directory")
    a = p.parse_args()
    gt, dims = read_truth(a.audit)
    preds, metrics, zero_area_below_threshold = read_predictions(a.labels, gt)
    lumas = brightness(a.images, dims)
    counts = defaultdict(Counter)
    gt_rows, pred_rows, image_rows = [], [], []
    for i, gboxes in gt.items():
        pboxes = preds.get(i, [])
        mg, mp = match(gboxes, pboxes)
        luma = lumas.get(i)
        light = "" if luma is None else LIGHT_GROUPS[0 if luma < 85 else 1 if luma < 170 else 2]
        small_fn = 0
        for g, (cls, box, long_px) in enumerate(gboxes):
            status = "TP" if g in mg else "FN"
            size = SIZE_GROUPS[0 if long_px < 16 else 1]
            area = area_band(box)
            keys = [("all", "all"), ("size_long_640", size), ("size_area", area)]
            if light:
                keys.append(("brightness", light))
            for kind, group in keys:
                counts[kind, group, cls][status] += 1
            small_fn += int(status == "FN" and size == SIZE_GROUPS[0])
            pred_index, iou = mg.get(g, ("", ""))
            gt_rows.append(dict(image_id=i, gt_index=g, class_name=NAMES[cls], status=status,
                                x1=box[0], y1=box[1], x2=box[2], y2=box[3], long_px_640=long_px,
                                area_group=area, mean_luma=luma, brightness=light, pred_index=pred_index, iou=iou))
        for j, (cls, box, conf) in enumerate(pboxes):
            status = "TP" if j in mp else "FP"
            if status == "FP":
                counts["all", "all", cls]["FP"] += 1
                if light:
                    counts["brightness", light, cls]["FP"] += 1
            gt_index, iou = mp.get(j, ("", ""))
            pred_rows.append(dict(image_id=i, pred_index=j, class_name=NAMES[cls], status=status,
                                  x1=box[0], y1=box[1], x2=box[2], y2=box[3], confidence=conf,
                                  mean_luma=luma, brightness=light, gt_index=gt_index, iou=iou))
        image_rows.append(dict(image_id=i, ground_truth=len(gboxes), TP=len(mg), FN=len(gboxes)-len(mg),
                               FP=len(pboxes)-len(mp), FN_small=small_fn, mean_luma=luma, brightness=light))
    if not pred_rows:
        raise ValueError("No prediction remains at the analysis threshold; check input data")
    rows = []
    axes = [("all", ("all",)), ("size_long_640", SIZE_GROUPS), ("size_area", AREA_GROUPS)]
    if lumas:
        axes.append(("brightness", LIGHT_GROUPS))
    for kind, groups in axes:
        for group in groups:
            for cls, name in NAMES.items():
                c = counts[kind, group, cls]
                total = c["TP"] + c["FN"]
                rows.append(dict(stratum=kind, group=group, class_name=name, ground_truth=total,
                                 TP=c["TP"], FN=c["FN"], FP=None if kind.startswith("size") else c["FP"],
                                 recall=c["TP"]/total if total else None))
    if sum(r["ground_truth"] for r in rows if r["stratum"] == "all") != 10610:
        raise RuntimeError("Ground-truth count changed")
    out = a.out
    out.mkdir(parents=True, exist_ok=False)
    for filename, entries in (("strata_metrics.csv", rows), ("ground_truth_matches.csv", gt_rows),
                              ("prediction_matches.csv", pred_rows), ("image_review.csv", image_rows)):
        write_csv(out / filename, entries)
    summary = dict(images=len(gt), images_with_saved_predictions=metrics["images_with_predictions"],
                   matched_gt=sum(r["status"] == "TP" for r in gt_rows), ground_truth=len(gt_rows),
                   fn=sum(r["status"] == "FN" for r in gt_rows), fp=sum(r["status"] == "FP" for r in pred_rows),
                   confidence=CONF, matching_iou=IOU, brightness_images=len(lumas),
                   zero_area_below_threshold=zero_area_below_threshold,
                   brightness_mean_y="0.114 B + 0.587 G + 0.299 R; global image brightness",
                   per_class=[r for r in rows if r["stratum"] == "all"])
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
