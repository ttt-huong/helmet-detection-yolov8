"""Descriptively compare two browser review-v7 exports.

The command hashes original image files and compares only exact SHA-256
matches. It never merges reviews, adjudicates labels, approves rights, or
turns an agreement percentage into an approval decision.

Example:
    python scripts/compare_two_reviews.py --roster pilot-roster.csv \
        --review-a a.json --images-a images-a --reviewer-a reviewer-a \
        --review-b b.json --images-b images-b --reviewer-b reviewer-b \
        --output-dir reports/two-review-pilot

Roster CSV columns: sha256,width,height,file_name_a,file_name_b.

Only helmet-vision-review-v7 is accepted. Each image must carry an explicit
terminal image_review_status (reviewed_empty or reviewed_with_labels).
Image-status agreement is descriptive and never constitutes a pilot pass.

Pillow is required for image format and dimension verification. The output
directory must be new. Roster integrity problems are reported and cause a
nonzero exit status.

Eligible box pairs use maximum-cardinality matching first, then maximum total
IoU. Remaining ties are deterministic by annotation array order.
"""

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
import sys
import uuid
from collections import Counter
from pathlib import Path


REVIEW_FORMAT = "helmet-vision-review-v7"
IMAGE_REVIEW_STATUSES = {"reviewed_empty", "reviewed_with_labels"}
CLASS_NAMES = (
    "hard_hat_worn", "traffic_helmet_worn", "cap_worn", "beanie_worn",
    "bare_head", "depicted_hat", "loose_hat", "depiction_region",
)
OBJECT_CLASS_IDS = tuple(range(7))
SURFACE_TYPES = ("poster", "printed_photo", "screen", "other_depiction")
SCENE_TYPES = {"depiction_only", "mixed_scene", "other"}
FRAME_SOURCE_STATUSES = {"clear", "review_required"}
REVIEW_STATES = {"confirmed", "depicted", "uncertain"}
IMAGE_FORMATS = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
    ".webp": "WEBP",
}


class ComparisonError(Exception):
    """An input or output contract error."""


def reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ComparisonError(f"JSON contains duplicate key {key!r}")
        result[key] = value
    return result


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def safe_file_name(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ComparisonError(f"{where}: file_name must be a non-empty basename")
    if value in {".", ".."} or "/" in value or "\\" in value or Path(value).name != value:
        raise ComparisonError(f"{where}: unsafe file_name {value!r}; path components are not allowed")
    if Path(value).suffix.lower() not in IMAGE_FORMATS:
        raise ComparisonError(f"{where}: unsupported image suffix for {value!r}")
    return value


def source_category(class_id):
    if class_id == 5:
        return "depicted"
    if class_id == 6:
        return "loose_physical_hat"
    if class_id == 7:
        return "surface_boundary"
    return "context_dependent_head"


def validate_image(raw, index):
    where = f"images[{index}]"
    if not isinstance(raw, dict):
        raise ComparisonError(f"{where}: expected an object")
    image_id = raw.get("image_id")
    if not isinstance(image_id, str):
        raise ComparisonError(f"{where}: image_id must be a UUID string")
    try:
        parsed_id = uuid.UUID(image_id)
    except (ValueError, AttributeError) as error:
        raise ComparisonError(f"{where}: invalid image_id {image_id!r}") from error
    if str(parsed_id) != image_id:
        raise ComparisonError(f"{where}: image_id must use canonical lowercase UUID form")

    file_name = safe_file_name(raw.get("file_name"), where)
    width, height = raw.get("width"), raw.get("height")
    if not is_int(width) or width < 1 or not is_int(height) or height < 1:
        raise ComparisonError(f"{where}: width and height must be positive integers")
    image_review_status = raw.get("image_review_status")
    if (not isinstance(image_review_status, str)
            or image_review_status not in IMAGE_REVIEW_STATUSES):
        raise ComparisonError(
            f"{where}: image_review_status must be terminal 'reviewed_empty' or 'reviewed_with_labels'"
        )
    scene_type = raw.get("scene_type")
    if not isinstance(scene_type, str) or scene_type not in SCENE_TYPES:
        raise ComparisonError(f"{where}: unsupported scene_type")
    frame_status = raw.get("frame_source_status")
    if not isinstance(frame_status, str) or frame_status not in FRAME_SOURCE_STATUSES:
        raise ComparisonError(f"{where}: unsupported frame_source_status")
    other_reviewed = raw.get("other_scene_no_depicted_people_reviewed")
    if not isinstance(other_reviewed, bool):
        raise ComparisonError(f"{where}: other_scene_no_depicted_people_reviewed must be boolean")
    reviewed_at = raw.get("frame_source_reviewed_at")
    if reviewed_at is not None and not isinstance(reviewed_at, str):
        raise ComparisonError(f"{where}: frame_source_reviewed_at must be a string or null")
    reviewed_at_valid = False
    if isinstance(reviewed_at, str) and reviewed_at:
        try:
            parsed_reviewed_at = datetime.fromisoformat(
                reviewed_at[:-1] + "+00:00" if reviewed_at.endswith("Z") else reviewed_at
            )
            reviewed_at_valid = parsed_reviewed_at.tzinfo is not None
        except ValueError:
            pass

    surface_types = raw.get("depiction_surface_types")
    if (not isinstance(surface_types, list)
            or any(not isinstance(value, str) or value not in SURFACE_TYPES for value in surface_types)
            or len(set(surface_types)) != len(surface_types)):
        raise ComparisonError(f"{where}: invalid or duplicate depiction_surface_types")
    surfaces = raw.get("depiction_surfaces")
    if not isinstance(surfaces, list):
        raise ComparisonError(f"{where}: depiction_surfaces must be an array")
    surface_by_id = {}
    normalized_surfaces = []
    for surface_index, surface in enumerate(surfaces):
        surface_where = f"{where}.depiction_surfaces[{surface_index}]"
        if not isinstance(surface, dict) or set(surface) != {"surface_id", "surface_type"}:
            raise ComparisonError(f"{surface_where}: expected exactly surface_id and surface_type")
        surface_id = surface.get("surface_id")
        surface_type = surface.get("surface_type")
        if (not isinstance(surface_id, str) or not surface_id.strip()
                or surface_id != surface_id.strip()
                or any(ord(char) < 32 for char in surface_id)):
            raise ComparisonError(f"{surface_where}: invalid surface_id")
        if surface_id in surface_by_id:
            raise ComparisonError(f"{surface_where}: duplicate surface_id {surface_id!r}")
        if not isinstance(surface_type, str) or surface_type not in SURFACE_TYPES:
            raise ComparisonError(f"{surface_where}: unsupported surface_type")
        surface_by_id[surface_id] = surface_type
        normalized_surfaces.append({"surface_id": surface_id, "surface_type": surface_type})
    if set(surface_types) != {surface["surface_type"] for surface in normalized_surfaces}:
        raise ComparisonError(f"{where}: depiction_surface_types does not match physical surface inventory")

    annotations = raw.get("annotations")
    if not isinstance(annotations, list):
        raise ComparisonError(f"{where}: annotations must be an array")
    if image_review_status == "reviewed_empty" and annotations:
        raise ComparisonError(f"{where}: reviewed_empty requires zero annotations")
    if image_review_status == "reviewed_with_labels" and not annotations:
        raise ComparisonError(f"{where}: reviewed_with_labels requires at least one annotation")
    normalized_annotations = []
    for annotation_index, annotation in enumerate(annotations):
        annotation_where = f"{where}.annotations[{annotation_index}]"
        if not isinstance(annotation, dict):
            raise ComparisonError(f"{annotation_where}: expected an object")
        class_id = annotation.get("class_id")
        if not is_int(class_id) or class_id < 0 or class_id >= len(CLASS_NAMES):
            raise ComparisonError(f"{annotation_where}: class_id must be an integer from 0 to 7")
        class_name = annotation.get("class_name")
        if class_name != CLASS_NAMES[class_id]:
            raise ComparisonError(f"{annotation_where}: class_id and class_name do not match")
        values = [annotation.get(key) for key in ("x", "y", "width", "height")]
        if any(not is_number(value) or not math.isfinite(value) for value in values):
            raise ComparisonError(f"{annotation_where}: box coordinates must be finite numbers")
        x, y, box_width, box_height = (float(value) for value in values)
        if (x < 0 or y < 0 or box_width <= 0 or box_height <= 0
                or x + box_width > 1 or y + box_height > 1):
            raise ComparisonError(f"{annotation_where}: box must be inside normalized image bounds")
        review_state = annotation.get("review_state")
        if not isinstance(review_state, str) or review_state not in REVIEW_STATES:
            raise ComparisonError(f"{annotation_where}: unsupported review_state")
        counts_as_wearer = annotation.get("counts_as_real_wearer")
        if not isinstance(counts_as_wearer, bool):
            raise ComparisonError(f"{annotation_where}: counts_as_real_wearer must be boolean")
        if counts_as_wearer != (class_id == 0 and review_state == "confirmed"):
            raise ComparisonError(
                f"{annotation_where}: counts_as_real_wearer must be true only for confirmed class 0"
            )
        surface_id = annotation.get("depiction_surface_id")
        if class_id == 7:
            if not isinstance(surface_id, str) or surface_id not in surface_by_id:
                raise ComparisonError(f"{annotation_where}: depiction_region must reference an inventory surface")
        elif "depiction_surface_id" in annotation:
            raise ComparisonError(f"{annotation_where}: non-region annotation cannot have depiction_surface_id")
        normalized_annotations.append({
            "class_id": class_id,
            "class_name": class_name,
            "x": x, "y": y, "width": box_width, "height": box_height,
            "review_state": review_state,
            "depiction_surface_id": surface_id,
            "source_category": source_category(class_id),
        })

    if not is_int(raw.get("real_wearer_count")) or raw["real_wearer_count"] < 0:
        raise ComparisonError(f"{where}: real_wearer_count must be a non-negative integer")
    counted_wearers = sum(
        annotation["class_id"] == 0 and annotation["review_state"] == "confirmed"
        for annotation in normalized_annotations
    )
    if raw["real_wearer_count"] != counted_wearers:
        raise ComparisonError(f"{where}: real_wearer_count does not match confirmed class-0 annotations")
    rights = raw.get("rights")
    if not isinstance(rights, dict) or any(
        not isinstance(rights.get(key), str)
        for key in ("training_use", "basis", "source_reference", "license_id", "attribution")
    ):
        raise ComparisonError(f"{where}: rights must contain the v7 string fields")
    if rights["training_use"] not in {"unknown", "approved", "not_allowed"}:
        raise ComparisonError(f"{where}: rights.training_use has an unsupported value")
    if rights["basis"] not in {"", "owned", "permission", "license", "public_domain"}:
        raise ComparisonError(f"{where}: rights.basis has an unsupported value")
    if not isinstance(raw.get("group_id"), str):
        raise ComparisonError(f"{where}: group_id must be a string")
    split = raw.get("split")
    # Pilot reviews are compared before adjudication/group assignment. The
    # workflow explicitly leaves project group_id/split blank at this stage.
    if not isinstance(split, str) or split not in {"", "train", "val", "test"}:
        raise ComparisonError(f"{where}: split must be blank, train, val, or test")

    incomplete = []
    region_ids = [
        annotation["depiction_surface_id"] for annotation in normalized_annotations
        if annotation["class_id"] == 7
    ]
    region_boxes = [
        tuple(float(f"{value:.8f}") for value in (
            annotation["x"] + annotation["width"] / 2,
            annotation["y"] + annotation["height"] / 2,
            annotation["width"],
            annotation["height"],
        ))
        for annotation in normalized_annotations if annotation["class_id"] == 7
    ]
    regions = [annotation for annotation in normalized_annotations if annotation["class_id"] == 7]
    if scene_type in {"depiction_only", "mixed_scene"} and not normalized_surfaces:
        incomplete.append("depiction scene has no physical surface inventory")
    if (len(region_ids) != len(set(region_ids))
            or set(region_ids) != set(surface_by_id)
            or len(region_boxes) != len(set(region_boxes))):
        incomplete.append("depiction_region inventory is incomplete or has duplicate surface regions")
    if any(annotation["class_id"] == 5 for annotation in normalized_annotations) and not normalized_surfaces:
        incomplete.append("depicted_hat has no declared physical surface")
    if scene_type == "other" and (
        normalized_surfaces
        or any(annotation["class_id"] in {5, 7} for annotation in normalized_annotations)
        or not other_reviewed
    ):
        incomplete.append("scene_type=other conflicts with depiction inventory or lacks explicit review")
    if frame_status == "clear" and not reviewed_at:
        incomplete.append("clear frame_source_status has no review timestamp")
    if reviewed_at is not None and not reviewed_at_valid:
        incomplete.append("frame_source_reviewed_at is not a valid timezone-aware ISO timestamp")
    if frame_status == "review_required" and reviewed_at is not None:
        incomplete.append("review_required frame_source_status has a review timestamp")
    for annotation_index, annotation in enumerate(normalized_annotations):
        if annotation["class_id"] <= 4:
            if scene_type == "depiction_only":
                expected_state = "depicted"
            else:
                center_x = annotation["x"] + annotation["width"] / 2
                center_y = annotation["y"] + annotation["height"] / 2
                center_inside = any(
                    center_x >= region["x"]
                    and center_x <= region["x"] + region["width"]
                    and center_y >= region["y"]
                    and center_y <= region["y"] + region["height"]
                    for region in regions
                )
                coverage = union_coverage(annotation, regions)
                if center_inside or coverage >= 0.5:
                    expected_state = "depicted"
                elif coverage > 0 or frame_status != "clear" or (
                    scene_type == "other" and not other_reviewed
                ):
                    expected_state = "uncertain"
                elif annotation["review_state"] in {"confirmed", "uncertain"}:
                    expected_state = annotation["review_state"]
                else:
                    expected_state = "uncertain"
            if annotation["review_state"] != expected_state:
                incomplete.append(
                    f"annotations[{annotation_index}] review_state conflicts with source geometry/metadata"
                )
        elif annotation["review_state"] == "depicted":
            incomplete.append(
                f"annotations[{annotation_index}] non-head class cannot have review_state=depicted"
            )

    return {
        "image_id": image_id,
        "file_name": file_name,
        "width": width,
        "height": height,
        "image_review_status": image_review_status,
        "scene_type": scene_type,
        "frame_source_status": frame_status,
        "frame_source_reviewed_at": reviewed_at,
        "other_scene_no_depicted_people_reviewed": other_reviewed,
        "depiction_surface_types": sorted(surface_types),
        "surfaces": normalized_surfaces,
        "surface_by_id": surface_by_id,
        "annotations": normalized_annotations,
        "sha256": None,
        "actual_dimensions": None,
        "issues": [],
        "incomplete_issues": incomplete,
    }


def load_review(path, reviewer):
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            dataset = json.load(handle, object_pairs_hook=reject_duplicate_json_keys)
    except ComparisonError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ComparisonError(f"Cannot read {reviewer} review JSON {path}: {error}") from error
    if not isinstance(dataset, dict) or dataset.get("format") != REVIEW_FORMAT:
        raise ComparisonError(f"{reviewer} review must use {REVIEW_FORMAT}")
    expected_classes = [{"id": index, "name": name} for index, name in enumerate(CLASS_NAMES)]
    if dataset.get("classes") != expected_classes or not isinstance(dataset.get("rule"), str):
        raise ComparisonError(f"{reviewer} review class mapping or rule is invalid for v7")
    images = dataset.get("images")
    if not isinstance(images, list):
        raise ComparisonError(f"{reviewer} review images must be an array")

    records, invalid = [], []
    for index, raw in enumerate(images):
        try:
            records.append(validate_image(raw, index))
        except ComparisonError as error:
            invalid.append({
                "reviewer": reviewer,
                "image_id": raw.get("image_id") if isinstance(raw, dict) else None,
                "file_name": raw.get("file_name") if isinstance(raw, dict) else None,
                "issue": str(error),
            })
    duplicates = {}
    for record in records:
        duplicates.setdefault(("image_id", record["image_id"].casefold()), []).append(record)
        duplicates.setdefault(("file_name", record["file_name"].casefold()), []).append(record)
    marked = set()
    for (kind, value), group in duplicates.items():
        if len(group) > 1:
            for record in group:
                if id(record) not in marked:
                    record["issues"].append(f"duplicate {kind}: {value}")
                    marked.add(id(record))
    return records, invalid


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_source_images(records, image_root, reviewer):
    try:
        from PIL import Image
    except ImportError as error:
        raise ComparisonError("Pillow is required to verify source image dimensions") from error
    if not image_root.is_dir():
        for record in records:
            if not record["issues"]:
                record["issues"].append(f"{reviewer} image directory does not exist: {image_root}")
        return
    root = image_root.resolve()
    for record in records:
        if record["issues"]:
            continue
        path = image_root / record["file_name"]
        try:
            resolved = path.resolve(strict=True)
            if resolved.parent != root or path.is_symlink() or not resolved.is_file():
                raise OSError("image must be a regular file directly inside the supplied directory")
            record["sha256"] = sha256_file(resolved)
            with Image.open(resolved) as image:
                detected_format = image.format
                dimensions = image.size
                image.verify()
            expected_format = IMAGE_FORMATS[path.suffix.lower()]
            if detected_format != expected_format:
                raise OSError(f"extension expects {expected_format}, decoded {detected_format}")
            record["actual_dimensions"] = list(dimensions)
            if dimensions != (record["width"], record["height"]):
                record["issues"].append(
                    f"declared dimensions {record['width']}x{record['height']} do not match "
                    f"decoded dimensions {dimensions[0]}x{dimensions[1]}"
                )
        except (OSError, ValueError) as error:
            record["issues"].append(f"source image unavailable or invalid: {error}")


def read_roster(path):
    required = {"sha256", "width", "height", "file_name_a", "file_name_b"}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if (not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames))
                    or set(reader.fieldnames) != required):
                raise ComparisonError(
                    "predeclared roster CSV must have exactly these columns: "
                    "sha256,width,height,file_name_a,file_name_b"
                )
            rows = []
            seen_hashes, seen_a, seen_b = set(), set(), set()
            for line, raw in enumerate(reader, start=2):
                where = f"roster CSV line {line}"
                sha = raw.get("sha256", "").strip().lower()
                if len(sha) != 64 or any(char not in "0123456789abcdef" for char in sha):
                    raise ComparisonError(f"{where}: sha256 must contain exactly 64 hex characters")
                if sha in seen_hashes:
                    raise ComparisonError(f"{where}: duplicate roster sha256 {sha}")
                try:
                    width, height = int(raw.get("width", "")), int(raw.get("height", ""))
                except (TypeError, ValueError) as error:
                    raise ComparisonError(f"{where}: width and height must be positive integers") from error
                if width < 1 or height < 1:
                    raise ComparisonError(f"{where}: width and height must be positive integers")
                file_a = safe_file_name(raw.get("file_name_a", ""), where)
                file_b = safe_file_name(raw.get("file_name_b", ""), where)
                if file_a.casefold() in seen_a or file_b.casefold() in seen_b:
                    raise ComparisonError(f"{where}: duplicate reviewer-specific roster filename")
                seen_hashes.add(sha)
                seen_a.add(file_a.casefold())
                seen_b.add(file_b.casefold())
                rows.append({
                    "roster_index": len(rows),
                    "sha256": sha,
                    "width": width,
                    "height": height,
                    "file_name_a": file_a,
                    "file_name_b": file_b,
                    "source_valid_a": False,
                    "source_valid_b": False,
                })
    except ComparisonError:
        raise
    except (OSError, UnicodeError, csv.Error) as error:
        raise ComparisonError(f"Cannot read predeclared image roster {path}: {error}") from error
    if not rows:
        raise ComparisonError("predeclared image roster must contain at least one image")
    return rows


