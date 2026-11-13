"""Plot labeled diagnostic examples from the frozen YOLOv8m analysis."""

import argparse
import csv
import math
from pathlib import Path, PurePosixPath
import zipfile

def read_rows(folder, name):
    with (folder / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pixels(row, width, height):
    return tuple(float(row[k]) * extent for k, extent in (
        ("x1", width), ("y1", height), ("x2", width), ("y2", height)))


def crop_limits(box, width, height):
    x1, y1, x2, y2 = box
    half = max(x2 - x1, y2 - y1) * 2
    cx, cy = (x1+x2)/2, (y1+y2)/2
    return max(0, cx-half), min(width, cx+half), max(0, cy-half), min(height, cy+half)


def candidates(gt, pred, imgs):
    buckets = [
        sorted((r for r in gt if r["class_name"] == "helmet" and r["status"] == "FN"
                and 8 <= float(r["long_px_640"]) < 16),
               key=lambda r: abs(float(r["long_px_640"]) - 15)),
        sorted((r for r in gt if r["status"] == "FN" and r["brightness"] == "<85"
                and float(r["long_px_640"]) >= 16),
               key=lambda r: (float(r["mean_luma"]), int(imgs[r["image_id"]]["ground_truth"]))),
        sorted((r for r in pred if r["status"] == "FP"),
               key=lambda r: (-float(r["confidence"]), int(imgs[r["image_id"]]["ground_truth"]))),
    ]
    chosen = []
    for bucket in buckets:
        seen = set()
        for row in bucket:
            image_id = row["image_id"]
            if image_id in seen:
                continue
            seen.add(image_id)
            chosen.append(row)
            if len(seen) == 4:
                break
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", help="Case keys in form image_id:FN-or-FP:index")
    args = parser.parse_args()

    import cv2
    import matplotlib
    import numpy as np

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    gt = read_rows(args.analysis, "ground_truth_matches.csv")
    pred = read_rows(args.analysis, "prediction_matches.csv")
    imgs = {r["image_id"]: r for r in read_rows(args.analysis, "image_review.csv")}
    keys = {f'{r["image_id"]}:{r["status"]}:{r.get("pred_index") if r["status"] == "FP" else r["gt_index"]}': r
            for r in (*gt, *pred) if r["status"] in {"FN", "FP"}}
    rows = [keys[key] for key in args.cases] if args.cases else candidates(gt, pred, imgs)
    columns = min(2 if args.cases else 4, len(rows))
    nrows = math.ceil(len(rows) / columns)
    fig, axes = plt.subplots(nrows, columns, figsize=(3.6*columns, 3.35*nrows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    with zipfile.ZipFile(args.images) as archive:
        members = {p.stem: entry for entry in archive.infolist()
                   if (p := PurePosixPath(entry.filename)).parent.name.lower() == "jpegimages"}
        for panel, (ax, row) in enumerate(zip(axes.flat, rows)):
            image_id = row["image_id"]
            raw = np.frombuffer(archive.read(members[image_id]), dtype=np.uint8)
            rgb = cv2.cvtColor(cv2.imdecode(raw, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            height, width = rgb.shape[:2]
            box = pixels(row, width, height)
            ax.imshow(rgb, interpolation="antialiased")
            x1, x2, y1, y2 = crop_limits(box, width, height)
            for other in (*gt, *pred):
                if other["image_id"] != image_id:
                    continue
                is_target = row is other
                if not is_target and (other["status"] == "TP" or args.cases):
                    continue
                a, b, c, d = pixels(other, width, height)
                if c < x1 or a > x2 or d < y1 or b > y2:
                    continue
                color = "#ff4557" if other["status"] == "FN" else "#00d9ff"
                ax.add_patch(Rectangle((a,b), c-a, d-b, fill=False, edgecolor=color,
                                       linewidth=2 if is_target else .7, alpha=1 if is_target else .55))
            ax.set(xlim=(x1, x2), ylim=(y2, y1))
            index = row["gt_index"] if row["status"] == "FN" else row["pred_index"]
            suffix = f'{float(row["long_px_640"]):.1f} px' if row["status"] == "FN" else f'conf {float(row["confidence"]):.2f}'
            letter = f'({chr(97 + panel)}) ' if args.cases else ""
            ax.set_title(f'{letter}{image_id} · {row["status"]} {row["class_name"]} #{index}\n{suffix} · Y={float(row["mean_luma"]):.1f}', fontsize=10)
    fig.tight_layout(pad=1.1)
    fig.savefig(args.out, dpi=210, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
