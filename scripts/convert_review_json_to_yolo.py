"""Convert the eight-class browser review manifest into a two-class YOLO dataset.

Usage::

    python scripts/convert_review_json_to_yolo.py --review-json review-v7.json \
        --images-dir source_images --output-dir datasets/hardhat_only_v1

Hardhat-only release datasets require review v7, which embeds split, rights,
source-scene attestation, per-surface depiction region IDs, and terminal
image-level review status. V6 and older exports are rejected because they do
not prove whether empty images were fully reviewed; re-export them through the
browser before conversion.
The output directory must not exist. The command creates it, ``<output-dir>.zip``,
a sibling ``test_scene_metadata.csv``, and a pending
``<output-dir-name>_hard_negative_source_groups.csv`` template. Confirm every
group and complete that template before cloud training. This prepares data only;
it does not train a model. Pillow is required to verify source image formats and dimensions.
"""

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
import zipfile


CLASSES = (
    "hard_hat_worn",
    "traffic_helmet_worn",
    "cap_worn",
    "beanie_worn",
    "bare_head",
    "depicted_hat",
    "loose_hat",
    "depiction_region",
)
SPLITS = ("train", "val", "test")
SCENE_TYPES = {"depiction_only", "mixed_scene", "other"}
LEGACY_SCENE_TYPES = {"poster_only": "depiction_only", "mixed_scene": "mixed_scene", "other": "other"}
DEPICTION_SURFACE_TYPES = {"poster", "printed_photo", "screen", "other_depiction"}
WORN_IDS = {0, 1, 2, 3}
SOURCE_DEPENDENT_HEAD_IDS = {*WORN_IDS, 4}
TARGET_WORN_IDS = {0}
TRAIN_CLASSES = ("hard_hat_worn", "depiction_region")
REVIEW_TO_TRAIN_CLASS = {0: 0, 7: 1}
MANIFEST_COLUMNS = ("image_id", "split", "group_id", "scene_type")
RIGHTS_MANIFEST_COLUMNS = (
    "image_id", "training_use", "basis", "source_reference", "license_id", "attribution",
)
REVIEW_FORMAT_V1 = "helmet-vision-review-v1"
REVIEW_FORMAT_V2 = "helmet-vision-review-v2"
REVIEW_FORMAT_V3 = "helmet-vision-review-v3"
REVIEW_FORMAT_V4 = "helmet-vision-review-v4"
REVIEW_FORMAT_V5 = "helmet-vision-review-v5"
REVIEW_FORMAT_V6 = "helmet-vision-review-v6"
REVIEW_FORMAT_V7 = "helmet-vision-review-v7"
TRAINING_USE_VALUES = {"approved", "not_allowed", "unknown"}
RIGHTS_BASES = {"owned", "permission", "license", "public_domain"}
IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
    ".webp": "WEBP",
}


class ConversionError(Exception):
    """An actionable input or output contract error."""


