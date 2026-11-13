"""Score image conditions and audit an outcome-blind sample of occlusion labels."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import random

from evaluate_helmet import check_manifests, write_json
from prepare_shwd import load_manifests


SEED = 52
PER_STRATUM = 12
OCCLUSION = {"che", "khong_che", "khong_ro"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def image_scores(path):
    import cv2
    import numpy as np

    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unreadable image: {path}")
    mean_y = float(image.mean(axis=(0, 1)) @ [0.114, 0.587, 0.299])
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 640 / max(h, w)
    resized = cv2.resize(gray, (max(1, round(w*scale)), max(1, round(h*scale))),
                         interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    sharpness = float(cv2.Laplacian(resized, cv2.CV_32F, ksize=1).var(dtype=np.float64))
    return mean_y, sharpness


def frozen_inputs(root, manifest_dir, matches_path):
    test = check_manifests(root, manifest_dir)["test_clean"]
    val_ids = load_manifests(manifest_dir)["val_clean"]
    val = [Path(line) for line in (root / "val_clean.txt").read_text(encoding="utf-8").splitlines()]
    if [p.stem for p in val] != val_ids or any(p.parent != root / "images" or not p.is_file() for p in val):
        raise ValueError("val_clean differs from its frozen manifest")
    rows = read_csv(matches_path)
    keys = {(r["image_id"], r["gt_index"]) for r in rows}
    counts = Counter(r["class_name"] for r in rows)
    if (len(rows) != len(keys) or counts != {"helmet": 1744, "bare_head": 8866}
            or {r["image_id"] for r in rows} != {p.stem for p in test}
            or any(r["status"] not in {"TP", "FN"} for r in rows)):
        raise ValueError("Expected the 10,610 verified per-box matches of v8m/test_clean")
    return val, test, rows


def occlusion_sample(matches):
    # Select using only ground-truth class, image ID and annotated crowd size.
    # The matching outcome and the prediction confidence never enter selection.
    crowd = Counter(r["image_id"] for r in matches)
    rng = random.Random(SEED)
    strata = {}
    used_images = set()
    for cls in ("helmet", "bare_head"):
        for dense in (False, True):
            rows = [r for r in matches if r["class_name"] == cls and (crowd[r["image_id"]] >= 12) == dense]
            rows.sort(key=lambda r: (r["image_id"], int(r["gt_index"])))
            rng.shuffle(rows)
            stratum = f"{cls}/{'dong' if dense else 'it_nguoi'}"
            strata[stratum] = []
            for r in rows:
                i = r["image_id"]
                if i in used_images:
                    continue
                used_images.add(i)
                strata[stratum].append(r)
                if len(strata[stratum]) == PER_STRATUM:
                    break
            if len(strata[stratum]) != PER_STRATUM:
                raise ValueError(f"Not enough unique images in {stratum}")
    ordered = [(name, bucket[j]) for j in range(PER_STRATUM) for name, bucket in strata.items()]
    return [{"review_id": f"C{i:02d}", "image_id": r["image_id"], "gt_index": r["gt_index"],
             **{k: r[k] for k in ("x1", "y1", "x2", "y2")}, "sampling_stratum": name}
            for i, (name, r) in enumerate(ordered, 1)]


def prepare(args):
    import cv2
    import numpy as np

    root = args.data_root.resolve()
    val, test, matches = frozen_inputs(root, args.manifests, args.matches)
    cv2.setNumThreads(2)
    score_val = [(p.stem, *image_scores(p)) for p in val]
    q1, q3 = (float(x) for x in np.quantile([r[2] for r in score_val], [.25, .75]))
    if not 0 < q1 < q3:
        raise ValueError("Invalid validation thresholds")
    selected = test[:16] if args.pilot else test
    records = []
    for path in selected:
        y, variance = image_scores(path)
        records.append({"image_id": path.stem, "mean_y": y, "var_laplacian": variance,
                        "brightness": "dark" if y < 85 else "bright" if y >= 170 else "mid",
                        "edge_score": "low" if variance < q1 else "high" if variance >= q3 else "mid"})
    args.output.mkdir(parents=True, exist_ok=False)
    write_csv(args.output / "image_conditions.csv", records)
    write_csv(args.output / "occlusion_sample.csv", occlusion_sample(matches))
    write_json(args.output / "protocol.json", {"pilot": args.pilot, "val_images": len(val), "test_images": len(records),
               "luma_thresholds": [85, 170], "edge_score_val_clean_q25": q1, "edge_score_val_clean_q75": q3,
               "edge_score": "Variance of grayscale Laplacian ksize=1, image long edge resized to 640",
               "edge_score_scope": "Image-level sharpness proxy sensitive to texture, compression and lighting",
               "occlusion": {"seed": SEED, "per_class_density_stratum": PER_STRATUM,
                             "dense_if_gt_boxes_at_least": 12, "sample_images": 4*PER_STRATUM,
                             "manual_labels": sorted(OCCLUSION)},
               "match_confidence": .408, "match_iou": .5})
    print(f"Scored {len(records)} test images; validation thresholds {q1:.2f}, {q3:.2f}")


def aggregate(args):
    conditions = {r["image_id"]: r for r in read_csv(args.conditions / "image_conditions.csv")}
    protocol = json.loads((args.conditions / "protocol.json").read_text(encoding="utf-8"))
    sample = {r["review_id"]: r for r in read_csv(args.conditions / "occlusion_sample.csv")}
    reviewed = {r["review_id"]: r for r in read_csv(args.review)}
    rows = read_csv(args.matches)
    if (protocol["pilot"] or len(conditions) != 1087 or set(conditions) != {r["image_id"] for r in rows}
            or reviewed.keys() != sample.keys() or any(r["occlusion"] not in OCCLUSION for r in reviewed.values())):
        raise ValueError("Full image scores and complete manual review are required")
    counts = defaultdict(Counter)
    for r in rows:
        image = conditions[r["image_id"]]
        axes = (("size_640", "small" if float(r["long_px_640"]) < 16 else "other"),
                ("brightness", image["brightness"]), ("edge_score", image["edge_score"]))
        for kind, group in axes:
            counts[kind, group, r["class_name"]][r["status"]] += 1
    matches = {(r["image_id"], r["gt_index"]): r for r in rows}
    joined_review = []
    for case_id, s in sample.items():
        r = matches[s["image_id"], s["gt_index"]]
        result = reviewed[case_id]
        label = result["occlusion"]
        counts["occlusion_sample", label, r["class_name"]][r["status"]] += 1
        joined_review.append({"review_id": case_id, "image_id": r["image_id"], "gt_index": r["gt_index"],
                              "class_name": r["class_name"], "sampling_stratum": s["sampling_stratum"],
                              "occlusion": label, "note": result["note"], "status": r["status"]})
    output_rows = []
    for (axis, group, cls), c in sorted(counts.items()):
        total = c["TP"] + c["FN"]
        output_rows.append({"axis": axis, "group": group, "class_name": cls, "boxes": total,
                            "TP": c["TP"], "FN": c["FN"],
                            "recall": "" if group == "khong_ro" else c["TP"]/total})
    args.output.mkdir(parents=True, exist_ok=False)
    write_csv(args.output / "condition_recall.csv", output_rows)
    write_csv(args.output / "occlusion_review_results.csv", joined_review)
    print("Verified matched box counts by condition and joined manual occlusion labels.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--manifests", type=Path, required=True)
    p.add_argument("--matches", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--pilot", action="store_true")
    p.set_defaults(run=prepare)
    p = sub.add_parser("aggregate")
    for name in ("conditions", "review", "matches", "output"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.set_defaults(run=aggregate)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