def inspect_roster_sources(roster, images_a, images_b):
    try:
        from PIL import Image
    except ImportError as error:
        raise ComparisonError("Pillow is required to verify roster source image dimensions") from error
    result = []
    for entry in roster:
        issues = []
        for reviewer, root, field in (
            ("a", images_a, "file_name_a"),
            ("b", images_b, "file_name_b"),
        ):
            if not root.is_dir():
                issues.append(f"reviewer {reviewer} source directory is missing: {root}")
                continue
            try:
                path = root / entry[field]
                resolved = path.resolve(strict=True)
                if resolved.parent != root.resolve() or path.is_symlink() or not resolved.is_file():
                    raise OSError("image must be a regular file directly inside the supplied directory")
                actual_hash = sha256_file(resolved)
                if actual_hash != entry["sha256"]:
                    raise OSError(f"SHA-256 mismatch: expected {entry['sha256']}, got {actual_hash}")
                with Image.open(resolved) as image:
                    detected_format = image.format
                    dimensions = image.size
                    image.verify()
                expected_format = IMAGE_FORMATS[path.suffix.lower()]
                if detected_format != expected_format:
                    raise OSError(f"extension expects {expected_format}, decoded {detected_format}")
                if dimensions != (entry["width"], entry["height"]):
                    raise OSError(
                        f"dimension mismatch: expected {entry['width']}x{entry['height']}, "
                        f"decoded {dimensions[0]}x{dimensions[1]}"
                    )
                entry[f"source_valid_{reviewer}"] = True
            except (OSError, ValueError) as error:
                issues.append(f"reviewer {reviewer} roster source invalid: {error}")
        entry["source_issues"] = issues
        result.append(entry)
    return result


def box_iou(left, right):
    ax1, ay1 = left["x"], left["y"]
    ax2, ay2 = ax1 + left["width"], ay1 + left["height"]
    bx1, by1 = right["x"], right["y"]
    bx2, by2 = bx1 + right["width"], by1 + right["height"]
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = iw * ih
    union = left["width"] * left["height"] + right["width"] * right["height"] - intersection
    return intersection / union if union > 0 else 0.0


def maximum_weight_assignment(weights):
    size = len(weights)
    if not size:
        return []
    max_weight = max(max(row) for row in weights)
    costs = [[max_weight - value for value in row] for row in weights]
    u, v = [0.0] * (size + 1), [0.0] * (size + 1)
    p, way = [0] * (size + 1), [0] * (size + 1)
    for row in range(1, size + 1):
        p[0] = row
        col0 = 0
        min_value = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[col0] = True
            row0 = p[col0]
            delta, col1 = float("inf"), 0
            for col in range(1, size + 1):
                if used[col]:
                    continue
                current = costs[row0 - 1][col - 1] - u[row0] - v[col]
                if current < min_value[col]:
                    min_value[col], way[col] = current, col0
                if min_value[col] < delta:
                    delta, col1 = min_value[col], col
            for col in range(size + 1):
                if used[col]:
                    u[p[col]] += delta
                    v[col] -= delta
                else:
                    min_value[col] -= delta
            col0 = col1
            if p[col0] == 0:
                break
        while True:
            col1 = way[col0]
            p[col0] = p[col1]
            col0 = col1
            if col0 == 0:
                break
    return [(p[col] - 1, col - 1) for col in range(1, size + 1) if p[col] > 0]


def match_boxes(left, right, threshold):
    if not left or not right:
        return [], list(range(len(left))), list(range(len(right)))
    size = max(len(left), len(right))
    bonus = size + 1.0
    ious = [[box_iou(left[i], right[j]) for j in range(len(right))]
            for i in range(len(left))]
    weights = []
    for row in range(size):
        weights.append([
            bonus + ious[row][col]
            if row < len(left) and col < len(right) and ious[row][col] >= threshold
            else 0.0
            for col in range(size)
        ])
    pairs, used_left, used_right = [], set(), set()
    for left_index, right_index in maximum_weight_assignment(weights):
        if (left_index < len(left) and right_index < len(right)
                and ious[left_index][right_index] >= threshold):
            pairs.append((left_index, right_index, ious[left_index][right_index]))
            used_left.add(left_index)
            used_right.add(right_index)
    return (
        pairs,
        [index for index in range(len(left)) if index not in used_left],
        [index for index in range(len(right)) if index not in used_right],
    )


def union_coverage(box, regions):
    x1, y1 = box["x"], box["y"]
    x2, y2 = x1 + box["width"], y1 + box["height"]
    clipped = []
    for region in regions:
        left = max(x1, region["x"])
        top = max(y1, region["y"])
        right = min(x2, region["x"] + region["width"])
        bottom = min(y2, region["y"] + region["height"])
        if right > left and bottom > top:
            clipped.append((left, top, right, bottom))
    xs = sorted({value for rect in clipped for value in (rect[0], rect[2])})
    covered_area = 0.0
    for left, right in zip(xs, xs[1:]):
        if right <= left:
            continue
        intervals = sorted(
            (top, bottom) for x1r, top, x2r, bottom in clipped
            if x1r < right and x2r > left
        )
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
        covered_area += (right - left) * covered_y
    area = box["width"] * box["height"]
    return covered_area / area if area else 0.0


def derived_source(annotation, record):
    """Derive head source from source metadata, regions, and effective review state."""
    class_id = annotation["class_id"]
    if class_id == 5:
        return "depicted"
    if class_id == 6:
        return "loose_physical_hat"
    if class_id == 7:
        return "surface_boundary"
    if record["scene_type"] == "depiction_only":
        return "depicted"
    if record["incomplete_issues"]:
        return "unresolved"
    regions = [
        item for item in record["annotations"]
        if item["class_id"] == 7
    ]
    center_x = annotation["x"] + annotation["width"] / 2
    center_y = annotation["y"] + annotation["height"] / 2
    center_inside = any(
        center_x >= region["x"]
        and center_x <= region["x"] + region["width"]
        and center_y >= region["y"]
        and center_y <= region["y"] + region["height"]
        for region in regions
    )
    coverage = union_coverage(annotation, regions)
    if center_inside or coverage >= 0.5:
        return "depicted"
    if coverage > 0:
        return "unresolved"
    other_scene_attested = (
        record["scene_type"] != "other"
        or record["other_scene_no_depicted_people_reviewed"]
    )
    if (record["frame_source_status"] == "clear"
            and record["scene_type"] in {"mixed_scene", "other"}
            and other_scene_attested
            and annotation["review_state"] == "confirmed"):
        return "real_scene"
    return "unresolved"


def source_tuple(record):
    physical = Counter(surface["surface_type"] for surface in record["surfaces"])
    regions = Counter(
        record["surface_by_id"][annotation["depiction_surface_id"]]
        for annotation in record["annotations"] if annotation["class_id"] == 7
    )
    return {
        "scene_type": record["scene_type"],
        "frame_source_status": record["frame_source_status"],
        "other_scene_no_depicted_people_reviewed": (
            record["other_scene_no_depicted_people_reviewed"]
            if record["scene_type"] == "other" else None
        ),
        "depiction_surface_types": record["depiction_surface_types"],
        "physical_surface_counts": {kind: physical.get(kind, 0) for kind in SURFACE_TYPES},
        "depiction_region_counts": {kind: regions.get(kind, 0) for kind in SURFACE_TYPES},
    }


def metrics(left, right, threshold):
    pairs, unmatched_a, unmatched_b = match_boxes(left, right, threshold)
    return {
        "left_count": len(left),
        "right_count": len(right),
        "matched_count": len(pairs),
        "unmatched_a_count": len(unmatched_a),
        "unmatched_b_count": len(unmatched_b),
        "pairs": pairs,
        "unmatched_a": unmatched_a,
        "unmatched_b": unmatched_b,
    }


def annotation_brief(annotation, record=None):
    if annotation is None:
        return None
    source = derived_source(annotation, record) if record is not None else annotation["source_category"]
    return {
        "class_id": annotation["class_id"],
        "class_name": annotation["class_name"],
        "box_xywh": [annotation["x"], annotation["y"], annotation["width"], annotation["height"]],
        "review_state": annotation["review_state"],
        "derived_source": source,
    }