def safe_image_id(value, where):
    if not isinstance(value, str) or not value:
        raise ConversionError(f"{where}: image_id must be a non-empty UUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise ConversionError(f"{where}: invalid image_id {value!r}; expected a browser UUID") from error
    if str(parsed) != value:
        raise ConversionError(f"{where}: image_id {value!r} is not in canonical UUID form")
    return value


def safe_file_name(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ConversionError(f"{where}: file_name must be a non-empty image filename")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ConversionError(f"{where}: file_name must be a basename without path components: {value!r}")
    if Path(value).name != value:
        raise ConversionError(f"{where}: file_name contains an unsafe path sequence: {value!r}")
    if Path(value).suffix.lower() not in IMAGE_FORMATS:
        raise ConversionError(
            f"{where}: unsupported image suffix for {value!r}; use .jpg, .jpeg, .png, .bmp, or .webp"
        )
    return value


def load_review(path):
    try:
        dataset = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConversionError(f"Cannot read review JSON {path}: {error}") from error
    review_format = dataset.get("format") if isinstance(dataset, dict) else None
    if review_format != REVIEW_FORMAT_V7:
        raise ConversionError(
            "The hardhat-only pipeline requires helmet-vision-review-v7 with terminal image_review_status. "
            "V6 and older exports cannot certify image-level annotation completeness; re-export from the browser."
        )

    expected_classes = [{"id": index, "name": name} for index, name in enumerate(CLASSES)]
    if dataset.get("classes") != expected_classes:
        raise ConversionError(
            "Review JSON class mapping is invalid; export a fresh manifest with the project's exact eight-class review ontology"
        )
    images = dataset.get("images")
    if not isinstance(images, list) or not images:
        raise ConversionError("Review JSON must contain a non-empty images array")

    seen_ids = set()
    seen_names = set()
    for index, item in enumerate(images):
        where = f"Review JSON images[{index}]"
        if not isinstance(item, dict):
            raise ConversionError(f"{where} must be an object")
        image_id = safe_image_id(item.get("image_id"), where)
        folded_id = image_id.casefold()
        if folded_id in seen_ids:
            raise ConversionError(f"{where}: duplicate image_id {image_id!r}")
        seen_ids.add(folded_id)
        file_name = safe_file_name(item.get("file_name"), where)
        folded_name = file_name.casefold()
        if folded_name in seen_names:
            raise ConversionError(f"{where}: duplicate file_name {file_name!r}")
        seen_names.add(folded_name)
    return review_format, images


def normalize_scene_type(scene_type, where, allow_legacy):
    if allow_legacy and isinstance(scene_type, str) and scene_type in LEGACY_SCENE_TYPES:
        scene_type = LEGACY_SCENE_TYPES[scene_type]
    if not isinstance(scene_type, str) or scene_type not in SCENE_TYPES:
        accepted = set(SCENE_TYPES) | (set(LEGACY_SCENE_TYPES) if allow_legacy else set())
        raise ConversionError(
            f"{where}: scene_type must be one of {', '.join(sorted(accepted))}; got {scene_type!r}"
        )
    return scene_type


def normalize_surface_types(value, where, required=False):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConversionError(f"{where}: depiction_surface_types must be an array of strings")
    if len(value) != len(set(value)):
        raise ConversionError(f"{where}: depiction_surface_types must not contain duplicates")
    unknown = sorted(set(value) - DEPICTION_SURFACE_TYPES)
    if unknown:
        raise ConversionError(
            f"{where}: depiction_surface_types contains unsupported value(s): {', '.join(unknown)}"
        )
    if required and not value:
        raise ConversionError(f"{where}: depiction_surface_types must be non-empty for this scene or annotation")
    return list(value)


def normalize_surface_inventory(value, where, required=False):
    if not isinstance(value, list):
        raise ConversionError(f"{where}: depiction_surfaces must be an array of surface records")
    if required and not value:
        raise ConversionError(f"{where}: depiction_surfaces must be non-empty for depiction scenes")
    inventory = []
    seen_ids = set()
    for index, record in enumerate(value):
        record_where = f"{where} depiction_surfaces[{index}]"
        if not isinstance(record, dict) or set(record) != {"surface_id", "surface_type"}:
            raise ConversionError(
                f"{record_where} must contain exactly surface_id and surface_type"
            )
        surface_id = record.get("surface_id")
        if (not isinstance(surface_id, str) or not surface_id.strip()
                or surface_id != surface_id.strip()
                or any(ord(char) < 32 for char in surface_id)):
            raise ConversionError(f"{record_where}: surface_id must be a non-empty trimmed string")
        if surface_id in seen_ids:
            raise ConversionError(f"{record_where}: duplicate surface_id {surface_id!r}")
        seen_ids.add(surface_id)
        surface_type = record.get("surface_type")
        if not isinstance(surface_type, str) or surface_type not in DEPICTION_SURFACE_TYPES:
            raise ConversionError(
                f"{record_where}: surface_type must be one of {', '.join(sorted(DEPICTION_SURFACE_TYPES))}"
            )
        inventory.append({"surface_id": surface_id, "surface_type": surface_type})
    return inventory


def validate_assignment(
    split, group_id, scene_type, where, allow_legacy=False,
    surface_types=None, depiction_surfaces=None,
):
    if not isinstance(split, str) or split not in SPLITS:
        raise ConversionError(f"{where}: split must be train, val, or test; got {split!r}")
    if not group_id or any(ord(char) < 32 for char in group_id):
        raise ConversionError(f"{where}: group_id must be non-empty and contain no control characters")
    normalized_scene = normalize_scene_type(scene_type, where, allow_legacy)
    surfaces = list(surface_types or [])
    if normalized_scene == "other" and surfaces:
        raise ConversionError(
            f"{where}: scene_type='other' cannot declare depiction_surface_types; "
            "use depiction_only or mixed_scene when people appear on a display surface"
        )
    return {
        "split": split,
        "group_id": group_id,
        "scene_type": normalized_scene,
        "depiction_surface_types": surfaces,
        "depiction_surfaces": list(depiction_surfaces or []),
    }


def validate_group_splits(assignments):
    group_ids = {}
    for image_id, assignment in assignments.items():
        group_id = assignment["group_id"]
        split = assignment["split"]
        group_key = group_id.casefold()
        previous = group_ids.setdefault(group_key, (group_id, split))
        if previous[1] != split:
            raise ConversionError(
                f"image {image_id}: group_id {group_id!r} appears in both "
                f"{previous[1]} and {split}; keep every frame or variant from one group in one split"
            )
        if previous[0] != group_id:
            raise ConversionError(
                f"image {image_id}: group_id {group_id!r} duplicates {previous[0]!r} "
                f"case-insensitively within split {split}; use one consistent group_id spelling"
            )


def load_embedded_assignments(images, review_format):
    assignments = {}
    for index, image in enumerate(images):
        where = f"Review JSON images[{index}]"
        group_id = image.get("group_id")
        if not isinstance(group_id, str):
            raise ConversionError(f"{where}: {review_format[-2:]} image must define string group_id")
        if review_format == REVIEW_FORMAT_V7:
            scene_type = normalize_scene_type(image.get("scene_type"), where, allow_legacy=False)
            surfaces = normalize_surface_types(
                image.get("depiction_surface_types"), where,
                required=scene_type in {"depiction_only", "mixed_scene"},
            )
            inventory = normalize_surface_inventory(
                image.get("depiction_surfaces"), where,
                required=scene_type in {"depiction_only", "mixed_scene"},
            )
            inventory_types = list(dict.fromkeys(
                record["surface_type"] for record in inventory
            ))
            if set(surfaces) != set(inventory_types):
                raise ConversionError(
                    f"{where}: depiction_surface_types must equal the unique types derived from depiction_surfaces"
                )
            assignment = validate_assignment(
                image.get("split"), group_id.strip(), scene_type, where,
                surface_types=surfaces, depiction_surfaces=inventory,
            )
        elif review_format in {REVIEW_FORMAT_V3, REVIEW_FORMAT_V4}:
            scene_type = normalize_scene_type(image.get("scene_type"), where, allow_legacy=False)
            surfaces = normalize_surface_types(
                image.get("depiction_surface_types"),
                where,
            )
            if scene_type in {"depiction_only", "mixed_scene"} or surfaces:
                raise ConversionError(
                    f"{where}: {review_format} has no per-surface instance IDs; "
                    "re-export depiction scenes as helmet-vision-review-v7"
                )
            assignment = validate_assignment(
                image.get("split"), group_id.strip(), scene_type, where,
                surface_types=surfaces,
            )
        else:
            assignment = validate_assignment(
                image.get("split"), group_id.strip(), image.get("scene_type"), where,
                allow_legacy=True,
            )
            if assignment["scene_type"] in {"depiction_only", "mixed_scene"}:
                raise ConversionError(
                    f"{where}: {review_format} has no per-surface instance IDs; "
                    "re-export depiction scenes as helmet-vision-review-v7"
                )
        assignments[image["image_id"]] = assignment
    validate_group_splits(assignments)
    return assignments


def normalize_rights(value, where):
    if not isinstance(value, dict):
        raise ConversionError(f"{where}: rights must be an object")
    training_use = value.get("training_use")
    if not isinstance(training_use, str) or training_use not in TRAINING_USE_VALUES:
        raise ConversionError(
            f"{where}: training_use must be one of {', '.join(sorted(TRAINING_USE_VALUES))}"
        )
    if training_use != "approved":
        raise ConversionError(f"{where}: image is not approved for model training (training_use={training_use!r})")

    basis = value.get("basis")
    if not isinstance(basis, str) or basis not in RIGHTS_BASES:
        raise ConversionError(f"{where}: basis must be one of {', '.join(sorted(RIGHTS_BASES))}")

    normalized = {"training_use": training_use, "basis": basis}
    for field in ("source_reference", "license_id", "attribution"):
        field_value = value.get(field, "")
        if not isinstance(field_value, str):
            raise ConversionError(f"{where}: rights.{field} must be a string")
        normalized[field] = field_value.strip()

    if not normalized["source_reference"]:
        raise ConversionError(f"{where}: rights.source_reference is required")
    if basis == "license" and not normalized["license_id"]:
        raise ConversionError(f"{where}: rights.license_id is required for basis='license'")
    if basis == "license" and not normalized["attribution"]:
        raise ConversionError(f"{where}: rights.attribution is required for basis='license'")
    return normalized


def load_embedded_rights(images):
    return {
        image["image_id"]: normalize_rights(
            image.get("rights"), f"Review JSON image {image['image_id']}"
        )
        for image in images
    }


def load_split_manifest(path, images):
    expected_ids = {image["image_id"] for image in images}
    assignments = {}
    group_splits = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
                raise ConversionError(
                    "Split manifest header must be exactly: " + ",".join(MANIFEST_COLUMNS)
                )
            for line_number, row in enumerate(reader, start=2):
                where = f"Split manifest line {line_number}"
                if None in row or any(value is None for value in row.values()):
                    raise ConversionError(f"{where}: expected exactly four CSV values")
                image_id = safe_image_id(row["image_id"].strip(), where)
                if image_id in assignments:
                    raise ConversionError(f"{where}: duplicate image_id {image_id!r}")
                split = row["split"].strip()
                group_id = row["group_id"].strip()
                scene_type = row["scene_type"].strip()
                if split not in SPLITS:
                    raise ConversionError(f"{where}: split must be train, val, or test; got {split!r}")
                if not group_id or any(ord(char) < 32 for char in group_id):
                    raise ConversionError(f"{where}: group_id must be non-empty and contain no control characters")
                assignment = validate_assignment(
                    split, group_id, scene_type, where, allow_legacy=True
                )
                previous_split = group_splits.setdefault(group_id, split)
                if previous_split != split:
                    raise ConversionError(
                        f"{where}: group_id {group_id!r} appears in both {previous_split} and {split}; "
                        "keep every frame or variant from a group in one split"
                    )
                assignments[image_id] = assignment
    except (OSError, UnicodeError, csv.Error) as error:
        raise ConversionError(f"Cannot read split manifest {path}: {error}") from error

    missing = sorted(expected_ids - assignments.keys())
    extra = sorted(assignments.keys() - expected_ids)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing rows for {len(missing)} review image(s), e.g. {missing[0]}")
        if extra:
            details.append(f"unknown image_id {extra[0]!r}")
        raise ConversionError("Split manifest must have exactly one row per review image: " + "; ".join(details))
    validate_group_splits(assignments)
    return assignments


def load_rights_manifest(path, images):
    expected_ids = {image["image_id"] for image in images}
    rights = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != RIGHTS_MANIFEST_COLUMNS:
                raise ConversionError(
                    "Rights manifest header must be exactly: " + ",".join(RIGHTS_MANIFEST_COLUMNS)
                )
            for line_number, row in enumerate(reader, start=2):
                where = f"Rights manifest line {line_number}"
                if None in row or any(value is None for value in row.values()):
                    raise ConversionError(
                        f"{where}: expected exactly {len(RIGHTS_MANIFEST_COLUMNS)} CSV values"
                    )
                image_id = safe_image_id(row["image_id"].strip(), where)
                if image_id in rights:
                    raise ConversionError(f"{where}: duplicate image_id {image_id!r}")
                rights[image_id] = normalize_rights(
                    {field: row[field].strip() for field in RIGHTS_MANIFEST_COLUMNS if field != "image_id"},
                    where,
                )
    except (OSError, UnicodeError, csv.Error) as error:
        raise ConversionError(f"Cannot read rights manifest {path}: {error}") from error

    missing = sorted(expected_ids - rights.keys())
    extra = sorted(rights.keys() - expected_ids)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing rows for {len(missing)} review image(s), e.g. {missing[0]}")
        if extra:
            details.append(f"unknown image_id {extra[0]!r}")
        raise ConversionError("Rights manifest must have exactly one row per review image: " + "; ".join(details))
    return rights


def resolve_source_images(images_dir, images):
    try:
        root = images_dir.resolve(strict=True)
    except OSError as error:
        raise ConversionError(f"Source images directory does not exist: {images_dir}") from error
    if not root.is_dir():
        raise ConversionError(f"Source images path is not a directory: {root}")

    by_name = {}
    try:
        for candidate in root.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_FORMATS:
                continue
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(root):
                raise ConversionError(f"Source image symlink escapes --images-dir: {candidate}")
            key = candidate.name.casefold()
            if key in by_name:
                raise ConversionError(
                    f"Duplicate source image filename {candidate.name!r}; filenames must be unique "
                    "across --images-dir"
                )
            by_name[key] = candidate
    except OSError as error:
        raise ConversionError(f"Cannot scan source images directory {root}: {error}") from error

    resolved = {}
    for item in images:
        file_name = item["file_name"]
        source = by_name.get(file_name.casefold())
        if source is None:
            raise ConversionError(
                f"No source image matches {file_name!r}; copy the original file into --images-dir"
            )
        if source.name != file_name:
            raise ConversionError(
                f"Source filename casing differs for {file_name!r}: found {source.name!r}; "
                "make the names match exactly"
            )
        resolved[item["image_id"]] = source

    digest_to_image_id = {}
    for item in images:
        image_id = item["image_id"]
        source = resolved[image_id]
        digest = hashlib.sha256()
        try:
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError as error:
            raise ConversionError(f"Cannot read source image for SHA-256 validation {source}: {error}") from error
        source_digest = digest.hexdigest()
        previous_image_id = digest_to_image_id.get(source_digest)
        if previous_image_id is not None:
            raise ConversionError(
                f"{source.name}: source bytes exactly match image_id {previous_image_id!r}; "
                "remove duplicate image files and keep source groups in one split"
            )
        digest_to_image_id[source_digest] = image_id
    return root, resolved


def image_dimensions(path, expected_width, expected_height):
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as error:
        raise ConversionError("Pillow is required to verify source images; install it with `python -m pip install Pillow`") from error

    expected_format = IMAGE_FORMATS[path.suffix.lower()]
    try:
        with Image.open(path) as image:
            actual_format = image.format
            width, height = image.size
            image.verify()
        if actual_format != expected_format:
            raise ConversionError(
                f"{path}: suffix indicates {expected_format}, but image content is {actual_format}; "
                "rename or replace the source image"
            )
    except ConversionError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ConversionError(f"Cannot verify image {path}: {error}") from error

    if type(expected_width) is not int or type(expected_height) is not int or expected_width <= 0 or expected_height <= 0:
        raise ConversionError(f"{path.name}: review JSON width and height must be positive integers")
    if (width, height) != (expected_width, expected_height):
        raise ConversionError(
            f"{path.name}: image dimensions are {width}x{height}, but review JSON records "
            f"{expected_width}x{expected_height}; re-export or replace the image"
        )
    return width, height


def validate_box(annotation, where):
    coordinates = [annotation.get(key) for key in ("x", "y", "width", "height")]
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in coordinates):
        raise ConversionError(f"{where}: x, y, width, and height must be finite numbers")
    x, y, width, height = coordinates
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > 1 or y + height > 1:
        raise ConversionError(f"{where}: box must have positive size and stay inside normalized image bounds [0, 1]")
    return float(x), float(y), float(width), float(height)


def union_area(rectangles):
    valid = [box for box in rectangles if box[2] > box[0] and box[3] > box[1]]
    x_edges = sorted({edge for box in valid for edge in (box[0], box[2])})
    total = 0.0
    for left, right in zip(x_edges, x_edges[1:]):
        if right <= left:
            continue
        intervals = sorted((box[1], box[3]) for box in valid if box[0] < right and box[2] > left)
        covered_y = 0.0
        if intervals:
            start, end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start > end:
                    covered_y += end - start
                    start, end = next_start, next_end
                else:
                    end = max(end, next_end)
            covered_y += end - start
        total += (right - left) * covered_y
    return total


def head_source_disposition(box, regions):
    x, y, width, height = box
    right, bottom = x + width, y + height
    center_x, center_y = x + width / 2, y + height / 2
    center_inside = any(
        center_x >= rx and center_x <= rr and center_y >= ry and center_y <= rb
        for rx, ry, rr, rb in regions
    )
    intersections = [
        (max(x, rx), max(y, ry), min(right, rr), min(bottom, rb))
        for rx, ry, rr, rb in regions
    ]
    coverage = union_area(intersections) / (width * height)
    if center_inside or coverage >= 0.5:
        return "depicted"
    if coverage > 0:
        return "uncertain"
    return "clear"


def validate_image_annotations(item, assignment, review_format=REVIEW_FORMAT_V7):
    where = f"image {item['image_id']}"
    has_surface_review_v7 = review_format == REVIEW_FORMAT_V7
    if item.get("frame_source_status") != "clear":
        raise ConversionError(f"{where}: frame_source_status must be 'clear'; review the full frame in the browser first")
    if (assignment["scene_type"] == "other"
            and item.get("other_scene_no_depicted_people_reviewed") is not True):
        raise ConversionError(
            f"{where}: scene_type='other' requires an explicit full-frame browser review "
            "confirming no people appear in posters, printed photos, or screens"
        )
    annotations = item.get("annotations")
    if not isinstance(annotations, list):
        raise ConversionError(f"{where}: annotations must be an array")
    image_review_status = item.get("image_review_status")
    if (not isinstance(image_review_status, str)
            or image_review_status not in {"reviewed_empty", "reviewed_with_labels"}):
        raise ConversionError(
            f"{where}: image_review_status must be terminal 'reviewed_empty' or 'reviewed_with_labels'; "
            "unreviewed or unresolved images cannot enter the dataset"
        )
    if image_review_status == "reviewed_empty" and annotations:
        raise ConversionError(
            f"{where}: reviewed_empty requires zero review annotations; use reviewed_with_labels for annotated images"
        )
    if image_review_status == "reviewed_with_labels" and not annotations:
        raise ConversionError(
            f"{where}: reviewed_with_labels requires at least one resolved review annotation"
        )

    parsed = []
    regions = []
    region_surface_ids = []
    inventory_by_id = {
        surface["surface_id"]: surface
        for surface in assignment["depiction_surfaces"]
    }
    for index, annotation in enumerate(annotations):
        ann_where = f"{where}, annotations[{index}]"
        if not isinstance(annotation, dict):
            raise ConversionError(f"{ann_where}: annotation must be an object")
        class_id = annotation.get("class_id")
        class_name = annotation.get("class_name")
        if type(class_id) is not int or not 0 <= class_id < len(CLASSES) or class_name != CLASSES[class_id]:
            raise ConversionError(
                f"{ann_where}: invalid class_id/class_name mapping; expected an exact project ontology pair"
            )
        if not has_surface_review_v7 and class_id in {5, 7}:
            raise ConversionError(
                f"{ann_where}: {review_format} depiction annotations lack per-surface instance IDs; "
                "re-export as helmet-vision-review-v7"
            )
        region_surface = None
        if class_id == 7:
            surface_id = annotation.get("depiction_surface_id")
            if not isinstance(surface_id, str):
                raise ConversionError(
                    f"{ann_where}: depiction_region must reference a declared v7 depiction_surface_id"
                )
            region_surface = inventory_by_id.get(surface_id)
            if not has_surface_review_v7 or region_surface is None:
                raise ConversionError(
                    f"{ann_where}: depiction_region must reference a declared v7 depiction_surface_id"
                )
            if ("depiction_surface_type" in annotation
                    and annotation.get("depiction_surface_type") != region_surface["surface_type"]):
                raise ConversionError(
                    f"{ann_where}: depiction_surface_type conflicts with the referenced surface inventory"
                )
        elif "depiction_surface_id" in annotation or "depiction_surface_type" in annotation:
            raise ConversionError(
                f"{ann_where}: depiction surface fields are only valid on a depiction_region annotation"
            )
        if has_surface_review_v7 and class_id == 5 and not assignment["depiction_surfaces"]:
            raise ConversionError(
                f"{ann_where}: depicted_hat requires a declared depiction surface in v7"
            )
        box = validate_box(annotation, ann_where)
        state = annotation.get("review_state")
        if state == "uncertain":
            raise ConversionError(f"{ann_where}: review_state is uncertain; resolve it in the browser before conversion")
        if state not in {"confirmed", "depicted"}:
            raise ConversionError(f"{ann_where}: review_state must be 'confirmed' or 'depicted'")
        counts = annotation.get("counts_as_real_wearer")
        if type(counts) is not bool:
            raise ConversionError(f"{ann_where}: counts_as_real_wearer must be true or false")
        parsed.append((class_id, box, state, counts, ann_where, region_surface))
        if class_id == 7:
            x, y, width, height = box
            regions.append((x, y, x + width, y + height))
            region_surface_ids.append(region_surface["surface_id"])

    if has_surface_review_v7:
        declared_ids = set(inventory_by_id)
        annotated_ids = set(region_surface_ids)
        duplicate_ids = sorted(
            surface_id for surface_id in annotated_ids
            if region_surface_ids.count(surface_id) > 1
        )
        missing_ids = sorted(declared_ids - annotated_ids)
        orphan_ids = sorted(annotated_ids - declared_ids)
        if duplicate_ids or missing_ids or orphan_ids:
            details = []
            if duplicate_ids:
                details.append("duplicate region IDs: " + ", ".join(duplicate_ids))
            if missing_ids:
                details.append("surfaces without a region: " + ", ".join(missing_ids))
            if orphan_ids:
                details.append("regions with unknown IDs: " + ", ".join(orphan_ids))
            raise ConversionError(
                f"{where}: every declared depiction surface must have exactly one region; "
                + "; ".join(details)
            )
    expected_region_count = len(assignment["depiction_surfaces"])
    if (has_surface_review_v7 and len(regions) != expected_region_count):
        raise ConversionError(
            f"{where}: expected exactly {expected_region_count} depiction_region box(es), "
            "one for each declared surface instance; "
            "if a display surface is borderless or cannot be boxed, "
            "keep frame_source_status='review_required' and exclude it from the dataset"
        )
    if (assignment["scene_type"] == "other"
            and any(class_id in {5, 7} for class_id, *_ in parsed)):
        raise ConversionError(
            f"{where}: scene_type='other' cannot contain depicted_hat or depiction_region annotations"
        )

    labels = []
    emitted_region_surfaces = []
    emitted_region_boxes = set()
    emitted_worn = 0
    for class_id, box, state, counts, ann_where, region_surface in parsed:
        if class_id in SOURCE_DEPENDENT_HEAD_IDS:
            if assignment["scene_type"] == "depiction_only":
                if state != "depicted" or counts:
                    raise ConversionError(
                        f"{ann_where}: depiction_only head candidates must be marked depicted "
                        "and never counted as real wearers"
                    )
                continue
            disposition = head_source_disposition(box, regions)
            if disposition == "depicted":
                if state != "depicted" or counts:
                    raise ConversionError(
                        f"{ann_where}: box is suppressed by a poster/photo/screen union region; "
                        "mark it depicted in the browser and do not count it as a real wearer"
                    )
                continue
            if disposition == "uncertain":
                raise ConversionError(
                    f"{ann_where}: real-head box partly overlaps a depiction region; resolve the uncertainty in the browser"
                )
            expected_count = class_id in TARGET_WORN_IDS
            if state != "confirmed" or counts is not expected_count:
                if expected_count:
                    raise ConversionError(
                        f"{ann_where}: a zero-overlap worn box must be confirmed and count_as_real_wearer=true"
                    )
                raise ConversionError(
                    f"{ann_where}: a zero-overlap bare_head box must be confirmed as a real-scene head "
                    "with counts_as_real_wearer=false"
                )
            if expected_count:
                emitted_worn += 1
        elif state != "confirmed" or counts:
            raise ConversionError(
                f"{ann_where}: non-worn classes must be confirmed with counts_as_real_wearer=false"
            )

        x, y, width, height = box
        yolo_geometry = (
            f"{x + width / 2:.8f}", f"{y + height / 2:.8f}",
            f"{width:.8f}", f"{height:.8f}",
        )
        train_class_id = REVIEW_TO_TRAIN_CLASS.get(class_id)
        if train_class_id is None:
            continue
        labels.append(f"{train_class_id} {' '.join(yolo_geometry)}")
        if class_id == 7:
            emitted_box = tuple(float(value) for value in yolo_geometry)
            if emitted_box in emitted_region_boxes:
                raise ConversionError(
                    f"{ann_where}: depiction_region geometry duplicates another surface instance"
                )
            emitted_region_boxes.add(emitted_box)
            emitted_region_surfaces.append({
                "surface_id": region_surface["surface_id"],
                "surface_type": region_surface["surface_type"],
                "box": list(emitted_box),
            })

    count = item.get("real_wearer_count")
    if type(count) is not int or count != emitted_worn:
        raise ConversionError(
            f"{where}: real_wearer_count={count!r} does not match {emitted_worn} confirmed, unsuppressed worn box(es)"
        )
    return labels, emitted_region_surfaces


def write_dataset(images, assignments, rights, sources, output_stage, review_format):
    split_counts = {split: [0] * len(TRAIN_CLASSES) for split in SPLITS}
    split_image_counts = {split: 0 for split in SPLITS}
    region_surfaces_by_image = {}
    test_rows = []
    for split in SPLITS:
        (output_stage / "images" / split).mkdir(parents=True)
        (output_stage / "labels" / split).mkdir(parents=True)

    for item in images:
        image_id = item["image_id"]
        assignment = assignments[image_id]
        split = assignment["split"]
        split_image_counts[split] += 1
        source = sources[image_id]
        image_dimensions(source, item.get("width"), item.get("height"))
        labels, region_surfaces = validate_image_annotations(
            item, assignment, review_format=review_format
        )
        region_surfaces_by_image[image_id] = region_surfaces
        target_image = output_stage / "images" / split / f"{image_id}{source.suffix.lower()}"
        target_label = output_stage / "labels" / split / f"{image_id}.txt"
        shutil.copy2(source, target_image)
        target_label.write_text("\n".join(labels) + ("\n" if labels else ""), encoding="utf-8")
        for line in labels:
            split_counts[split][int(line.split(" ", 1)[0])] += 1
        if split == "test":
            test_rows.append((
                image_id,
                assignment["scene_type"],
                assignment["depiction_surface_types"],
                assignment["depiction_surfaces"],
                region_surfaces,
            ))

    empty_splits = [split for split in SPLITS if split_image_counts[split] == 0]
    if empty_splits:
        raise ConversionError("Each split must contain at least one image; empty: " + ", ".join(empty_splits))

    test_scenes = {row[1] for row in test_rows}
    missing_test_scenes = {"depiction_only", "mixed_scene"} - test_scenes
    if missing_test_scenes:
        raise ConversionError(
            "The locked test split must include at least one reviewed depiction_only and one mixed_scene image "
            "so the evaluator can assess depiction gates; missing " + ", ".join(sorted(missing_test_scenes))
        )

    missing_by_split = {
        split: [TRAIN_CLASSES[index] for index, count in enumerate(counts) if count == 0]
        for split, counts in split_counts.items()
        if split in {"train", "val"} and any(count == 0 for count in counts)
    }
    if missing_by_split:
        details = "; ".join(f"{split}: {', '.join(names)}" for split, names in missing_by_split.items())
        raise ConversionError(
            "The hardhat target and depiction-region support class must each have boxes in train and val; missing " + details
        )

    yaml_lines = ["path: .", "train: images/train", "val: images/val", "test: images/test", "names:"]
    yaml_lines.extend(f"  {index}: {name}" for index, name in enumerate(TRAIN_CLASSES))
    (output_stage / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    manifest_path = output_stage / "split_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(MANIFEST_COLUMNS)
        writer.writerows(
            (
                image["image_id"],
                assignments[image["image_id"]]["split"],
                assignments[image["image_id"]]["group_id"],
                assignments[image["image_id"]]["scene_type"],
            )
            for image in images
        )

    image_sources = {
        "format": "helmet-vision-image-sources-v4",
        "review_format": REVIEW_FORMAT_V7,
        "images": [
            {
                "image_id": image["image_id"],
                "file_name": image["file_name"],
                "image_review_status": image["image_review_status"],
                **assignments[image["image_id"]],
                "depiction_region_surfaces": region_surfaces_by_image[image["image_id"]],
                "review_class_counts": {
                    class_name: sum(
                        annotation["class_id"] == class_id
                        for annotation in image["annotations"]
                    )
                    for class_id, class_name in enumerate(CLASSES)
                },
                "rights": rights[image["image_id"]],
            }
            for image in images
        ],
    }
    (output_stage / "dataset_image_sources.json").write_text(
        json.dumps(image_sources, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return test_rows


def write_hard_negative_source_group_template(path, assignments):
    groups = sorted(
        {
            (assignment["split"], assignment["group_id"])
            for assignment in assignments.values()
        },
        key=lambda item: (item[0], item[1].casefold(), item[1]),
    )
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow((
            "split", "group_id", "review_status",
            "hard_negative_sources", "hat_type_negative_sources",
        ))
        for split, group_id in groups:
            writer.writerow((split, group_id, "pending", "", ""))


def create_zip(dataset_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dataset_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(dataset_dir.name) / path.relative_to(dataset_dir))


def publish(
    output_dir, zip_path, sidecar_path, source_groups_path,
    images, assignments, rights, sources, review_format,
):
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    targets = (output_dir, zip_path, sidecar_path, source_groups_path)
    if any(path.exists() for path in targets):
        existing = [str(path) for path in targets if path.exists()]
        raise ConversionError("Output target already exists; choose a new output-dir: " + ", ".join(existing))

    published = []
    try:
        with tempfile.TemporaryDirectory(prefix=".helmet-yolo-", dir=parent) as temporary:
            stage_root = Path(temporary)
            staged_dataset = stage_root / output_dir.name
            staged_dataset.mkdir()
            test_rows = write_dataset(
                images, assignments, rights, sources, staged_dataset, review_format
            )
            staged_sidecar = stage_root / sidecar_path.name
            with staged_sidecar.open("w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, lineterminator="\n")
                writer.writerow((
                    "image_id", "scene_type", "depiction_surface_types",
                    "depiction_surfaces", "depiction_region_surfaces",
                ))
                writer.writerows(
                    (
                        image_id,
                        scene_type,
                        json.dumps(surface_types, separators=(",", ":")),
                        json.dumps(surfaces, separators=(",", ":")),
                        json.dumps(region_surfaces, separators=(",", ":")),
                    )
                    for image_id, scene_type, surface_types, surfaces, region_surfaces in test_rows
                )
            staged_source_groups = stage_root / source_groups_path.name
            write_hard_negative_source_group_template(staged_source_groups, assignments)
            staged_zip = stage_root / zip_path.name
            create_zip(staged_dataset, staged_zip)

            os.replace(staged_dataset, output_dir)
            published.append(output_dir)
            os.replace(staged_zip, zip_path)
            published.append(zip_path)
            os.replace(staged_sidecar, sidecar_path)
            published.append(sidecar_path)
            os.replace(staged_source_groups, source_groups_path)
            published.append(source_groups_path)
    except Exception:
        for path in reversed(published):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-json", required=True, type=Path,
        help="Browser helmet-vision-review-v7 export with terminal per-image review status; older formats are not release-compatible",
    )
    parser.add_argument("--images-dir", required=True, type=Path, help="Directory containing original reviewed images")
    parser.add_argument("--output-dir", required=True, type=Path, help="New dataset directory to create")
    args = parser.parse_args(argv)

    try:
        review_format, images = load_review(args.review_json.expanduser())
        assignments = load_embedded_assignments(images, review_format)
        rights = load_embedded_rights(images)
        images_root, sources = resolve_source_images(args.images_dir.expanduser(), images)
        output_dir = args.output_dir.expanduser().absolute()
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        output_dir = output_dir.resolve()
        if output_dir == images_root or output_dir.is_relative_to(images_root):
            raise ConversionError("--output-dir must be outside --images-dir so generated files cannot mix with source images")
        zip_path = Path(str(output_dir) + ".zip")
        sidecar_path = output_dir.parent / "test_scene_metadata.csv"
        source_groups_path = output_dir.parent / f"{output_dir.name}_hard_negative_source_groups.csv"
        publish(
            output_dir, zip_path, sidecar_path, source_groups_path,
            images, assignments, rights, sources, review_format,
        )
    except ConversionError as error:
        print(f"Conversion failed: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Conversion failed while writing outputs: {error}", file=sys.stderr)
        return 2

    print(f"Created YOLO dataset: {output_dir}")
    print(f"Created ZIP: {zip_path}")
    print(f"Created test scene metadata: {sidecar_path}")
    print(f"Created pending hard-negative group template: {source_groups_path}")
    print(f"Created split manifest: {output_dir / 'split_manifest.csv'}")
    print(f"Created image source metadata: {output_dir / 'dataset_image_sources.json'}")
    print("No training was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
