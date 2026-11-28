"""Validate the hardhat-only YOLO dataset and its depiction-region support class."""

import argparse
from collections import Counter
import math
from pathlib import Path
import sys


CLASSES = {
    0: "hard_hat_worn",
    1: "depiction_region",
}
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
SPLITS = ("train", "val", "test")


class DatasetError(Exception):
    """An actionable dataset validation error."""


def load_config(path):
    try:
        import yaml
    except ImportError as error:
        raise DatasetError(
            "PyYAML is required to read data.yaml. Install only the validator "
            "dependency with `python -m pip install PyYAML`; this check does not train a model."
        ) from error

    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError) as error:
        raise DatasetError(f"Could not read valid YAML from {path}: {error}") from error
    if not isinstance(config, dict):
        raise DatasetError(f"Expected a YAML mapping in {path}")
    return config


def class_names(value):
    if isinstance(value, list):
        names = {index: name for index, name in enumerate(value)}
    elif isinstance(value, dict):
        try:
            names = {int(index): name for index, name in value.items()}
        except (TypeError, ValueError) as error:
            raise DatasetError("data.yaml names must use integer class IDs") from error
    else:
        raise DatasetError("data.yaml must define names as a list or an ID-to-name mapping")

    if names != CLASSES:
        raise DatasetError(
            "Class mapping differs from the hardhat-only training contract. "
            f"Expected {CLASSES}, found {names}"
        )
    return names


def resolve_path(value, root, split):
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"data.yaml is missing a non-empty {split} path")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def split_images(source, split):
    if source.is_dir():
        images = sorted(
            path for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    elif source.is_file() and source.suffix.lower() == ".txt":
        images = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = source.parent / path
            images.append(path.resolve())
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                raise DatasetError(f"{source}:{line_number} is not a supported image path: {value}")
    else:
        raise DatasetError(f"{split} must point to an image directory or a .txt image manifest: {source}")

    if not images:
        raise DatasetError(f"The {split} split contains no images: {source}")
    missing = [path for path in images if not path.is_file()]
    if missing:
        examples = ", ".join(str(path) for path in missing[:3])
        raise DatasetError(f"The {split} split lists missing images, for example: {examples}")
    return images


def label_path_for(image):
    parts = list(image.parts)
    image_parts = [index for index, part in enumerate(parts) if part.lower() == "images"]
    if not image_parts:
        raise DatasetError(
            f"Cannot derive a labels path for {image}. Place images under an `images` directory "
            "with a sibling `labels` directory."
        )
    parts[image_parts[0]] = "labels"
    return Path(*parts).with_suffix(".txt")


def read_labels(image, split, counts):
    path = label_path_for(image)
    if not path.is_file():
        raise DatasetError(
            f"Missing label file {path}. Use an empty .txt file for an intentional background image."
        )

    has_boxes = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        values = line.split()
        if not values:
            continue
        if len(values) != 5:
            raise DatasetError(f"{path}:{line_number} must contain class, x_center, y_center, width, height")
        try:
            class_id = int(values[0])
            x_center, y_center, width, height = map(float, values[1:])
        except ValueError as error:
            raise DatasetError(f"{path}:{line_number} contains a non-numeric label value") from error

        if class_id not in CLASSES:
            raise DatasetError(f"{path}:{line_number} uses unknown class ID {class_id}")
        if not all(math.isfinite(value) for value in (x_center, y_center, width, height)):
            raise DatasetError(f"{path}:{line_number} contains a non-finite coordinate")
        if width <= 0 or height <= 0:
            raise DatasetError(f"{path}:{line_number} has a zero or negative box size")
        if not all(0 <= value <= 1 for value in (x_center, y_center, width, height)):
            raise DatasetError(f"{path}:{line_number} has coordinates outside the normalized [0, 1] range")
        if x_center - width / 2 < 0 or x_center + width / 2 > 1:
            raise DatasetError(f"{path}:{line_number} box extends outside the image horizontally")
        if y_center - height / 2 < 0 or y_center + height / 2 > 1:
            raise DatasetError(f"{path}:{line_number} box extends outside the image vertically")
        counts[class_id] += 1
        has_boxes = True

    return not has_boxes


def validate(dataset_yaml):
    config = load_config(dataset_yaml)
    class_names(config.get("names"))
    root_value = config.get("path", str(dataset_yaml.parent))
    if not isinstance(root_value, str):
        raise DatasetError("data.yaml path must be a string")
    root = Path(root_value).expanduser()
    if not root.is_absolute():
        root = dataset_yaml.parent / root
    root = root.resolve()

    global_ids = {}
    summary = {}
    train_counts = Counter()
    validation_counts = Counter()
    for split in SPLITS:
        source = resolve_path(config.get(split), root, split)
        images = split_images(source, split)
        ids = set()
        class_counts = Counter()
        backgrounds = 0
        for image in images:
            image_id = image.stem
            if image_id in ids:
                raise DatasetError(f"Duplicate image ID {image_id!r} inside {split}")
            ids.add(image_id)
            if image_id in global_ids:
                raise DatasetError(
                    f"Image ID {image_id!r} appears in both {global_ids[image_id]} and {split}. "
                    "Keep all frames or variants from one source group in one split."
                )
            global_ids[image_id] = split
            backgrounds += read_labels(image, split, class_counts)

        if split == "train":
            train_counts = class_counts
        elif split == "val":
            validation_counts = class_counts
        summary[split] = (len(images), sum(class_counts.values()), backgrounds, class_counts)

    for split, counts in (("Training", train_counts), ("Validation", validation_counts)):
        missing_classes = [
            name for class_id, name in CLASSES.items() if counts[class_id] == 0
        ]
        if missing_classes:
            raise DatasetError(
                f"{split} split has no boxes for these classes: " + ", ".join(missing_classes)
            )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_yaml", type=Path, help="Path to the two-class hardhat-only YOLO data.yaml")
    args = parser.parse_args()
    dataset_yaml = args.data_yaml.expanduser().resolve()
    try:
        summary = validate(dataset_yaml)
    except DatasetError as error:
        print(f"Dataset validation failed: {error}", file=sys.stderr)
        return 2

    print(f"Validated {dataset_yaml}")
    for split, (images, boxes, backgrounds, counts) in summary.items():
        named_counts = {CLASSES[class_id]: counts[class_id] for class_id in CLASSES}
        print(
            f"{split}: {images} images, {boxes} boxes, {backgrounds} explicit backgrounds, "
            f"classes={named_counts}"
        )
    print("Hardhat target and depiction-region support classes appear in train and validation. No image IDs overlap between splits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
