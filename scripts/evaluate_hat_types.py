"""Create diagnostic-only metrics for the hardhat model and depiction-region filter.

This standalone evaluator does not evaluate or approve deployment releases.
"""

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import sys


CLASS_NAMES = {
    0: "hard_hat_worn",
    1: "depiction_region",
}
WORN_IDS = {0}
DEPICTION_REGION_ID = 1
MIN_MODEL_CONFIDENCE = 0.001
MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH = 10
CORE_DEPICTION_SURFACE_TYPES = ("poster", "printed_photo", "screen")
DEPICTION_SURFACE_TYPES = {*CORE_DEPICTION_SURFACE_TYPES, "other_depiction"}
DEPICTION_SCENES = ("depiction_only", "mixed_scene")
LEGACY_SCENE_TYPES = {"poster_only": "depiction_only", "mixed_scene": "mixed_scene", "other": "other"}
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
HAT_TYPE_NEGATIVE_SOURCES = ("traffic_helmet_worn", "cap_worn", "beanie_worn")
REVIEW_CLASS_NAMES = (
    "hard_hat_worn", "traffic_helmet_worn", "cap_worn", "beanie_worn",
    "bare_head", "depicted_hat", "loose_hat", "depiction_region",
)
MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS = 100


class EvaluationError(Exception):
    """An actionable configuration or dataset error."""


def load_yaml(path):
    try:
        import yaml
    except ImportError as error:
        raise EvaluationError(
            "PyYAML is required to read data.yaml. Install it in the cloud runtime "
            "with `python -m pip install pyyaml`."
        ) from error

    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError) as error:
        raise EvaluationError(f"Could not read {path}: {error}") from error
    if not isinstance(config, dict):
        raise EvaluationError(f"Expected a YAML mapping in {path}")
    return config


def normalize_names(value, source):
    if isinstance(value, list):
        names = {index: name for index, name in enumerate(value)}
    elif isinstance(value, dict):
        try:
            names = {int(index): name for index, name in value.items()}
        except (TypeError, ValueError) as error:
            raise EvaluationError(f"{source} must use integer class IDs") from error
    else:
        raise EvaluationError(f"{source} has no supported class-name mapping")

    if names != CLASS_NAMES:
        raise EvaluationError(f"{source} class order differs. Expected {CLASS_NAMES}, found {names}")
    return names


def resolve_dataset_root(config, data_yaml):
    configured = config.get("path", str(data_yaml.parent))
    if not isinstance(configured, str):
        raise EvaluationError("data.yaml path must be a string")
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = data_yaml.parent / root
    return root.resolve()


