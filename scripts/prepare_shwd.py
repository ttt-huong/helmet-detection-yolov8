"""Recreate the project's frozen YOLO dataset from the original VOC2028 ZIP."""

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import shutil
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from evaluate_helmet import CLASSES, SPLITS as EVALUATION_SPLITS, digest


ARCHIVE_SHA256 = "2f6c5c347b778271bc8b27c2d61b731fc5fb8cdb4f45fce583dd2f82e6a46401"
MANIFESTS = {
    "train": (5457, "95b070d540392058cd4b5ded0ca32397cd31313d4fd2c5f033b133a63f3f9140"),
    "val": (607, "a2400eec362d035872b78189cdfe054a0f606e321651d8d5876050fdac6456bd"),
    "val_clean": (425, "78e8ef69a358272f8ea2484e5853a64415840a559cf4739b714268ecfa31f8c4"),
    "val_clean_site": (264, "418fcb67981fbde59c9d60c031b9cc16245c840ba52eb6608b182adb05b483fd"),
    **{name: (count, sha) for name, (count, _, sha) in EVALUATION_SPLITS.items()},
}
SOURCE_CLASSES = {"hat": 0, "dog": 0, "person": 1}


def load_manifests(directory):
    splits = {}
    for name, (count, sha) in MANIFESTS.items():
        path = directory / f"{name}.txt"
        if digest(path) != sha:
            raise ValueError(f"Wrong frozen manifest: {path}")
        ids = path.read_text(encoding="utf-8-sig").split()
        if len(ids) != count or len(set(ids)) != count:
            raise ValueError(f"Unexpected IDs in {path}")
        splits[name] = ids
    return splits


def archive_members(archive, folder, ids):
    members = {}
    for entry in archive.infolist():
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        if entry.is_dir() or path.parent.name.lower() != folder or path.stem not in ids:
            continue
        if path.stem in members:
            raise ValueError(f"Duplicate archive entry: {path.stem} in {folder}")
        members[path.stem] = (entry, path.name)
    if members.keys() != ids:
        raise ValueError(f"Missing {folder} entries: {sorted(ids - members.keys())[:8]}")
    return members


def yolo_labels(xml_bytes, image_id, counts):
    xml = ET.fromstring(xml_bytes)
    width, height = (float(xml.findtext(f"size/{k}")) for k in ("width", "height"))
    rows = []
    for obj in xml.findall("object"):
        cls = obj.findtext("name")
        x1, y1, x2, y2 = (float(obj.findtext(f"bndbox/{k}"))
                          for k in ("xmin", "ymin", "xmax", "ymax"))
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError(f"Invalid VOC box in {image_id}")
        if cls not in SOURCE_CLASSES or (cls == "dog" and image_id != "000377"):
            raise ValueError(f"Unexpected class {cls!r} in {image_id}")
        counts[cls] += 1
        rows.append(f"{SOURCE_CLASSES[cls]} {(x1+x2)/2/width:.6f} {(y1+y2)/2/height:.6f} "
                    f"{(x2-x1)/width:.6f} {(y2-y1)/height:.6f}")
    if not rows:
        raise ValueError(f"Missing labels for {image_id}")
    return "\n".join(rows) + "\n"


def prepare(archive_path, manifests, output):
    if output.exists():
        raise FileExistsError(f"Use a new output directory: {output}")
    if digest(archive_path) != ARCHIVE_SHA256:
        raise ValueError("SHA-256 does not match the original VOC2028.zip")
    splits = load_manifests(manifests)
    original_ids = set().union(*(splits[k] for k in ("train", "val", "test")))
    if len(original_ids) != 7581 or any(set(ids) - original_ids for ids in splits.values()):
        raise ValueError("Invalid dataset split membership")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive, TemporaryDirectory(dir=output.parent) as tmp:
        images = archive_members(archive, "jpegimages", original_ids)
        labels = archive_members(archive, "annotations", original_ids)
        stage = Path(tmp) / "dataset"
        (stage / "images").mkdir(parents=True)
        (stage / "labels").mkdir()
        counts = Counter()
        for image_id in sorted(original_ids):
            entry, name = images[image_id]
            with archive.open(entry) as src, (stage / "images" / name).open("wb") as dst:
                shutil.copyfileobj(src, dst)
            lines = yolo_labels(archive.read(labels[image_id][0]), image_id, counts)
            (stage / "labels" / f"{image_id}.txt").write_text(lines, encoding="utf-8", newline="\n")
        if counts != {"hat": 9044, "person": 111514, "dog": 3}:
            raise ValueError(f"Unexpected class counts: {counts}")
        for name, ids in splits.items():
            paths = [str(output / "images" / images[i][1]) for i in ids]
            (stage / f"{name}.txt").write_text("\n".join(paths) + "\n", encoding="utf-8", newline="\n")
        config = {"path": str(output), "train": "train.txt", "val": "val_clean.txt",
                  "test": "test_clean.txt", "names": CLASSES}
        (stage / "data.yaml").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        stage.rename(output)
    print(f"Prepared {len(original_ids)} images, {sum(counts.values())} labels, {len(splits)} manifests at {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--manifests", default=Path("manifests"), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.archive, args.manifests, args.output.resolve())


if __name__ == "__main__":
    main()