def disagreement(sha, a, b, category, field, value_a, value_b, detail=""):
    return {
        "sha256": sha,
        "image_id_a": a["image_id"],
        "image_id_b": b["image_id"],
        "file_name_a": a["file_name"],
        "file_name_b": b["file_name"],
        "category": category,
        "field": field,
        "value_a": json.dumps(value_a, ensure_ascii=False, sort_keys=True),
        "value_b": json.dumps(value_b, ensure_ascii=False, sort_keys=True),
        "detail": detail,
    }


def box_row(sha, a, b, comparison, group, left, right, iou, status,
            source_a="", source_b="", class_agrees="", state_agrees="", source_agrees=""):
    return {
        "sha256": sha,
        "image_id_a": a["image_id"],
        "image_id_b": b["image_id"],
        "file_name_a": a["file_name"],
        "file_name_b": b["file_name"],
        "comparison": comparison,
        "group": group,
        "status": status,
        "iou": "" if iou is None else f"{iou:.8f}",
        "class_a": "" if left is None else left["class_name"],
        "class_b": "" if right is None else right["class_name"],
        "review_state_a": "" if left is None else left["review_state"],
        "review_state_b": "" if right is None else right["review_state"],
        "derived_source_a": source_a,
        "derived_source_b": source_b,
        "class_id_agrees": class_agrees,
        "review_state_agrees": state_agrees,
        "derived_source_agrees": source_agrees,
        "box_a": "" if left is None else json.dumps(annotation_brief(left), ensure_ascii=False),
        "box_b": "" if right is None else json.dumps(annotation_brief(right), ensure_ascii=False),
    }


def strip_detail(value):
    return {key: item for key, item in value.items()
            if key not in {"pairs", "unmatched_a", "unmatched_b"}}


def compare_image(a, b, threshold, source_agreement_allowed=True):
    sha = a["sha256"]
    source_a, source_b = source_tuple(a), source_tuple(b)
    mismatches = [field for field in source_a if source_a[field] != source_b[field]]
    disagreements, box_rows = [], []
    for field in mismatches:
        disagreements.append(disagreement(
            sha, a, b, "source_metadata", field, source_a[field], source_b[field]
        ))

    regions_by_type = {}
    for kind in SURFACE_TYPES:
        left = [
            item for item in a["annotations"] if item["class_id"] == 7
            and a["surface_by_id"][item["depiction_surface_id"]] == kind
        ]
        right = [
            item for item in b["annotations"] if item["class_id"] == 7
            and b["surface_by_id"][item["depiction_surface_id"]] == kind
        ]
        item_metrics = metrics(left, right, threshold)
        regions_by_type[kind] = item_metrics
        for ia, ib, iou in item_metrics["pairs"]:
            box_rows.append(box_row(sha, a, b, "depiction_region", kind, left[ia], right[ib], iou, "matched"))
        for side, items in (("a", item_metrics["unmatched_a"]), ("b", item_metrics["unmatched_b"])):
            group = left if side == "a" else right
            for index in items:
                item = group[index]
                left_item, right_item = (item, None) if side == "a" else (None, item)
                box_rows.append(box_row(
                    sha, a, b, "depiction_region", kind, left_item, right_item, None, f"unmatched_{side}"
                ))
                disagreements.append(disagreement(
                    sha, a, b, "depiction_region_box", kind,
                    annotation_brief(left_item), annotation_brief(right_item),
                    f"unmatched reviewer {side.upper()} region box",
                ))

    class_metrics = {}
    for class_id in OBJECT_CLASS_IDS:
        name = CLASS_NAMES[class_id]
        left = [item for item in a["annotations"] if item["class_id"] == class_id]
        right = [item for item in b["annotations"] if item["class_id"] == class_id]
        item_metrics = metrics(left, right, threshold)
        class_metrics[name] = item_metrics
        for ia, ib, iou in item_metrics["pairs"]:
            box_rows.append(box_row(sha, a, b, "review_class", name, left[ia], right[ib], iou, "matched"))
        for side, items in (("a", item_metrics["unmatched_a"]), ("b", item_metrics["unmatched_b"])):
            group = left if side == "a" else right
            for index in items:
                item = group[index]
                left_item, right_item = (item, None) if side == "a" else (None, item)
                box_rows.append(box_row(
                    sha, a, b, "review_class", name, left_item, right_item, None, f"unmatched_{side}"
                ))
                disagreements.append(disagreement(
                    sha, a, b, "review_class_box", name,
                    annotation_brief(left_item), annotation_brief(right_item),
                    f"unmatched reviewer {side.upper()} box",
                ))

    object_a = [item for item in a["annotations"] if item["class_id"] in OBJECT_CLASS_IDS]
    object_b = [item for item in b["annotations"] if item["class_id"] in OBJECT_CLASS_IDS]
    object_metrics = metrics(object_a, object_b, threshold)
    object_denominator = (
        object_metrics["matched_count"]
        + object_metrics["unmatched_a_count"]
        + object_metrics["unmatched_b_count"]
    )
    head_sources_a = Counter(
        derived_source(item, a) for item in object_a if item["class_id"] <= 4
    )
    head_sources_b = Counter(
        derived_source(item, b) for item in object_b if item["class_id"] <= 4
    )
    object_agreement = {
        "reviewer_a_object_box_count": object_metrics["left_count"],
        "reviewer_b_object_box_count": object_metrics["right_count"],
        "matched_spatial_object_count": object_metrics["matched_count"],
        "unmatched_a_count": object_metrics["unmatched_a_count"],
        "unmatched_b_count": object_metrics["unmatched_b_count"],
        "object_box_agreement_denominator": object_denominator,
        "derived_head_source_denominator": 0,
        "derived_head_source_agreement_count": 0,
        "derived_head_source_unresolved_pair_count": 0,
        "derived_head_source_resolved_mismatch_count": 0,
        "incomplete_source_pair_count": 0,
        "head_vs_nonhead_class_boundary_pair_count": 0,
        "unmatched_head_box_count": 0,
        "unmatched_unresolved_head_box_count": 0,
        "reviewer_a_head_source_counts": {
            key: head_sources_a.get(key, 0) for key in ("real_scene", "depicted", "unresolved")
        },
        "reviewer_b_head_source_counts": {
            key: head_sources_b.get(key, 0) for key in ("real_scene", "depicted", "unresolved")
        },
        "reviewer_a_zero_object_boxes": not object_a,
        "reviewer_b_zero_object_boxes": not object_b,
        "reviewer_a_zero_head_boxes": not head_sources_a,
        "reviewer_b_zero_head_boxes": not head_sources_b,
        "class_id_agreement_count": 0,
        "raw_review_state_agreement_count": 0,
    }
    for ia, ib, iou in object_metrics["pairs"]:
        left, right = object_a[ia], object_b[ib]
        left_source, right_source = derived_source(left, a), derived_source(right, b)
        left_is_head, right_is_head = left["class_id"] <= 4, right["class_id"] <= 4
        source_pair = left_is_head or right_is_head
        source_agrees = (
            source_agreement_allowed
            and left_is_head and right_is_head
            and left_source != "unresolved"
            and right_source != "unresolved"
            and left_source == right_source
        )
        class_agrees = left["class_id"] == right["class_id"]
        state_agrees = left["review_state"] == right["review_state"]
        if source_pair:
            object_agreement["derived_head_source_denominator"] += 1
            object_agreement["derived_head_source_agreement_count"] += int(source_agrees)
            object_agreement["incomplete_source_pair_count"] += int(
                not source_agreement_allowed
            )
            if left_is_head != right_is_head:
                object_agreement["head_vs_nonhead_class_boundary_pair_count"] += 1
            elif not source_agreement_allowed:
                pass
            elif left_source == "unresolved" or right_source == "unresolved":
                object_agreement["derived_head_source_unresolved_pair_count"] += 1
            elif left_source != right_source:
                object_agreement["derived_head_source_resolved_mismatch_count"] += 1
        object_agreement["class_id_agreement_count"] += int(class_agrees)
        object_agreement["raw_review_state_agreement_count"] += int(state_agrees)
        box_rows.append(box_row(
            sha, a, b, "object_source_spatial", "class_ids_0_to_6", left, right, iou,
            "matched", left_source, right_source, class_agrees, state_agrees, source_agrees,
        ))
        if source_pair and not source_agrees:
            category = (
                "head_vs_nonhead_class_boundary"
                if left_is_head != right_is_head
                else "source_incomplete_review"
                if not source_agreement_allowed
                else "head_source_unresolved"
                if left_source == "unresolved" or right_source == "unresolved"
                else "object_source_category"
            )
            disagreements.append(disagreement(
                sha, a, b, category, f"box_pair_{ia}_{ib}",
                left_source, right_source, f"spatially matched at IoU {iou:.6f}",
            ))
        if not class_agrees:
            disagreements.append(disagreement(
                sha, a, b, "object_class_id", f"box_pair_{ia}_{ib}",
                left["class_name"], right["class_name"], f"spatially matched at IoU {iou:.6f}",
            ))
        if not state_agrees:
            disagreements.append(disagreement(
                sha, a, b, "object_review_state", f"box_pair_{ia}_{ib}",
                left["review_state"], right["review_state"], f"spatially matched at IoU {iou:.6f}",
            ))
    for side, items in (("a", object_metrics["unmatched_a"]), ("b", object_metrics["unmatched_b"])):
        group = object_a if side == "a" else object_b
        record = a if side == "a" else b
        for index in items:
            item = group[index]
            left_item, right_item = (item, None) if side == "a" else (None, item)
            is_head = item["class_id"] <= 4
            item_source = derived_source(item, record)
            if is_head:
                object_agreement["derived_head_source_denominator"] += 1
                object_agreement["unmatched_head_box_count"] += 1
                object_agreement["unmatched_unresolved_head_box_count"] += int(
                    item_source == "unresolved"
                )
            box_rows.append(box_row(
                sha, a, b, "object_source_spatial", "class_ids_0_to_6",
                left_item, right_item, None, f"unmatched_{side}",
                item_source, "", "", "", "",
            ))
            disagreements.append(disagreement(
                sha, a, b, "object_box_unmatched", f"reviewer_{side}_box_{index}",
                annotation_brief(left_item, a if side == "a" else None),
                annotation_brief(right_item, b if side == "b" else None),
                f"unmatched reviewer {side.upper()} object box",
            ))
    object_agreement["class_id_agreement_fraction"] = (
        object_agreement["class_id_agreement_count"] / object_denominator
        if object_denominator else None
    )
    object_agreement["raw_review_state_agreement_fraction"] = (
        object_agreement["raw_review_state_agreement_count"] / object_denominator
        if object_denominator else None
    )
    source_denominator = object_agreement["derived_head_source_denominator"]
    object_agreement["derived_head_source_agreement_fraction"] = (
        object_agreement["derived_head_source_agreement_count"] / source_denominator
        if source_denominator else None
    )

    row = {
        "sha256": sha,
        "image_id_a": a["image_id"],
        "image_id_b": b["image_id"],
        "file_name_a": a["file_name"],
        "file_name_b": b["file_name"],
        "dimensions": f"{a['width']}x{a['height']}",
        "source_metadata_exact_agreement": not mismatches,
        "source_metadata_mismatch_fields": mismatches,
        "source_metadata_a": source_a,
        "source_metadata_b": source_b,
        "depiction_region_geometry": {
            kind: strip_detail(value) for kind, value in regions_by_type.items()
        },
        "class_box_agreement": {
            name: strip_detail(value) for name, value in class_metrics.items()
        },
        "object_source_agreement": object_agreement,
        "disagreement_count": len(disagreements),
    }
    return row, disagreements, box_rows, regions_by_type, class_metrics, object_agreement