def image_paths_for_split(value, root, data_yaml):
    if not isinstance(value, str) or not value.strip():
        raise EvaluationError("data.yaml must define a non-empty test split")
    source = Path(value).expanduser()
    if not source.is_absolute():
        source = root / source
    source = source.resolve()

    if source.is_dir():
        paths = sorted(
            path for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    elif source.is_file() and source.suffix.lower() == ".txt":
        paths = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            path = Path(text).expanduser()
            if not path.is_absolute():
                path = source.parent / path
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                raise EvaluationError(f"{source}:{line_number} is not an image path: {text}")
            paths.append(path.resolve())
    else:
        raise EvaluationError(
            f"The test split must be an image directory or a .txt manifest: {source}"
        )

    if not paths:
        raise EvaluationError(f"The test split contains no images: {source}")
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise EvaluationError(f"The test split lists a missing image: {missing[0]}")
    return paths


def label_path_for(image_path):
    parts = list(image_path.parts)
    image_indexes = [index for index, part in enumerate(parts) if part.lower() == "images"]
    if not image_indexes:
        raise EvaluationError(
            f"Cannot locate labels for {image_path}. Use sibling images/ and labels/ directories."
        )
    parts[image_indexes[0]] = "labels"
    return Path(*parts).with_suffix(".txt")


def read_truth(image_path, width, height):
    label_path = label_path_for(image_path)
    if not label_path.is_file():
        raise EvaluationError(
            f"Missing labels for {image_path}. Use an empty label file for background images."
        )

    truth = []
    for line_number, line in enumerate(label_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 5:
            raise EvaluationError(f"{label_path}:{line_number} must contain five YOLO values")
        try:
            class_id = int(fields[0])
            x_center, y_center, box_width, box_height = map(float, fields[1:])
        except ValueError as error:
            raise EvaluationError(f"{label_path}:{line_number} contains non-numeric values") from error
        values = (x_center, y_center, box_width, box_height)
        if class_id not in CLASS_NAMES or not all(math.isfinite(value) for value in values):
            raise EvaluationError(f"{label_path}:{line_number} contains an invalid class or coordinate")
        if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 < box_width <= 1 and 0 < box_height <= 1):
            raise EvaluationError(f"{label_path}:{line_number} has an invalid normalized box")
        if (x_center - box_width / 2 < 0 or x_center + box_width / 2 > 1
                or y_center - box_height / 2 < 0 or y_center + box_height / 2 > 1):
            raise EvaluationError(f"{label_path}:{line_number} box extends beyond the image")
        truth.append((class_id, (
            (x_center - box_width / 2) * width,
            (y_center - box_height / 2) * height,
            (x_center + box_width / 2) * width,
            (y_center + box_height / 2) * height,
        )))
    return truth


def normalized_yolo_box_from_pixels(box, width, height):
    x1, y1, x2, y2 = box
    values = (
        (x1 + x2) / (2 * width),
        (y1 + y2) / (2 * height),
        (x2 - x1) / width,
        (y2 - y1) / height,
    )
    return tuple(float(f"{value:.8f}") for value in values)


def intersection_area(first, second):
    overlap_width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    overlap_height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    return overlap_width * overlap_height


def box_area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def box_iou(first, second):
    intersection = intersection_area(first, second)
    union = box_area(first) + box_area(second) - intersection
    return intersection / union if union > 0 else 0.0


def rectangle_union_area(boxes):
    """Return the area covered by a union of axis-aligned xyxy rectangles."""
    valid = [box for box in boxes if box_area(box) > 0]
    x_edges = sorted({coordinate for box in valid for coordinate in (box[0], box[2])})
    total = 0.0
    for left, right in zip(x_edges, x_edges[1:]):
        if right <= left:
            continue
        intervals = sorted(
            (box[1], box[3]) for box in valid if box[0] < right and box[2] > left
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
        total += (right - left) * covered_y
    return total


def depiction_union_overlap(box, region_boxes):
    area = box_area(box)
    if area <= 0:
        return False, 0.0
    center_x = (box[0] + box[2]) / 2
    center_y = (box[1] + box[3]) / 2
    center_inside = any(
        region[0] <= center_x <= region[2] and region[1] <= center_y <= region[3]
        for region in region_boxes
    )
    intersections = [
        (max(box[0], region[0]), max(box[1], region[1]),
         min(box[2], region[2]), min(box[3], region[3]))
        for region in region_boxes
        if min(box[2], region[2]) > max(box[0], region[0])
        and min(box[3], region[3]) > max(box[1], region[1])
    ]
    return center_inside, rectangle_union_area(intersections) / area


def filter_worn_predictions(predictions):
    depiction_regions = [
        item["box"] for item in predictions if item["class_id"] == DEPICTION_REGION_ID
    ]
    count_candidates = []
    suppressed = []
    uncertain = []

    for item in predictions:
        if item["class_id"] not in WORN_IDS:
            continue
        box = item["box"]
        center_inside, coverage = depiction_union_overlap(box, depiction_regions)
        if center_inside or coverage >= 0.5:
            suppressed.append(item)
        elif coverage > 0:
            uncertain.append(item)
        else:
            count_candidates.append(item)

    return count_candidates, suppressed, uncertain


def match_predictions(truth, predictions, minimum_iou):
    depiction_boxes = [
        box for class_id, box in truth if class_id == DEPICTION_REGION_ID
    ]
    pairs = []
    for truth_index, (truth_class, truth_box) in enumerate(truth):
        for prediction_index, prediction in enumerate(predictions):
            if truth_class != prediction["class_id"]:
                continue
            if (truth_class in WORN_IDS
                    and any(intersection_area(prediction["box"], box) > 0 for box in depiction_boxes)):
                continue
            overlap = box_iou(truth_box, prediction["box"])
            if overlap >= minimum_iou:
                pairs.append((-overlap, -prediction["confidence"], truth_index, prediction_index))

    matched_truth = set()
    matched_predictions = set()
    matches = []
    for negative_iou, _, truth_index, prediction_index in sorted(pairs):
        if truth_index in matched_truth or prediction_index in matched_predictions:
            continue
        matched_truth.add(truth_index)
        matched_predictions.add(prediction_index)
        matches.append((truth_index, prediction_index, -negative_iou))
    return matched_truth, matched_predictions, matches


def normalize_scene_type(value, where):
    scene_type = LEGACY_SCENE_TYPES.get(value, value) if isinstance(value, str) else value
    if not isinstance(scene_type, str) or scene_type not in {"depiction_only", "mixed_scene", "other"}:
        raise EvaluationError(
            f"{where} scene_type must be depiction_only, mixed_scene, or other; found {value!r}."
        )
    return scene_type


def normalize_surface_types(value, where):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvaluationError(f"{where} depiction_surface_types must be a JSON array of strings")
    if len(value) != len(set(value)):
        raise EvaluationError(f"{where} depiction_surface_types must not contain duplicates")
    unknown = sorted(set(value) - DEPICTION_SURFACE_TYPES)
    if unknown:
        raise EvaluationError(
            f"{where} depiction_surface_types contains unsupported value(s): {', '.join(unknown)}"
        )
    return value


def normalize_surface_instances(value, where, include_box=False):
    if not isinstance(value, list):
        raise EvaluationError(f"{where} must be a JSON array of surface records")
    normalized = []
    seen_ids = set()
    seen_boxes = set()
    for index, record in enumerate(value):
        record_where = f"{where}[{index}]"
        expected_keys = {"surface_id", "surface_type", "box"} if include_box else {
            "surface_id", "surface_type",
        }
        if not isinstance(record, dict) or set(record) != expected_keys:
            raise EvaluationError(
                f"{record_where} has unexpected surface record fields"
            )
        surface_id = record.get("surface_id")
        surface_type = record.get("surface_type")
        if (not isinstance(surface_id, str) or not surface_id.strip()
                or surface_id != surface_id.strip()
                or any(ord(char) < 32 for char in surface_id)):
            raise EvaluationError(f"{record_where} surface_id must be a non-empty trimmed string")
        if surface_id in seen_ids:
            raise EvaluationError(f"{record_where} duplicates surface_id {surface_id!r}")
        if not isinstance(surface_type, str) or surface_type not in DEPICTION_SURFACE_TYPES:
            raise EvaluationError(f"{record_where} has an unsupported surface_type")
        seen_ids.add(surface_id)
        normalized_record = {"surface_id": surface_id, "surface_type": surface_type}
        if include_box:
            box = record.get("box")
            if (not isinstance(box, list) or len(box) != 4
                    or any(type(value) not in (int, float) or not math.isfinite(value) for value in box)):
                raise EvaluationError(f"{record_where} box must be four finite normalized numbers")
            box = [float(value) for value in box]
            center_x, center_y, width, height = box
            if (not 0 <= center_x <= 1 or not 0 <= center_y <= 1
                    or not 0 < width <= 1 or not 0 < height <= 1
                    or center_x - width / 2 < 0 or center_x + width / 2 > 1
                    or center_y - height / 2 < 0 or center_y + height / 2 > 1
                    or any(float(f"{value:.8f}") != value for value in box)):
                raise EvaluationError(
                    f"{record_where} box must match the normalized eight-decimal YOLO geometry"
                )
            box_key = tuple(box)
            if box_key in seen_boxes:
                raise EvaluationError(
                    f"{record_where} duplicates region geometry assigned to another surface ID"
                )
            seen_boxes.add(box_key)
            normalized_record["box"] = box
        normalized.append(normalized_record)
    return normalized


def image_group(truth, metadata_value=None):
    if metadata_value:
        return metadata_value["scene_type"]

    has_depiction = any(class_id == DEPICTION_REGION_ID for class_id, _ in truth)
    has_real_person = any(class_id in WORN_IDS for class_id, _ in truth)
    if has_depiction and has_real_person:
        return "mixed_scene"
    if has_depiction:
        return "depiction_only"
    return "other"


def read_metadata(path):
    if path is None:
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        required_columns = {
            "image_id", "scene_type", "depiction_surface_types",
            "depiction_surfaces", "depiction_region_surfaces",
        }
        if (not rows.fieldnames
                or set(rows.fieldnames) != required_columns
                or len(rows.fieldnames) != len(required_columns)):
            raise EvaluationError(
                "Metadata CSV must contain exactly image_id, scene_type, depiction_surface_types, "
                "depiction_surfaces, depiction_region_surfaces"
            )
        metadata = {}
        for row in rows:
            image_id = (row.get("image_id") or "").strip()
            if not image_id or image_id in metadata:
                raise EvaluationError(f"Metadata CSV contains a blank or duplicate image_id: {image_id!r}")
            scene_value = (row.get("scene_type") or "").strip()
            scene_type = normalize_scene_type(scene_value, f"Metadata CSV image {image_id!r}")
            try:
                raw_surfaces = json.loads(row.get("depiction_surface_types") or "")
                raw_inventory = json.loads(row.get("depiction_surfaces") or "")
                raw_regions = json.loads(row.get("depiction_region_surfaces") or "")
            except json.JSONDecodeError as error:
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} has invalid surface JSON"
                ) from error
            surfaces = normalize_surface_types(
                raw_surfaces, f"Metadata CSV image {image_id!r}"
            )
            inventory = normalize_surface_instances(
                raw_inventory, f"Metadata CSV image {image_id!r} depiction_surfaces"
            )
            region_surfaces = normalize_surface_instances(
                raw_regions,
                f"Metadata CSV image {image_id!r} depiction_region_surfaces",
                include_box=True,
            )
            derived_types = list(dict.fromkeys(
                surface["surface_type"] for surface in inventory
            ))
            if set(surfaces) != set(derived_types):
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} depiction_surface_types do not match its inventory"
                )
            inventory_by_id = {
                surface["surface_id"]: surface["surface_type"]
                for surface in inventory
            }
            region_by_id = {
                surface["surface_id"]: (surface["surface_type"], tuple(surface["box"]))
                for surface in region_surfaces
            }
            if (len(region_by_id) != len(region_surfaces)
                    or set(region_by_id) != set(inventory_by_id)
                    or any(region_by_id[surface_id][0] != inventory_by_id[surface_id]
                           for surface_id in inventory_by_id)):
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} depiction regions must map one-to-one "
                    "to inventory IDs with matching surface types"
                )
            if scene_type in DEPICTION_SCENES and not surfaces:
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} must declare at least one depiction surface "
                    f"for scene_type={scene_type!r}"
                )
            if scene_type == "other" and surfaces:
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} cannot declare depiction surfaces "
                    "with scene_type='other'"
                )
            if scene_type in DEPICTION_SCENES and not inventory:
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} must declare depiction surface instances"
                )
            if scene_type == "other" and (inventory or region_surfaces):
                raise EvaluationError(
                    f"Metadata CSV image {image_id!r} cannot declare depiction surfaces in an other scene"
                )
            metadata[image_id] = {
                "scene_type": scene_type,
                "depiction_surface_types": surfaces,
                "depiction_surfaces": inventory,
                "depiction_region_surfaces": region_surfaces,
            }
    return metadata


