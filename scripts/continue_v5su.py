"""Audit or prepare the frozen SHWD dataset; training is disabled in this script."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


ARCHIVE_SHA256 = "2f6c5c347b778271bc8b27c2d61b731fc5fb8cdb4f45fce583dd2f82e6a46401"
BOX_SHA256 = "f4cc2ffb264ca22eab8f66ed98b364838815dacd9f8e68f5a64975791ac166ab"
SPLITS = {
    "train": (5457, "95b070d540392058cd4b5ded0ca32397cd31313d4fd2c5f033b133a63f3f9140"),
    "val": (607, "a2400eec362d035872b78189cdfe054a0f606e321651d8d5876050fdac6456bd"),
    "test": (1517, "29765cc1b50f4f4a779a4166f5cba0c0fd5caf8a2b6725c62873f3ed22f0baaa"),
    "val_clean": (425, "78e8ef69a358272f8ea2484e5853a64415840a559cf4739b714268ecfa31f8c4"),
    "test_clean": (1087, "f123acb538133f5ebd60eb4f47ff92a87dd86ab588b2a10c61ba0e94f285b155"),
    "val_clean_site": (264, "418fcb67981fbde59c9d60c031b9cc16245c840ba52eb6608b182adb05b483fd"),
    "test_clean_site": (628, "3baba09a45a21181f5f6ca090a8e82c8090692ae24195b80995c7f245d2abfdf"),
}
CLASS_IDS = {"hat": 0, "dog": 0, "person": 1}
CLASS_NAMES = {0: "helmet", 1: "bare_head"}


def check_digest(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual}")


def load_frozen_inputs(audit_dir):
    manifests = {}
    for name, (count, digest) in SPLITS.items():
        path = audit_dir / f"{name}.txt"
        check_digest(path, digest)
        ids = path.read_text(encoding="utf-8-sig").split()
        if len(ids) != count or len(set(ids)) != count:
            raise ValueError(f"Unexpected number of IDs in {path}")
        manifests[name] = ids

    path = audit_dir / "boxes_raw.csv"
    check_digest(path, BOX_SHA256)
    labels = defaultdict(list)
    classes = Counter()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            image_id, source_class = row["id"], row["cls"]
            w, h, x1, y1, x2, y2 = (float(row[key]) for key in ("W", "H", "x1", "y1", "x2", "y2"))
            if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
                raise ValueError(f"Invalid box for {image_id}")
            classes[source_class] += 1
            labels[image_id].append(
                f"{CLASS_IDS[source_class]} {(x1+x2)/2/w:.6f} {(y1+y2)/2/h:.6f} "
                f"{(x2-x1)/w:.6f} {(y2-y1)/h:.6f}"
            )
    if classes != {"person": 111514, "hat": 9044, "dog": 3}:
        raise ValueError(f"Unexpected classes in {path}: {classes}")
    image_ids = set(labels)
    original_ids = set(manifests["train"]) | set(manifests["val"]) | set(manifests["test"])
    if len(image_ids) != 7581 or image_ids != original_ids:
        raise ValueError("The original train/val/test manifests do not match the label IDs")
    if any(set(ids) - image_ids for ids in manifests.values()):
        raise ValueError("A filtered manifest contains an unknown image ID")
    return manifests, labels


def dataset_config(root):
    return {
        "path": str(root),
        "train": "train.txt",
        "val": "val_clean.txt",
        "test": "test_clean.txt",
        "names": CLASS_NAMES,
    }


def prepare_dataset(archive_path, destination, audit_dir):
    manifests, labels = load_frozen_inputs(audit_dir)
    check_digest(archive_path, ARCHIVE_SHA256)
    if destination.exists():
        raise FileExistsError(f"Dataset destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        members = {}
        for entry in archive.infolist():
            name = PurePosixPath(entry.filename.replace("\\", "/"))
            if entry.is_dir() or name.parent.name.lower() != "jpegimages" or name.stem not in labels:
                continue
            if name.stem in members:
                raise ValueError(f"More than one archive image for {name.stem}")
            members[name.stem] = (entry, name.name)
        if missing := sorted(set(labels) - set(members)):
            raise ValueError(f"Missing {len(missing)} SHWD images, including {missing[:5]}")

        staged = Path(temp) / "dataset"
        (staged / "images").mkdir(parents=True)
        (staged / "labels").mkdir()
        for image_id, lines in labels.items():
            member, filename = members[image_id]
            with archive.open(member) as source, (staged / "images" / filename).open("wb") as image:
                shutil.copyfileobj(source, image)
            (staged / "labels" / f"{image_id}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for name, ids in manifests.items():
            paths = (str(destination / "images" / members[image_id][1]) for image_id in ids)
            (staged / f"{name}.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")
        # JSON is valid YAML. The final path must be used in absolute image lists.
        (staged / "data.yaml").write_text(json.dumps(dataset_config(destination), indent=2) + "\n", encoding="utf-8")
        staged.rename(destination)
    print(f"Prepared {len(labels)} images at {destination}")


def verify_dataset(root, audit_dir):
    manifests, labels = load_frozen_inputs(audit_dir)
    cfg = json.loads((root / "data.yaml").read_text(encoding="utf-8"))
    expected = dataset_config(root)
    expected["names"] = {str(i): name for i, name in CLASS_NAMES.items()}
    if cfg != expected:
        raise ValueError("data.yaml differs from the frozen dataset configuration or the dataset was moved")
    for name, ids in manifests.items():
        paths = [Path(line) for line in (root / f"{name}.txt").read_text(encoding="utf-8").splitlines()]
        if [path.stem for path in paths] != ids:
            raise ValueError(f"Manifest image IDs or order changed: {name}")
        if any(path.parent != root / "images" or not path.is_file() for path in paths):
            raise ValueError(f"Missing images or unexpected paths in {name}.txt")
    for image_id, lines in labels.items():
        if (root / "labels" / f"{image_id}.txt").read_text(encoding="utf-8").splitlines() != lines:
            raise ValueError(f"Frozen YOLO labels changed for image {image_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, required=True, help="Directory with boxes_raw.csv and seven frozen manifests")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("audit", help="Verify manifests and labels without a GPU or third-party packages")
    prepare = commands.add_parser("prepare", help="Rebuild YOLO dataset from the original SHWD ZIP")
    prepare.add_argument("archive", type=Path)
    prepare.add_argument("data_root", type=Path)
    commands.add_parser("resume", help="Disabled: train only through Notebook 03 on managed Google Colab GPU")
    args = parser.parse_args()
    if args.command == "audit":
        manifests, labels = load_frozen_inputs(args.audit_dir)
        print(f"Verified {len(labels)} label files and {sum(map(len, labels.values()))} boxes")
        print("Frozen manifests:", {name: len(ids) for name, ids in manifests.items()})
    elif args.command == "prepare":
        prepare_dataset(args.archive, args.data_root.resolve(), args.audit_dir)
    elif args.command == "resume":
        parser.error("The legacy resume command is disabled; use Notebook 03 on managed Google Colab GPU.")


if __name__ == "__main__":
    main()