def score_metrics(total_a, total_b, matched):
    precision = matched / total_a if total_a else None
    recall = matched / total_b if total_b else None
    f1 = 2 * matched / (total_a + total_b) if total_a + total_b else None
    return {
        "reviewer_a_box_count": total_a,
        "reviewer_b_box_count": total_b,
        "matched_box_count": matched,
        "unmatched_a_box_count": total_a - matched,
        "unmatched_b_box_count": total_b - matched,
        "both_reviewers_zero_box_images_are_unscored": total_a == 0 and total_b == 0,
        "precision_a_to_b": precision,
        "recall_b_from_a": recall,
        "f1": f1,
    }


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def resolve_review_record(entry, reviewer, records, invalid, by_sha):
    file_field = "file_name_a" if reviewer == "a" else "file_name_b"
    expected_name = entry[file_field].casefold()
    candidates = by_sha.get(entry["sha256"], [])
    if len(candidates) > 1:
        return "ambiguous", None
    if len(candidates) == 1:
        record = candidates[0]
        if record["issues"]:
            return "invalid", record
        if (record["width"], record["height"]) != (entry["width"], entry["height"]):
            return "invalid", record
        return ("incomplete" if record["incomplete_issues"] else "present"), record
    named_records = [
        record for record in records
        if record["file_name"].casefold() == expected_name
    ]
    named_invalid = [
        record for record in invalid
        if isinstance(record.get("file_name"), str)
        and record["file_name"].casefold() == expected_name
    ]
    if len(named_records) > 1 or len(named_invalid) > 1:
        return "ambiguous", None
    if named_records or named_invalid:
        return "invalid", named_records[0] if named_records else None
    return "omitted", None