def reject_duplicate_json_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise EvaluationError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_split_assignments(path):
    if not path.is_file():
        raise EvaluationError(f"Missing split manifest required for subtype rejection gate: {path}")

    assignments = {}
    group_splits = {}
    expected_columns = ("image_id", "split", "group_id", "scene_type")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise EvaluationError(
                "split_manifest.csv must contain image_id,split,group_id,scene_type"
            )
        for line_number, row in enumerate(reader, 2):
            image_id = (row.get("image_id") or "").strip()
            split = (row.get("split") or "").strip()
            group_id = (row.get("group_id") or "").strip()
            scene_type = (row.get("scene_type") or "").strip()
            if (not image_id or not group_id
                    or split not in {"train", "val", "test"}
                    or scene_type not in {"depiction_only", "mixed_scene", "other"}
                    or image_id != row.get("image_id")
                    or split != row.get("split")
                    or group_id != row.get("group_id")
                    or scene_type != row.get("scene_type")
                    or any(ord(char) < 32 for char in image_id + group_id)):
                raise EvaluationError(
                    f"{path}:{line_number} has invalid image/split/group/scene metadata"
                )
            if image_id in assignments:
                raise EvaluationError(f"{path}:{line_number} duplicates image_id {image_id!r}")
            folded = group_id.casefold()
            previous = group_splits.setdefault(folded, (group_id, split))
            if previous != (group_id, split):
                raise EvaluationError(
                    f"{path}:{line_number} reuses group_id {group_id!r} across splits or casing"
                )
            assignments[image_id] = {
                "split": split,
                "group_id": group_id,
                "scene_type": scene_type,
            }

    if not assignments:
        raise EvaluationError(f"{path} contains no image assignments")
    return assignments


