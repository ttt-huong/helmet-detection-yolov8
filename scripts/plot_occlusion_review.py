"""Render review crops containing the ground-truth box and surrounding context."""

import argparse
import csv
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sample", type=Path, required=True)
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int)
    args = p.parse_args()

    from matplotlib import pyplot as plt
    from matplotlib.patches import Rectangle
    from PIL import Image

    with args.sample.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))[:args.limit]
    images = {f.stem: f for f in args.images.iterdir() if f.is_file()}
    args.output.mkdir(parents=True, exist_ok=True)
    for first in range(0, len(rows), 16):
        fig, axes = plt.subplots(4, 4, figsize=(14, 13), layout="constrained")
        for ax in axes.flat:
            ax.set_axis_off()
        for ax, row in zip(axes.flat, rows[first:first+16]):
            with Image.open(images[row["image_id"]]) as source:
                img = source.convert("RGB")
            w, h = img.size
            x1, y1, x2, y2 = [float(row[k])*size for k, size in zip(("x1","y1","x2","y2"), (w,h,w,h))]
            pad = max(16, max(x2-x1, y2-y1)*.65)
            xlo, xhi, ylo, yhi = max(0, x1-pad), min(w, x2+pad), max(0, y1-pad), min(h, y2+pad)
            ax.imshow(img.crop((int(xlo), int(ylo), int(xhi), int(yhi))),
                      extent=(int(xlo), int(xhi), int(yhi), int(ylo)), interpolation="nearest")
            ax.add_patch(Rectangle((x1,y1), x2-x1, y2-y1, fill=False, edgecolor="#00eaff", linewidth=1.7))
            ax.set_title(row["review_id"], fontsize=12)
        fig.savefig(args.output / f"review_{first+1:02d}_{min(first+16,len(rows)):02d}.png", dpi=135)
        plt.close(fig)


if __name__ == "__main__":
    main()