def empty_roster_record(entry, reviewer):
    filename = entry["file_name_a" if reviewer == "a" else "file_name_b"]
    return {
        "image_id": "",
        "file_name": filename,
        "width": entry["width"],
        "height": entry["height"],
        "image_review_status": None,
        "sha256": entry["sha256"],
        "scene_type": None,
        "frame_source_status": None,
        "other_scene_no_depicted_people_reviewed": None,
        "depiction_surface_types": [],
        "surfaces": [],
        "surface_by_id": {},
        "annotations": [],
        "incomplete_issues": ["review missing or invalid"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--review-a", required=True, type=Path)
    parser.add_argument("--images-a", required=True, type=Path)
    parser.add_argument("--reviewer-a", required=True)
    parser.add_argument("--review-b", required=True, type=Path)
    parser.add_argument("--images-b", required=True, type=Path)
    parser.add_argument("--reviewer-b", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    args = parser.parse_args(argv)
    reviewer_a, reviewer_b = args.reviewer_a.strip(), args.reviewer_b.strip()
    if not reviewer_a or not reviewer_b or reviewer_a == reviewer_b:
        parser.error("reviewer IDs must be non-empty and distinct")
    if not math.isfinite(args.iou_threshold) or not 0 < args.iou_threshold <= 1:
        parser.error("--iou-threshold must be greater than 0 and at most 1")
    if args.output_dir.exists():
        parser.error(f"output directory already exists; refusing to overwrite: {args.output_dir}")

    try:
        roster = read_roster(args.roster)
        records_a, invalid_a = load_review(args.review_a, reviewer_a)
        records_b, invalid_b = load_review(args.review_b, reviewer_b)
        inspect_source_images(records_a, args.images_a, reviewer_a)
        inspect_source_images(records_b, args.images_b, reviewer_b)
        inspect_roster_sources(roster, args.images_a, args.images_b)
    except ComparisonError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    diagnostics = []
    for reviewer, invalid in ((reviewer_a, invalid_a), (reviewer_b, invalid_b)):
        for item in invalid:
            diagnostics.append({
                "reviewer": reviewer,
                "image_id": item.get("image_id"),
                "file_name": item.get("file_name"),
                "sha256": "",
                "issue_type": "invalid_review_record",
                "issue": item["issue"],
            })
    for reviewer, records in ((reviewer_a, records_a), (reviewer_b, records_b)):
        for record in records:
            for issue in record["issues"]:
                diagnostics.append({
                    "reviewer": reviewer,
                    "image_id": record["image_id"],
                    "file_name": record["file_name"],
                    "sha256": record["sha256"] or "",
                    "issue_type": "invalid_or_unusable_review_image",
                    "issue": issue,
                })
            for issue in record["incomplete_issues"]:
                diagnostics.append({
                    "reviewer": reviewer,
                    "image_id": record["image_id"],
                    "file_name": record["file_name"],
                    "sha256": record["sha256"] or "",
                    "issue_type": "incomplete_source_review",
                    "issue": issue,
                })
    for entry in roster:
        if entry["source_issues"]:
            diagnostics.append({
                "reviewer": "both",
                "image_id": "",
                "file_name": f"{entry['file_name_a']} | {entry['file_name_b']}",
                "sha256": entry["sha256"],
                "issue_type": "invalid_predeclared_roster_source",
                "issue": "; ".join(entry["source_issues"]),
            })

    def index_by_sha(records):
        result = {}
        for record in records:
            if record["sha256"]:
                result.setdefault(record["sha256"], []).append(record)
        return result

    by_sha_a, by_sha_b = index_by_sha(records_a), index_by_sha(records_b)
    roster_hashes = {entry["sha256"] for entry in roster}
    duplicate_shas = {
        sha for index in (by_sha_a, by_sha_b)
        for sha, values in index.items() if len(values) > 1
    }
    for sha in sorted(duplicate_shas):
        for reviewer, index in ((reviewer_a, by_sha_a), (reviewer_b, by_sha_b)):
            for record in index.get(sha, []):
                diagnostics.append({
                    "reviewer": reviewer,
                    "image_id": record["image_id"],
                    "file_name": record["file_name"],
                    "sha256": sha,
                    "issue_type": "duplicate_review_image_sha256",
                    "issue": "same source bytes appear more than once in this reviewer export",
                })
    for reviewer, index in ((reviewer_a, by_sha_a), (reviewer_b, by_sha_b)):
        for sha in sorted(set(index) - roster_hashes):
            for record in index[sha]:
                diagnostics.append({
                    "reviewer": reviewer,
                    "image_id": record["image_id"],
                    "file_name": record["file_name"],
                    "sha256": sha,
                    "issue_type": "image_not_in_predeclared_roster",
                    "issue": "review export contains an image absent from the shared roster",
                })

    image_rows, disagreement_rows, box_rows = [], [], []
    region_totals = {kind: [0, 0, 0] for kind in SURFACE_TYPES}
    region_zero_counts = {kind: [0, 0] for kind in SURFACE_TYPES}
    class_totals = {name: [0, 0, 0] for name in CLASS_NAMES[:7]}
    class_zero_counts = {name: [0, 0] for name in CLASS_NAMES[:7]}
    object_totals = Counter()
    head_source_counts = {"a": Counter(), "b": Counter()}
    zero_object_images = Counter()
    zero_head_images = Counter()
    zero_annotation_images = Counter()
    both_zero_object_images = 0
    source_status_pairs = Counter()
    review_presence_pairs = Counter()
    image_review_status_pairs = Counter()
    image_review_status_counts = {"a": Counter(), "b": Counter()}
    image_review_status_comparable_count = 0
    image_review_status_incomplete_count = 0
    image_review_status_agreement_count = 0
    image_review_status_disagreement_count = 0
    both_reviewed_empty_count = 0
    both_reviewed_with_labels_count = 0
    both_empty_annotation_reviewed_empty_count = 0
    box_comparable_count = 0
    partial_box_metrics_count = 0
    metadata_comparable_count = 0
    excluded_invalid_object_boxes = Counter()
    for entry in roster:
        status_a, record_a = resolve_review_record(
            entry, "a", records_a, invalid_a, by_sha_a
        )
        status_b, record_b = resolve_review_record(
            entry, "b", records_b, invalid_b, by_sha_b
        )
        review_presence_pairs[f"{status_a}/{status_b}"] += 1
        source_status_pairs[
            f"{record_a['frame_source_status'] if record_a else status_a}/"
            f"{record_b['frame_source_status'] if record_b else status_b}"
        ] += 1
        source_files_verified = entry["source_valid_a"] and entry["source_valid_b"]
        for reviewer, status, record in (
            (reviewer_a, status_a, record_a), (reviewer_b, status_b, record_b)
        ):
            if status in {"omitted", "invalid", "ambiguous"}:
                diagnostics.append({
                    "reviewer": reviewer,
                    "image_id": "" if record is None else record["image_id"],
                    "file_name": entry["file_name_a" if reviewer == reviewer_a else "file_name_b"],
                    "sha256": entry["sha256"],
                    "issue_type": f"review_{status}",
                    "issue": f"predeclared roster image is {status} in reviewer export",
                })

        record_valid_a = (
            status_a in {"present", "incomplete"}
            and record_a is not None and not record_a["issues"]
        )
        record_valid_b = (
            status_b in {"present", "incomplete"}
            and record_b is not None and not record_b["issues"]
        )
        source_usable_a = entry["source_valid_a"] and record_valid_a
        source_usable_b = entry["source_valid_b"] and record_valid_b
        image_review_status_a = (
            record_a["image_review_status"]
            if source_usable_a and record_a["image_review_status"] in IMAGE_REVIEW_STATUSES
            else None
        )
        image_review_status_b = (
            record_b["image_review_status"]
            if source_usable_b and record_b["image_review_status"] in IMAGE_REVIEW_STATUSES
            else None
        )
        image_review_status_comparable = (
            image_review_status_a is not None and image_review_status_b is not None
        )
        image_review_status_agrees = (
            image_review_status_comparable
            and image_review_status_a == image_review_status_b
        )
        image_review_status_pairs[
            f"{image_review_status_a or 'incomplete'}/{image_review_status_b or 'incomplete'}"
        ] += 1
        if image_review_status_a is not None:
            image_review_status_counts["a"][image_review_status_a] += 1
        if image_review_status_b is not None:
            image_review_status_counts["b"][image_review_status_b] += 1
        if image_review_status_a is None or image_review_status_b is None:
            image_review_status_incomplete_count += 1
        else:
            image_review_status_comparable_count += 1
            if image_review_status_agrees:
                image_review_status_agreement_count += 1
                both_reviewed_empty_count += int(image_review_status_a == "reviewed_empty")
                both_reviewed_with_labels_count += int(
                    image_review_status_a == "reviewed_with_labels"
                )
                both_empty_annotation_reviewed_empty_count += int(
                    image_review_status_a == "reviewed_empty"
                    and not record_a["annotations"] and not record_b["annotations"]
                )
            else:
                image_review_status_disagreement_count += 1
        box_comparable = source_usable_a and source_usable_b
        if record_a is not None and not source_usable_a:
            excluded_invalid_object_boxes["a"] += sum(
                item["class_id"] in OBJECT_CLASS_IDS for item in record_a["annotations"]
            )
        if record_b is not None and not source_usable_b:
            excluded_invalid_object_boxes["b"] += sum(
                item["class_id"] in OBJECT_CLASS_IDS for item in record_b["annotations"]
            )
        partial_box_metrics = source_usable_a != source_usable_b
        metadata_comparable = (
            box_comparable
            and not record_a["incomplete_issues"]
            and not record_b["incomplete_issues"]
        )
        if box_comparable or partial_box_metrics:
            metric_a = record_a if source_usable_a else empty_roster_record(entry, "a")
            metric_b = record_b if source_usable_b else empty_roster_record(entry, "b")
            row, disagreements, boxes, regions, classes, objects = compare_image(
                metric_a, metric_b, args.iou_threshold,
                source_agreement_allowed=metadata_comparable,
            )
            if box_comparable:
                box_comparable_count += 1
            else:
                partial_box_metrics_count += 1
            if metadata_comparable:
                metadata_comparable_count += 1
            else:
                incomplete_sides = []
                if status_a not in {"present", "incomplete"} or (
                    record_a and record_a["incomplete_issues"]
                ):
                    incomplete_sides.append("a")
                if status_b not in {"present", "incomplete"} or (
                    record_b and record_b["incomplete_issues"]
                ):
                    incomplete_sides.append("b")
                row["source_metadata_mismatch_fields"].extend(
                    f"incomplete_review_{side}" for side in incomplete_sides
                )
                row["source_metadata_exact_agreement"] = False
                for side, record, valid_side in (
                    ("a", record_a, source_usable_a),
                    ("b", record_b, source_usable_b),
                ):
                    if not entry[f"source_valid_{side}"]:
                        disagreements.append(disagreement(
                            entry["sha256"], metric_a, metric_b,
                            "roster_source_file", f"source_file_{side}_verified",
                            False, True, "; ".join(entry["source_issues"]),
                        ))
                    if not valid_side:
                        disagreements.append(disagreement(
                            entry["sha256"], metric_a, metric_b,
                            "review_presence_or_validity", f"reviewer_{side}",
                            status_a if side == "a" else status_b, "present and source-verified",
                        ))
                    elif record["incomplete_issues"]:
                        disagreements.append(disagreement(
                            entry["sha256"], metric_a, metric_b,
                            "source_metadata_incomplete", f"reviewer_{side}",
                            None, record["incomplete_issues"],
                        ))
            row.update({
                "roster_index": entry["roster_index"],
                "review_status_a": status_a,
                "review_status_b": status_b,
                "source_files_verified": source_files_verified,
                "source_file_a_verified": entry["source_valid_a"],
                "source_file_b_verified": entry["source_valid_b"],
                "box_comparable": box_comparable,
                "partial_box_metrics": partial_box_metrics,
                "source_metadata_comparable": metadata_comparable,
                "clear_status_metadata_agreement": (
                    box_comparable
                    and
                    metadata_comparable
                    and row["source_metadata_exact_agreement"]
                    and metric_a["frame_source_status"] == "clear"
                    and metric_b["frame_source_status"] == "clear"
                ),
            })
            for kind, value in regions.items():
                region_totals[kind][0] += value["left_count"]
                region_totals[kind][1] += value["right_count"]
                region_totals[kind][2] += value["matched_count"]
                region_zero_counts[kind][0] += int(
                    source_usable_a and value["left_count"] == 0
                )
                region_zero_counts[kind][1] += int(
                    source_usable_b and value["right_count"] == 0
                )
            for name, value in classes.items():
                class_totals[name][0] += value["left_count"]
                class_totals[name][1] += value["right_count"]
                class_totals[name][2] += value["matched_count"]
                class_zero_counts[name][0] += int(
                    source_usable_a and value["left_count"] == 0
                )
                class_zero_counts[name][1] += int(
                    source_usable_b and value["right_count"] == 0
                )
            object_totals.update({
                key: value for key, value in objects.items() if is_int(value)
            })
            if source_usable_a:
                for key, value in objects["reviewer_a_head_source_counts"].items():
                    head_source_counts["a"][key] += value
                zero_object_images["a"] += int(objects["reviewer_a_zero_object_boxes"])
                zero_head_images["a"] += int(objects["reviewer_a_zero_head_boxes"])
                zero_annotation_images["a"] += int(not metric_a["annotations"])
            if source_usable_b:
                for key, value in objects["reviewer_b_head_source_counts"].items():
                    head_source_counts["b"][key] += value
                zero_object_images["b"] += int(objects["reviewer_b_zero_object_boxes"])
                zero_head_images["b"] += int(objects["reviewer_b_zero_head_boxes"])
                zero_annotation_images["b"] += int(not metric_b["annotations"])
            both_zero_object_images += int(
                source_usable_a and source_usable_b
                and objects["reviewer_a_zero_object_boxes"]
                and objects["reviewer_b_zero_object_boxes"]
            )
            disagreement_rows.extend(disagreements)
            box_rows.extend(boxes)
            image_disagreement_count = len(disagreements)
        else:
            tuple_a = source_tuple(record_a) if record_a is not None else None
            tuple_b = source_tuple(record_b) if record_b is not None else None
            row = {
                "sha256": entry["sha256"],
                "roster_index": entry["roster_index"],
                "image_id_a": "" if record_a is None else record_a["image_id"],
                "image_id_b": "" if record_b is None else record_b["image_id"],
                "file_name_a": entry["file_name_a"],
                "file_name_b": entry["file_name_b"],
                "dimensions": f"{entry['width']}x{entry['height']}",
                "review_status_a": status_a,
                "review_status_b": status_b,
                "source_files_verified": source_files_verified,
                "source_file_a_verified": entry["source_valid_a"],
                "source_file_b_verified": entry["source_valid_b"],
                "box_comparable": False,
                "partial_box_metrics": False,
                "source_metadata_comparable": False,
                "source_metadata_exact_agreement": False,
                "clear_status_metadata_agreement": False,
                "source_metadata_mismatch_fields": ["missing_or_invalid_review_or_source"],
                "source_metadata_a": tuple_a,
                "source_metadata_b": tuple_b,
                "depiction_region_geometry": None,
                "class_box_agreement": None,
                "object_source_agreement": None,
            }
            image_disagreement_count = 0
            for reviewer, status in ((reviewer_a, status_a), (reviewer_b, status_b)):
                if status not in {"present", "incomplete"}:
                    item = disagreement(
                        entry["sha256"],
                        record_a or {"image_id": "", "file_name": entry["file_name_a"]},
                        record_b or {"image_id": "", "file_name": entry["file_name_b"]},
                        "review_presence_or_validity", reviewer, status, "present",
                        "predeclared roster image is absent, invalid, or ambiguous",
                    )
                    disagreement_rows.append(item)
                    image_disagreement_count += 1
            if not source_files_verified:
                item = disagreement(
                    entry["sha256"],
                    record_a or {"image_id": "", "file_name": entry["file_name_a"]},
                    record_b or {"image_id": "", "file_name": entry["file_name_b"]},
                    "roster_source_file", "source_files_verified",
                    entry["source_valid_a"], entry["source_valid_b"],
                    "; ".join(entry["source_issues"]),
                )
                disagreement_rows.append(item)
                image_disagreement_count += 1
        row.update({
            "image_review_status_a": (
                None if record_a is None else record_a.get("image_review_status")
            ),
            "image_review_status_b": (
                None if record_b is None else record_b.get("image_review_status")
            ),
            "image_review_status_available_a": image_review_status_a is not None,
            "image_review_status_available_b": image_review_status_b is not None,
            "image_review_status_pair": (
                f"{image_review_status_a or 'incomplete'}/"
                f"{image_review_status_b or 'incomplete'}"
            ),
            "image_review_status_comparable": image_review_status_comparable,
            "image_review_status_agrees": image_review_status_agrees,
            "image_review_status_incomplete": not image_review_status_comparable,
        })
        status_disagreements = []
        left_for_disagreement = record_a or {
            "image_id": "", "file_name": entry["file_name_a"]
        }
        right_for_disagreement = record_b or {
            "image_id": "", "file_name": entry["file_name_b"]
        }
        if not image_review_status_comparable:
            for side, value, available in (
                ("a", row["image_review_status_a"], image_review_status_a is not None),
                ("b", row["image_review_status_b"], image_review_status_b is not None),
            ):
                if not available:
                    status_disagreements.append(disagreement(
                        entry["sha256"], left_for_disagreement, right_for_disagreement,
                        "image_review_status_incomplete", f"reviewer_{side}", value,
                        "verified terminal v7 image status",
                        "roster image is missing, invalid, ambiguous, or has an unverifiable source file",
                    ))
        elif not image_review_status_agrees:
            status_disagreements.append(disagreement(
                entry["sha256"], left_for_disagreement, right_for_disagreement,
                "image_review_status", "image_review_status",
                image_review_status_a, image_review_status_b,
                "both terminal statuses are available but differ",
            ))
        disagreement_rows.extend(status_disagreements)
        image_disagreement_count += len(status_disagreements)
        row["reviewer_a_annotation_count"] = None if record_a is None else len(record_a["annotations"])
        row["reviewer_b_annotation_count"] = None if record_b is None else len(record_b["annotations"])
        row["excluded_invalid_object_box_count_a"] = (
            None if record_a is None and status_a in {"invalid", "ambiguous"}
            else 0 if record_a is None or source_usable_a
            else sum(item["class_id"] in OBJECT_CLASS_IDS for item in record_a["annotations"])
        )
        row["excluded_invalid_object_box_count_b"] = (
            None if record_b is None and status_b in {"invalid", "ambiguous"}
            else 0 if record_b is None or source_usable_b
            else sum(item["class_id"] in OBJECT_CLASS_IDS for item in record_b["annotations"])
        )
        row["zero_object_boxes_a"] = (
            None if not source_usable_a else not any(
                item["class_id"] in OBJECT_CLASS_IDS for item in record_a["annotations"]
            )
        )
        row["zero_object_boxes_b"] = (
            None if not source_usable_b else not any(
                item["class_id"] in OBJECT_CLASS_IDS for item in record_b["annotations"]
            )
        )
        row["zero_head_boxes_a"] = (
            None if not source_usable_a else not any(
                item["class_id"] <= 4 for item in record_a["annotations"]
            )
        )
        row["zero_head_boxes_b"] = (
            None if not source_usable_b else not any(
                item["class_id"] <= 4 for item in record_b["annotations"]
            )
        )
        row["disagreement_count"] = image_disagreement_count
        image_rows.append(row)

    set_a, set_b = set(by_sha_a), set(by_sha_b)
    roster_hashes = {entry["sha256"] for entry in roster}
    all_roster_match = (
        not diagnostics
        and box_comparable_count == len(roster)
        and metadata_comparable_count == len(roster)
        and image_review_status_comparable_count == len(roster)
        and set_a == roster_hashes
        and set_b == roster_hashes
    )
    output = args.output_dir
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"error: output directory already exists; refusing to overwrite: {output}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"error: cannot create output directory {output}: {error}", file=sys.stderr)
        return 2

    source_agreement_count = sum(row["source_metadata_exact_agreement"] for row in image_rows)
    clear_status_metadata_agreement_count = sum(
        row["clear_status_metadata_agreement"] for row in image_rows
    )
    unresolved_source_metadata_count = sum(
        not row["clear_status_metadata_agreement"] for row in image_rows
    )
    object_denominator = object_totals["object_box_agreement_denominator"]
    source_denominator = object_totals["derived_head_source_denominator"]
    source_numerator = object_totals["derived_head_source_agreement_count"]
    summary = {
        "format": "two-review-v7-descriptive-comparison-v1",
        "review_format": REVIEW_FORMAT,
        "reviewers": {"a": reviewer_a, "b": reviewer_b},
        "roster": args.roster.name,
        "roster_sha256": sha256_file(args.roster),
        "review_json_sha256": {
            "a": sha256_file(args.review_a),
            "b": sha256_file(args.review_b),
        },
        "iou_threshold": args.iou_threshold,
        "box_matching_policy": (
            "Maximum-cardinality eligible pairing first, then maximum total IoU; "
            "ties are deterministic by annotation array order."
        ),
        "status": "descriptive_only",
        "human_adjudication_required": True,
        "automated_95_percent_pass": False,
        "notice": (
            "All metrics are descriptive. They do not adjudicate disagreements, approve rights, "
            "establish provenance, or grant release. Human adjudication remains required; no "
            "95% pass decision is computed. Empty/empty boxes are unscored and do not prove "
            "that the reviewers found every instance."
        ),
        "rights_handling": "Rights declarations are not compared as proof and are not interpreted as approval.",
        "administrative_fields_not_in_source_tuple": ["rights", "group_id", "split"],
        "integrity": {
            "predeclared_roster_image_count": len(roster),
            "reviewer_a_image_rows": len(records_a) + len(invalid_a),
            "reviewer_b_image_rows": len(records_b) + len(invalid_b),
            "box_comparable_roster_images": box_comparable_count,
            "partial_box_metrics_count": partial_box_metrics_count,
            "partial_box_metrics_roster_images": partial_box_metrics_count,
            "box_metrics_available_roster_images": box_comparable_count + partial_box_metrics_count,
            "excluded_invalid_object_boxes": dict(excluded_invalid_object_boxes),
            "source_metadata_comparable_roster_images": metadata_comparable_count,
            "image_review_status_comparable_roster_images": image_review_status_comparable_count,
            "image_review_status_incomplete_roster_images": image_review_status_incomplete_count,
            "image_review_status_agreement_count": image_review_status_agreement_count,
            "image_review_status_disagreement_count": image_review_status_disagreement_count,
            "reviewer_a_roster_hash_set_equal": set(by_sha_a) == roster_hashes,
            "reviewer_b_roster_hash_set_equal": set(by_sha_b) == roster_hashes,
            "unmatched_review_sha256_a": sorted(set_a - roster_hashes),
            "unmatched_review_sha256_b": sorted(set_b - roster_hashes),
            "roster_sha256_missing_from_a": sorted(roster_hashes - set_a),
            "roster_sha256_missing_from_b": sorted(roster_hashes - set_b),
            "diagnostic_count": len(diagnostics),
            "comparison_exit_status": 0 if all_roster_match else 2,
        },
        "source_metadata_exact_agreement": {
            "metric": "exact metadata/status tuple agreement over every predeclared roster image",
            "exact_match_count": source_agreement_count,
            "denominator": len(roster),
            "fraction_over_roster": source_agreement_count / len(roster) if roster else None,
            "comparable_count": metadata_comparable_count,
            "fraction_among_comparable": (
                source_agreement_count / metadata_comparable_count
                if metadata_comparable_count else None
            ),
            "missing_invalid_or_incomplete_images_are_non_agreements": True,
            "fields": [
                "scene_type",
                "frame_source_status",
                "other_scene_no_depicted_people_reviewed (conditional for scene_type=other)",
                "depiction_surface_types",
                "physical inventory counts by surface_type",
                "depiction_region box counts by surface_type",
            ],
        },
        "clear_status_metadata_agreement": {
            "metric": "exact source metadata tuple, complete rows, and clear frame-source status on both sides",
            "matched_count": clear_status_metadata_agreement_count,
            "denominator": len(roster),
            "fraction_over_roster": (
                clear_status_metadata_agreement_count / len(roster) if roster else None
            ),
            "unresolved_or_incomplete_image_count": unresolved_source_metadata_count,
            "review_required_images_are_not_resolved_source_agreements": True,
            "this_is_not_object_box_source_agreement": True,
        },
        "frame_source_status_pairs": dict(source_status_pairs),
        "both_reviewers_review_required_status_pair_count": source_status_pairs[
            "review_required/review_required"
        ],
        "review_presence_status_pairs": dict(review_presence_pairs),
        "image_review_status": {
            "metric": (
                "descriptive terminal per-image review-status agreement over the full predeclared "
                "roster; status does not prove annotation completeness or establish a 95% pass"
            ),
            "denominator": len(roster),
            "comparable_count_both_reviewers_have_verified_terminal_status": (
                image_review_status_comparable_count
            ),
            "incomplete_count_missing_invalid_ambiguous_or_unverified_status": (
                image_review_status_incomplete_count
            ),
            "agreement_count": image_review_status_agreement_count,
            "disagreement_count": image_review_status_disagreement_count,
            "agreement_fraction_over_full_roster": (
                image_review_status_agreement_count / len(roster) if roster else None
            ),
            "status_pairs_over_full_roster": dict(image_review_status_pairs),
            "status_counts_by_reviewer": {
                reviewer: dict(counts)
                for reviewer, counts in image_review_status_counts.items()
            },
            "both_reviewers_reviewed_empty_count": both_reviewed_empty_count,
            "both_reviewers_reviewed_with_labels_count": both_reviewed_with_labels_count,
            "both_reviewed_empty_with_zero_annotations_count": (
                both_empty_annotation_reviewed_empty_count
            ),
            "status_agreement_is_descriptive_only": True,
            "automated_95_percent_pass": False,
            "empty_empty_images_remain_in_denominator": True,
        },
        "depiction_region_geometry": {
            "metric": "IoU matching by physical surface_type; counts include unmatched boxes",
            "by_surface_type": {
                kind: {
                    **score_metrics(*region_totals[kind]),
                    "reviewer_a_zero_box_image_count": region_zero_counts[kind][0],
                    "reviewer_b_zero_box_image_count": region_zero_counts[kind][1],
                }
                for kind in SURFACE_TYPES
            },
        },
        "review_class_boxes": {
            "metric": "IoU matching within review class ID 0 through 6; ID 7 regions are separate",
            "by_class": {
                name: {
                    **score_metrics(*class_totals[name]),
                    "reviewer_a_zero_box_image_count": class_zero_counts[name][0],
                    "reviewer_b_zero_box_image_count": class_zero_counts[name][1],
                }
                for name in CLASS_NAMES[:7]
            },
        },
        "object_class_and_review_state": {
            "metric": "cross-class spatial IoU matching for object classes 0 through 6",
            "matched_spatial_object_pair_count": object_totals["matched_spatial_object_count"],
            "unmatched_object_box_count_a": object_totals["unmatched_a_count"],
            "unmatched_object_box_count_b": object_totals["unmatched_b_count"],
            "denominator": object_denominator,
            "class_id_agreement_count": object_totals["class_id_agreement_count"],
            "class_id_agreement_fraction": (
                object_totals["class_id_agreement_count"] / object_denominator
                if object_denominator else None
            ),
            "raw_review_state_agreement_count": object_totals["raw_review_state_agreement_count"],
            "raw_review_state_agreement_fraction": (
                object_totals["raw_review_state_agreement_count"] / object_denominator
                if object_denominator else None
            ),
            "unmatched_object_boxes_are_non_agreements": True,
            "object_box_denominator_is_matched_pairs_plus_each_unmatched_box": True,
            "one_sided_valid_export_boxes_are_unmatched_non_agreements": True,
            "images_omitted_by_both_have_no_object_box_units": True,
            "zero_object_box_images_by_reviewer": dict(zero_object_images),
            "both_reviewers_zero_object_boxes": both_zero_object_images,
            "zero_object_box_counts_apply_only_to_valid_source_sides_in_box_metrics": True,
            "zero_annotation_images_by_reviewer": dict(zero_annotation_images),
        },
        "head_source_disposition": {
            "metric": "classes 0-4 only; cross-class spatial IoU pairs plus each unmatched head box",
            "denominator": source_denominator,
            "agreement_count_resolved_and_equal": source_numerator,
            "non_agreement_count": source_denominator - source_numerator,
            "agreement_fraction": source_numerator / source_denominator if source_denominator else None,
            "unresolved_matched_pair_count": object_totals["derived_head_source_unresolved_pair_count"],
            "resolved_mismatch_pair_count": object_totals["derived_head_source_resolved_mismatch_count"],
            "head_vs_nonhead_class_boundary_pair_count": object_totals["head_vs_nonhead_class_boundary_pair_count"],
            "unmatched_head_box_count": object_totals["unmatched_head_box_count"],
            "unmatched_unresolved_head_box_count": object_totals["unmatched_unresolved_head_box_count"],
            "incomplete_source_pair_count": object_totals["incomplete_source_pair_count"],
            "unresolved_head_box_counts_by_reviewer": {
                "a": head_source_counts["a"]["unresolved"],
                "b": head_source_counts["b"]["unresolved"],
            },
            "derived_source_counts_by_reviewer": {
                "a": {key: head_source_counts["a"][key] for key in ("real_scene", "depicted", "unresolved")},
                "b": {key: head_source_counts["b"][key] for key in ("real_scene", "depicted", "unresolved")},
            },
            "zero_head_box_images_by_reviewer": dict(zero_head_images),
            "source_derivation": (
                "For classes 0-4, depiction_only is depicted. In other scenes, center-in-region "
                "or union coverage >= 0.5 is depicted; smaller positive coverage is unresolved. "
                "Zero overlap is real_scene only for clear mixed_scene or explicitly attested "
                "other scene and review_state=confirmed. Invalid/incomplete source review is "
                "unresolved. A matched source pair agrees only if both dispositions are resolved "
                "and equal; unresolved and unmatched head boxes are non-agreements. Class 5 is "
                "depicted; class 6 is a loose physical hat; class 7 is a surface boundary and is "
                "compared separately by physical surface_type. counts_as_real_wearer is not used "
                "as source truth."
            ),
        },
        "reports": [
            "summary.json", "per_image_agreement.csv", "disagreements.csv",
            "box_matches.csv", "roster_issues.csv",
        ],
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    per_image_fields = [
        "roster_index", "sha256", "image_id_a", "image_id_b", "file_name_a", "file_name_b",
        "image_review_status_a", "image_review_status_b",
        "image_review_status_available_a", "image_review_status_available_b",
        "image_review_status_pair", "image_review_status_comparable",
        "image_review_status_agrees", "image_review_status_incomplete",
        "dimensions", "review_status_a", "review_status_b", "source_files_verified",
        "source_file_a_verified", "source_file_b_verified",
        "box_comparable", "partial_box_metrics", "source_metadata_comparable",
        "source_metadata_exact_agreement",
        "source_metadata_mismatch_fields", "source_metadata_a", "source_metadata_b",
        "clear_status_metadata_agreement",
        "depiction_region_geometry", "class_box_agreement", "object_source_agreement",
        "reviewer_a_annotation_count", "reviewer_b_annotation_count",
        "excluded_invalid_object_box_count_a", "excluded_invalid_object_box_count_b",
        "zero_object_boxes_a", "zero_object_boxes_b", "zero_head_boxes_a", "zero_head_boxes_b",
        "disagreement_count",
    ]
    per_image_rows = []
    for row in image_rows:
        formatted = dict(row)
        for field in (
            "source_metadata_mismatch_fields", "source_metadata_a", "source_metadata_b",
            "depiction_region_geometry", "class_box_agreement", "object_source_agreement",
        ):
            value = formatted.get(field)
            formatted[field] = (
                "" if value is None
                else json.dumps(value, ensure_ascii=False, sort_keys=True)
            )
        per_image_rows.append(formatted)
    write_csv(output / "per_image_agreement.csv", per_image_fields, per_image_rows)
    disagreement_fields = [
        "sha256", "image_id_a", "image_id_b", "file_name_a", "file_name_b",
        "category", "field", "value_a", "value_b", "detail",
    ]
    write_csv(output / "disagreements.csv", disagreement_fields, disagreement_rows)
    box_fields = [
        "sha256", "image_id_a", "image_id_b", "file_name_a", "file_name_b",
        "comparison", "group", "status", "iou", "class_a", "class_b",
        "review_state_a", "review_state_b", "derived_source_a", "derived_source_b",
        "class_id_agrees", "review_state_agrees", "derived_source_agrees", "box_a", "box_b",
    ]
    write_csv(output / "box_matches.csv", box_fields, box_rows)
    issue_fields = ["reviewer", "image_id", "file_name", "sha256", "issue_type", "issue"]
    write_csv(output / "roster_issues.csv", issue_fields, diagnostics)
    print(f"Wrote descriptive comparison reports to {output}")
    print(f"Predeclared roster images: {len(roster)}; box-comparable: {box_comparable_count}")
    print(
        "Image-review status agreement: "
        f"{image_review_status_agreement_count}/{len(roster)} roster images; "
        f"incomplete status on {image_review_status_incomplete_count}"
    )
    print(f"Roster diagnostics: {len(diagnostics)}")
    print("No approval or 95% pass decision was computed; human adjudication remains required.")
    return 0 if all_roster_match else 2


if __name__ == "__main__":
    raise SystemExit(main())