def read_image_source_metadata(path, manifest_path, test_image_ids):
    assignments = read_split_assignments(manifest_path)
    if not path.is_file():
        raise EvaluationError(f"Missing image-source metadata required for subtype gate: {path}")
    try:
        source = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationError(f"Could not read image-source metadata {path}: {error}") from error

    if (not isinstance(source, dict)
            or source.get("format") != "helmet-vision-image-sources-v4"
            or source.get("review_format") != "helmet-vision-review-v7"
            or not isinstance(source.get("images"), list)):
        raise EvaluationError(
            "Image-source metadata must use helmet-vision-image-sources-v4 "
            "with review_format=helmet-vision-review-v7 and an images array"
        )

    records = {}
    for index, record in enumerate(source["images"]):
        where = f"{path} images[{index}]"
        if not isinstance(record, dict):
            raise EvaluationError(f"{where} must be an object")
        image_id = record.get("image_id")
        file_name = record.get("file_name")
        if (not isinstance(image_id, str) or not image_id.strip()
                or image_id != image_id.strip()
                or not isinstance(file_name, str) or not file_name.strip()):
            raise EvaluationError(f"{where} has an invalid image_id or file_name")
        if image_id in records:
            raise EvaluationError(f"{where} duplicates image_id {image_id!r}")
        assignment = assignments.get(image_id)
        if assignment is None:
            raise EvaluationError(f"{where} is absent from split_manifest.csv")
        if any(record.get(key) != value for key, value in assignment.items()):
            raise EvaluationError(f"{where} disagrees with split_manifest.csv")

        image_review_status = record.get("image_review_status")
        counts = record.get("review_class_counts")
        surface_types = record.get("depiction_surface_types")
        surfaces = record.get("depiction_surfaces")
        region_surfaces = record.get("depiction_region_surfaces")
        if (image_review_status not in {"reviewed_empty", "reviewed_with_labels"}
                or not isinstance(counts, dict)
                or set(counts) != set(REVIEW_CLASS_NAMES)
                or any(type(counts.get(name)) is not int or counts[name] < 0
                       for name in REVIEW_CLASS_NAMES)
                or not isinstance(surface_types, list)
                or not isinstance(surfaces, list)
                or not isinstance(region_surfaces, list)):
            raise EvaluationError(f"{where} has invalid review counts/status or region inventory")
        surface_types = normalize_surface_types(surface_types, f"{where} depiction_surface_types")
        surfaces = normalize_surface_instances(surfaces, f"{where} depiction_surfaces")
        region_surfaces = normalize_surface_instances(
            region_surfaces, f"{where} depiction_region_surfaces", include_box=True
        )
        derived_types = list(dict.fromkeys(surface["surface_type"] for surface in surfaces))
        if set(surface_types) != set(derived_types):
            raise EvaluationError(
                f"{where} depiction_surface_types do not match the unique types in depiction_surfaces"
            )
        inventory_by_id = {
            surface["surface_id"]: surface["surface_type"] for surface in surfaces
        }
        regions_by_id = {
            surface["surface_id"]: surface["surface_type"] for surface in region_surfaces
        }
        if inventory_by_id != regions_by_id:
            raise EvaluationError(
                f"{where} depiction_region_surfaces must map one-to-one to depiction_surfaces"
            )
        annotation_count = sum(counts.values())
        if ((image_review_status == "reviewed_empty" and annotation_count != 0)
                or (image_review_status == "reviewed_with_labels" and annotation_count == 0)
                or counts["depiction_region"] != len(region_surfaces)):
            raise EvaluationError(f"{where} review status/counts conflict with its region inventory")
        if assignment["scene_type"] == "other" and (surface_types or surfaces or region_surfaces):
            raise EvaluationError(f"{where} declares depiction surfaces for scene_type='other'")
        if (assignment["scene_type"] in DEPICTION_SCENES
                and (not surface_types or not surfaces or not region_surfaces)):
            raise EvaluationError(
                f"{where} requires surface types, inventory, and regions for a depiction scene"
            )
        record = dict(record)
        record["depiction_surface_types"] = surface_types
        record["depiction_surfaces"] = surfaces
        record["depiction_region_surfaces"] = region_surfaces
        records[image_id] = record

    if set(records) != set(assignments):
        missing = sorted(set(assignments) - set(records))
        extra = sorted(set(records) - set(assignments))
        raise EvaluationError(
            "Image-source metadata and split_manifest.csv must cover the same image IDs; "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )
    manifest_test_ids = {
        image_id for image_id, assignment in assignments.items()
        if assignment["split"] == "test"
    }
    if set(test_image_ids) != manifest_test_ids:
        missing = sorted(manifest_test_ids - set(test_image_ids))
        extra = sorted(set(test_image_ids) - manifest_test_ids)
        raise EvaluationError(
            "data.yaml test images must exactly match split_manifest.csv test IDs; "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )
    return records


def eligible_subtype_only_test_group_images(
    image_source_records, test_image_ids, subtype, reviewed_scene_metadata=None,
):
    grouped_records = defaultdict(list)
    for image_id in test_image_ids:
        record = image_source_records.get(image_id)
        if record is not None:
            grouped_records[record["group_id"]].append((image_id, record))

    eligible_image_ids = set()
    eligible_group_ids = set()
    for group_id, members in grouped_records.items():
        if any(
            record["split"] != "test"
            or record["scene_type"] != "other"
            or record["depiction_surface_types"]
            or record["depiction_surfaces"]
            or record["depiction_region_surfaces"]
            or any(
                record["review_class_counts"][name] != 0
                for name in REVIEW_CLASS_NAMES if name != subtype
            )
            for _, record in members
        ):
            continue
        if not any(record["review_class_counts"][subtype] > 0 for _, record in members):
            continue
        if reviewed_scene_metadata is not None and any(
            image_id not in reviewed_scene_metadata
            or reviewed_scene_metadata[image_id]["scene_type"] != "other"
            or reviewed_scene_metadata[image_id]["depiction_surface_types"]
            or reviewed_scene_metadata[image_id]["depiction_surfaces"]
            or reviewed_scene_metadata[image_id]["depiction_region_surfaces"]
            for image_id, _ in members
        ):
            continue
        eligible_group_ids.add(group_id)
        eligible_image_ids.update(image_id for image_id, _ in members)

    return eligible_image_ids, eligible_group_ids


def metric_row(class_id, counts):
    tp = counts[class_id]["TP"]
    fp = counts[class_id]["FP"]
    fn = counts[class_id]["FN"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "class_id": class_id,
        "class_name": CLASS_NAMES[class_id],
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "precision": precision,
        "recall": recall,
    }


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def depiction_surface_gates(counts, has_reviewed_metadata):
    gates = {}
    for surface_type in CORE_DEPICTION_SURFACE_TYPES:
        gates[surface_type] = {}
        for scene_type in DEPICTION_SCENES:
            values = counts[surface_type][scene_type]
            image_count = values["image_count"]
            depiction_surface_instance_image_count = values["depiction_surface_instance_image_count"]
            false_candidates = values["false_unverified_worn_candidates"]
            if not has_reviewed_metadata:
                status = "not_evaluated_missing_reviewed_metadata"
            elif image_count == 0:
                status = "not_evaluated_missing_coverage"
            elif depiction_surface_instance_image_count != image_count:
                status = "fail_missing_ground_truth_depiction_region"
            elif false_candidates:
                status = "fail_false_unverified_worn_candidates"
            else:
                status = "pass_reviewed_metadata"
            gates[surface_type][scene_type] = {
                "image_count": image_count,
                "depiction_surface_instance_image_count": depiction_surface_instance_image_count,
                "false_unverified_worn_candidates": false_candidates,
                "status": status,
            }
    return gates


def evaluate(args):
    try:
        import yaml
        from PIL import Image
        from ultralytics import YOLO
    except ImportError as error:
        raise EvaluationError(
            "Install the project requirements in the cloud runtime before evaluation: "
            "`python -m pip install -r requirements.txt`."
        ) from error

    data_yaml = args.data_yaml.expanduser().resolve()
    config = load_yaml(data_yaml)
    normalize_names(config.get("names"), "data.yaml")
    dataset_root = resolve_dataset_root(config, data_yaml)
    images = image_paths_for_split(config.get("test"), dataset_root, data_yaml)
    metadata = read_metadata(args.metadata_csv.expanduser().resolve() if args.metadata_csv else None)
    test_image_stems = [image_path.stem for image_path in images]
    test_image_ids = set(test_image_stems)
    if len(test_image_stems) != len(test_image_ids):
        raise EvaluationError("Locked-test image stems must be unique for exact metadata coverage")

    image_source_argument = getattr(args, "image_source_metadata", None)
    image_source_path = (
        image_source_argument.expanduser().resolve()
        if image_source_argument
        else dataset_root / "dataset_image_sources.json"
    )
    split_manifest_path = dataset_root / "split_manifest.csv"
    image_source_metadata_error = None
    try:
        image_source_records = read_image_source_metadata(
            image_source_path, split_manifest_path, test_image_ids
        )
        if metadata:
            for image_id in test_image_ids:
                source_record = image_source_records[image_id]
                scene_record = metadata.get(image_id)
                if scene_record is not None:
                    if (scene_record["scene_type"] != source_record["scene_type"]
                            or set(scene_record["depiction_surface_types"])
                            != set(source_record["depiction_surface_types"])):
                        raise EvaluationError(
                            f"Image-source scene/surface types disagree with reviewed scene metadata for {image_id!r}"
                        )
                    source_surfaces = {
                        item["surface_id"]: item["surface_type"]
                        for item in source_record["depiction_surfaces"]
                    }
                    reviewed_surfaces = {
                        item["surface_id"]: item["surface_type"]
                        for item in scene_record["depiction_surfaces"]
                    }
                    source_regions = {
                        item["surface_id"]: (item["surface_type"], tuple(item["box"]))
                        for item in source_record["depiction_region_surfaces"]
                    }
                    reviewed_regions = {
                        item["surface_id"]: (item["surface_type"], tuple(item["box"]))
                        for item in scene_record["depiction_region_surfaces"]
                    }
                    if source_surfaces != reviewed_surfaces or source_regions != reviewed_regions:
                        raise EvaluationError(
                            f"Image-source surface inventory/regions disagree with reviewed scene metadata for {image_id!r}"
                        )
    except (EvaluationError, OSError, UnicodeError, csv.Error, ValueError) as error:
        image_source_records = {}
        image_source_metadata_error = f"{type(error).__name__}: {error}"

    subtype_eligible_group_members = {
        subtype: eligible_subtype_only_test_group_images(
            image_source_records,
            test_image_ids,
            subtype,
            metadata if args.metadata_csv else None,
        )
        for subtype in HAT_TYPE_NEGATIVE_SOURCES
    }

    model = YOLO(str(args.weights.expanduser().resolve()))
    normalize_names(model.names, "checkpoint")
    if model.task != "detect":
        raise EvaluationError(f"Expected a detection checkpoint, found task={model.task!r}")

    counts = defaultdict(Counter)
    image_rows = []
    prediction_rows = []
    group_counts = defaultdict(Counter)
    hat_type_rejection_counts = {
        subtype: {
            "eligible_image_ids": subtype_eligible_group_members[subtype][0],
            "eligible_group_ids": subtype_eligible_group_members[subtype][1],
            "hard_hat_prediction_box_count": 0,
            "images_with_hard_hat_prediction_count": 0,
        }
        for subtype in HAT_TYPE_NEGATIVE_SOURCES
    }
    surface_gate_counts = {
        surface_type: {
            scene_type: Counter(
                image_count=0,
                depiction_surface_instance_image_count=0,
                false_unverified_worn_candidates=0,
            )
            for scene_type in DEPICTION_SCENES
        }
        for surface_type in CORE_DEPICTION_SURFACE_TYPES
    }

    for image_index, image_path in enumerate(images, start=1):
        with Image.open(image_path) as source:
            width, height = source.size
        truth = read_truth(image_path, width, height)
        reviewed_metadata = metadata.get(image_path.stem)
        group = image_group(truth, reviewed_metadata)
        surface_types = (
            reviewed_metadata["depiction_surface_types"] if reviewed_metadata else []
        )
        surface_instances = (
            reviewed_metadata["depiction_surfaces"] if reviewed_metadata else []
        )
        region_surfaces = (
            reviewed_metadata["depiction_region_surfaces"] if reviewed_metadata else []
        )
        region_surface_coverage_complete = (
            len(region_surfaces) == len(surface_instances)
            and {item["surface_id"]: item["surface_type"] for item in region_surfaces}
            == {item["surface_id"]: item["surface_type"] for item in surface_instances}
        )
        region_count = sum(class_id == DEPICTION_REGION_ID for class_id, _ in truth)
        if reviewed_metadata:
            actual_region_boxes = [
                normalized_yolo_box_from_pixels(box, width, height)
                for class_id, box in truth if class_id == DEPICTION_REGION_ID
            ]
            mapped_region_boxes = [tuple(record["box"]) for record in region_surfaces]
            if len(set(actual_region_boxes)) != len(actual_region_boxes):
                raise EvaluationError(
                    f"Reviewed test image {image_path.stem!r} has duplicate model class-1 GT geometry "
                    "for distinct surface instances"
                )
            if Counter(actual_region_boxes) != Counter(mapped_region_boxes):
                raise EvaluationError(
                    f"Reviewed test image {image_path.stem!r} model class-1 GT boxes do not match "
                    "the sidecar's per-surface box mapping"
                )
        if (reviewed_metadata and group in DEPICTION_SCENES
                and (region_count != len(surface_instances)
                     or not region_surface_coverage_complete)):
            raise EvaluationError(
                f"Reviewed test image {image_path.stem!r} is marked {group!r} but its "
                "ground-truth depiction_region count does not equal its reviewed surface inventory"
            )
        if (reviewed_metadata and group == "other"
                and any(class_id == DEPICTION_REGION_ID for class_id, _ in truth)):
            raise EvaluationError(
                f"Reviewed test image {image_path.stem!r} is marked 'other' but contains depiction labels"
            )
        result = model.predict(
            source=str(image_path),
            imgsz=args.imgsz,
            conf=MIN_MODEL_CONFIDENCE,
            device=args.device,
            verbose=False,
        )[0]
        predictions = []
        for row in result.boxes.data.tolist():
            class_id = int(row[5])
            values = tuple(map(float, row[:5]))
            if class_id not in CLASS_NAMES or not all(math.isfinite(value) for value in values):
                continue
            confidence = float(row[4])
            if class_id in WORN_IDS and confidence < args.confidence:
                continue
            if class_id == DEPICTION_REGION_ID and confidence < MIN_MODEL_CONFIDENCE:
                continue
            predictions.append({
                "class_id": class_id,
                "confidence": confidence,
                "box": tuple(float(value) for value in row[:4]),
            })

        for subtype in HAT_TYPE_NEGATIVE_SOURCES:
            gate_counts = hat_type_rejection_counts[subtype]
            if image_path.stem in gate_counts["eligible_image_ids"]:
                hard_hat_predictions = sum(
                    prediction["class_id"] in WORN_IDS for prediction in predictions
                )
                gate_counts["hard_hat_prediction_box_count"] += hard_hat_predictions
                if hard_hat_predictions:
                    gate_counts["images_with_hard_hat_prediction_count"] += 1

        countable, suppressed, uncertain = filter_worn_predictions(predictions)
        filtered_predictions = [
            item for item in predictions
            if item["class_id"] not in WORN_IDS
        ] + countable
        matched_truth, matched_predictions, matches = match_predictions(
            truth, filtered_predictions, args.match_iou
        )

        for truth_index, (class_id, _) in enumerate(truth):
            counts[class_id]["FN"] += 1
        for prediction in filtered_predictions:
            counts[prediction["class_id"]]["FP"] += 1
        for truth_index, prediction_index, overlap in matches:
            truth_class = truth[truth_index][0]
            counts[truth_class]["FN"] -= 1
            counts[truth_class]["FP"] -= 1
            counts[truth_class]["TP"] += 1

        group_counts[group]["images"] += 1
        true_worn = sum(class_id in WORN_IDS for class_id, _ in truth)
        countable_worn = len(countable)
        suppressed_worn = len(suppressed)
        uncertain_worn = len(uncertain)
        unmatched_countable_worn = sum(
            prediction_index not in matched_predictions
            for prediction_index, prediction in enumerate(filtered_predictions)
            if prediction["class_id"] in WORN_IDS
        )
        if group == "depiction_only":
            group_counts[group]["unverified_worn_candidates"] += countable_worn
            group_counts[group]["unverified_false_worn_candidates"] += countable_worn
            group_counts[group]["suppressed_worn_candidates"] += suppressed_worn
            group_counts[group]["uncertain_worn_candidates"] += uncertain_worn
        elif group == "mixed_scene":
            group_counts[group]["expected_real_worn_boxes"] += true_worn
            group_counts[group]["unverified_worn_candidates"] += countable_worn
            group_counts[group]["unverified_unmatched_worn_candidates"] += unmatched_countable_worn
            group_counts[group]["suppressed_worn_candidates"] += suppressed_worn
            group_counts[group]["uncertain_worn_candidates"] += uncertain_worn

        if group in DEPICTION_SCENES:
            false_candidate_count = (
                countable_worn if group == "depiction_only" else unmatched_countable_worn
            )
            for surface_type in CORE_DEPICTION_SURFACE_TYPES:
                if surface_type in surface_types:
                    surface_gate_counts[surface_type][group]["image_count"] += 1
                    if (region_count == len(surface_instances)
                            and region_surface_coverage_complete):
                        surface_gate_counts[surface_type][group][
                            "depiction_surface_instance_image_count"
                        ] += 1
                    surface_gate_counts[surface_type][group][
                        "false_unverified_worn_candidates"
                    ] += false_candidate_count

        per_class_truth = Counter(class_id for class_id, _ in truth)
        per_class_candidate = Counter(item["class_id"] for item in filtered_predictions)
        image_row = {
            "image_id": image_path.stem,
            "image_path": str(image_path),
            "scene_type": group,
            "depiction_surface_types": json.dumps(surface_types, separators=(",", ":")),
            "ground_truth_worn": true_worn,
            "unverified_worn_candidates": countable_worn,
            "suppressed_worn_candidates": suppressed_worn,
            "uncertain_worn_candidates": uncertain_worn,
            "unverified_unmatched_worn_candidates": unmatched_countable_worn,
        }
        for class_id, class_name in CLASS_NAMES.items():
            image_row[f"gt_{class_name}"] = per_class_truth[class_id]
            image_row[f"pred_{class_name}"] = per_class_candidate[class_id]
        image_rows.append(image_row)

        matched_by_prediction = {prediction_index: (truth_index, overlap)
                                 for truth_index, prediction_index, overlap in matches}
        filtered_index_by_prediction = {
            id(item): index for index, item in enumerate(filtered_predictions)
        }
        suppressed_keys = {id(item) for item in suppressed}
        uncertain_keys = {id(item) for item in uncertain}
        countable_keys = {id(item) for item in countable}
        for prediction_index, prediction in enumerate(predictions):
            if id(prediction) in suppressed_keys:
                status = "suppressed_by_depiction_region"
            elif id(prediction) in uncertain_keys:
                status = "uncertain_partial_depiction_overlap"
            elif id(prediction) in countable_keys:
                status = "unverified_wearer_candidate"
            elif prediction["class_id"] == DEPICTION_REGION_ID:
                status = "depiction_region"
            else:
                status = "prediction"
            filtered_index = filtered_index_by_prediction.get(id(prediction))
            match = matched_by_prediction.get(filtered_index) if filtered_index is not None else None
            metric_status = "excluded" if filtered_index is None else "TP" if match else "FP"
            prediction_rows.append({
                "image_id": image_path.stem,
                "scene_type": group,
                "depiction_surface_types": json.dumps(surface_types, separators=(",", ":")),
                "class_name": CLASS_NAMES[prediction["class_id"]],
                "confidence": prediction["confidence"],
                "x1": prediction["box"][0],
                "y1": prediction["box"][1],
                "x2": prediction["box"][2],
                "y2": prediction["box"][3],
                "status": status,
                "metric_status": metric_status,
                "matched_iou": match[1] if match else "",
            })

        if image_index % 100 == 0 or image_index == len(images):
            print(f"Evaluated {image_index}/{len(images)} test images", flush=True)

    class_rows = [metric_row(class_id, counts) for class_id in CLASS_NAMES]
    if args.metadata_csv and set(metadata) != test_image_ids:
        raise EvaluationError("Reviewed metadata must have exactly one row for every test image stem")
    has_reviewed_metadata = bool(args.metadata_csv)
    surface_gates = depiction_surface_gates(surface_gate_counts, has_reviewed_metadata)

    hat_type_negative_rejection_gates = {}
    hat_type_negative_rejection_gate_reasons = []
    for subtype in HAT_TYPE_NEGATIVE_SOURCES:
        counts_for_subtype = hat_type_rejection_counts[subtype]
        eligible_image_count = len(counts_for_subtype["eligible_image_ids"])
        eligible_group_count = len(counts_for_subtype["eligible_group_ids"])
        hard_hat_prediction_box_count = counts_for_subtype["hard_hat_prediction_box_count"]
        images_with_hard_hat_prediction_count = counts_for_subtype[
            "images_with_hard_hat_prediction_count"
        ]
        reasons = []
        if image_source_metadata_error:
            reasons.append("image_source_metadata_missing_or_invalid")
        if eligible_group_count < MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS:
            reasons.append("eligible_locked_test_groups_below_minimum")
        if hard_hat_prediction_box_count > 0:
            reasons.append("hard_hat_predictions_nonzero")
        status = "pass" if not reasons else "blocked"
        hat_type_negative_rejection_gates[subtype] = {
            "eligible_locked_test_image_count": eligible_image_count,
            "eligible_locked_test_group_count": eligible_group_count,
            "minimum_locked_test_groups": MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS,
            "confidence_threshold": args.confidence,
            "hard_hat_prediction_box_count": hard_hat_prediction_box_count,
            "images_with_hard_hat_prediction_count": images_with_hard_hat_prediction_count,
            "status": status,
        }
        hat_type_negative_rejection_gate_reasons.extend(
            f"{subtype}:{reason}" for reason in reasons
        )
    hat_type_negative_rejection_gate_status = (
        "pass"
        if all(gate["status"] == "pass" for gate in hat_type_negative_rejection_gates.values())
        else "blocked"
    )

    locked_test_hardhat_ground_truth_count = sum(row["ground_truth_worn"] for row in image_rows)
    hardhat_ground_truth_gate_status = (
        "pass" if locked_test_hardhat_ground_truth_count >= MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH
        else "blocked"
    )
    all_surface_gates_pass = all(
            gate["image_count"] > 0
            and gate["depiction_surface_instance_image_count"] == gate["image_count"]
            and gate["false_unverified_worn_candidates"] == 0
            and gate["status"] == "pass_reviewed_metadata"
            for per_scene in surface_gates.values()
            for gate in per_scene.values()
        )
    diagnostic_gate_status = (
        "diagnostic_pass"
        if all_surface_gates_pass
        and hardhat_ground_truth_gate_status == "pass"
        and hat_type_negative_rejection_gate_status == "pass"
        else "diagnostic_blocked"
    )
    summary = {
        "status": "diagnostic_complete",
        "artifact_type": "standalone_hat_type_diagnostics",
        "diagnostic_only": True,
        "release_approval": "not_evaluated_by_standalone_evaluator",
        "checkpoint": str(args.weights.expanduser().resolve()),
        "data_yaml": str(data_yaml),
        "device": args.device,
        "images": len(images),
        "confidence_threshold": args.confidence,
        "minimum_model_confidence": MIN_MODEL_CONFIDENCE,
        "locked_test_hardhat_ground_truth_count": locked_test_hardhat_ground_truth_count,
        "minimum_locked_test_hardhat_ground_truth": MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH,
        "hardhat_ground_truth_gate_status": hardhat_ground_truth_gate_status,
        "matching_iou_threshold": args.match_iou,
        "class_metrics_after_wearer_filter": class_rows,
        "scene_groups": {name: dict(values) for name, values in group_counts.items()},
        "scene_metadata_source": "reviewed_metadata_csv" if has_reviewed_metadata else "inferred_from_test_labels",
        "required_depiction_surface_types": list(CORE_DEPICTION_SURFACE_TYPES),
        "required_depiction_scenes": list(DEPICTION_SCENES),
        "depiction_surface_test_gates": surface_gates,
        "hat_type_negative_source_metadata": {
            "path": str(image_source_path),
            "split_manifest_path": str(split_manifest_path),
            "status": "valid" if image_source_metadata_error is None else "invalid_or_missing",
            "error": image_source_metadata_error,
        },
        "required_hat_type_negative_sources": list(HAT_TYPE_NEGATIVE_SOURCES),
        "hat_type_negative_rejection_gate_status": hat_type_negative_rejection_gate_status,
        "hat_type_negative_rejection_gates": hat_type_negative_rejection_gates,
        "hat_type_negative_rejection_gate_reasons": hat_type_negative_rejection_gate_reasons,
        "diagnostic_gate_status": diagnostic_gate_status,
        "count_policy": (
            "This standalone diagnostic evaluator counts only zero-overlap *_worn detections as unverified candidates. "
            "Coverage is the union of depiction-region intersections divided by wearer-box area. "
            "A wearer-box center inside any depiction_region or at least 50 percent union coverage suppresses it. "
            "Smaller positive overlap is marked uncertain and is not counted. Surface gates use only reviewed "
            "depiction_surface_types metadata; no medium is inferred from labels or scene_type. "
            "This report does not evaluate release approval; the API still requires human review."
        ),
        "limitations": [
            "A missed or borderless poster, printed photo, or screen may leave a false wearer candidate.",
            "Each zero-false-candidate gate applies only to its reviewed locked-test surface and scene stratum, not as a general guarantee.",
            "Subtype rejection is evaluated over every locked-test image in a group only when all group images are scene_type='other' with empty surface inventories and no other review classes, and at least one group image contains that subtype.",
            "The diagnostic hardhat ground-truth minimum is unmet when the locked test has fewer than the configured minimum boxes.",
            "A frame-level annotation is not necessarily an independent scene, person, video, or depiction sample.",
        ],
    }

    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "per_class_metrics.csv", class_rows)
    write_csv(output / "per_image_metrics.csv", image_rows)
    write_csv(output / "predictions.csv", prediction_rows)
    hat_type_rejection_rows = [
        {
            "hat_type": subtype,
            "eligible_locked_test_image_count": gate["eligible_locked_test_image_count"],
            "eligible_locked_test_group_count": gate["eligible_locked_test_group_count"],
            "minimum_locked_test_groups": gate["minimum_locked_test_groups"],
            "confidence_threshold": gate["confidence_threshold"],
            "hard_hat_prediction_box_count": gate["hard_hat_prediction_box_count"],
            "images_with_hard_hat_prediction_count": gate["images_with_hard_hat_prediction_count"],
            "status": gate["status"],
            "reasons": json.dumps(
                [reason for reason in hat_type_negative_rejection_gate_reasons
                 if reason.startswith(f"{subtype}:")],
                ensure_ascii=False,
            ),
        }
        for subtype, gate in hat_type_negative_rejection_gates.items()
    ]
    write_csv(output / "hat_type_negative_rejection_metrics.csv", hat_type_rejection_rows)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Locked-test hardhat ground-truth boxes: "
        f"{locked_test_hardhat_ground_truth_count} "
        f"(minimum: {MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH})"
    )
    print(f"Standalone diagnostic gate: {diagnostic_gate_status}")
    print(json.dumps(summary["depiction_surface_test_gates"], ensure_ascii=False, indent=2))
    print(f"Wrote evaluation results to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-yaml", type=Path, required=True, help="Two-class YOLO data.yaml with a test split")
    parser.add_argument("--weights", type=Path, required=True, help="Trained two-class hardhat best.pt")
    parser.add_argument("--output", type=Path, required=True, help="New directory for reports")
    parser.add_argument("--device", required=True, help="Explicit cloud device, for example 0 or cpu")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--match-iou", type=float, default=0.5)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--metadata-csv", type=Path,
        help="Reviewed CSV with image_id,scene_type,depiction_surface_types,depiction_surfaces,depiction_region_surfaces; required for surface gates to pass",
    )
    parser.add_argument(
        "--image-source-metadata", type=Path, default=None,
        help=(
            "review-v7 image-sources-v4 JSON with per-image review_class_counts, split, and group_id; "
            "defaults to <data.yaml dataset root>/dataset_image_sources.json; required for subtype rejection gate"
        ),
    )
    args = parser.parse_args()
    if not 0.01 <= args.confidence <= 0.9:
        parser.error("--confidence must be between 0.01 and 0.90")
    if not 0.1 <= args.match_iou <= 0.95:
        parser.error("--match-iou must be between 0.10 and 0.95")
    if args.imgsz < 32:
        parser.error("--imgsz must be at least 32")

    try:
        evaluate(args)
    except (EvaluationError, OSError, ValueError) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
