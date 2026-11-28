"""Merge browser helmet-vision-review-v7 exports without changing annotations.

Example::

    python scripts/merge_review_json.py --inputs reviews/batch-01.json reviews/batch-02.json \
        --output helmet-vision-review-v7.json

The original images remain separate and must be collected in one directory before
running ``convert_review_json_to_yolo.py``. Existing output files are never replaced.
"""

import argparse
import json
from pathlib import Path
import sys

try:
    from .convert_review_json_to_yolo import (
        CLASSES,
        REVIEW_FORMAT_V7,
        ConversionError,
        safe_file_name,
        safe_image_id,
    )
except ImportError:
    from convert_review_json_to_yolo import (
        CLASSES,
        REVIEW_FORMAT_V7,
        ConversionError,
        safe_file_name,
        safe_image_id,
    )


class MergeError(Exception):
    """An actionable input or output error while combining review batches."""


def reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise MergeError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def reject_nonstandard_constant(value):
    raise MergeError(f"non-standard JSON number {value!r} is not allowed")


def load_batch(path):
    try:
        dataset = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, MergeError) as error:
        raise MergeError(f"Cannot read review JSON {path}: {error}") from error

    if not isinstance(dataset, dict):
        raise MergeError(f"{path}: review export must be a JSON object")
    if dataset.get("format") != REVIEW_FORMAT_V7:
        raise MergeError(f"{path}: only {REVIEW_FORMAT_V7} browser exports can be merged")

    expected_classes = [{"id": index, "name": name} for index, name in enumerate(CLASSES)]
    if dataset.get("classes") != expected_classes:
        raise MergeError(f"{path}: class mapping does not match the project's eight-class ontology")
    if not isinstance(dataset.get("rule"), str) or not dataset["rule"].strip():
        raise MergeError(f"{path}: review export is missing its labeling rule")

    images = dataset.get("images")
    if not isinstance(images, list) or not images:
        raise MergeError(f"{path}: review export must contain a non-empty images array")

    metadata = {key: value for key, value in dataset.items() if key != "images"}
    return metadata, images


def merge_review_json(input_paths, output_path):
    resolved_inputs = [path.expanduser().resolve() for path in input_paths]
    resolved_output = output_path.expanduser().resolve()
    if len(resolved_inputs) < 2:
        raise MergeError("provide at least two review exports with --inputs")
    if any(path == resolved_output for path in resolved_inputs):
        raise MergeError("--output must be different from every input review JSON")
    if resolved_output.suffix.lower() != ".json":
        raise MergeError("--output must use the .json extension")
    if resolved_output.exists():
        raise MergeError(f"output already exists; choose a new path: {resolved_output}")

    merged_images = []
    seen_ids = set()
    seen_names = set()
    base_metadata = None

    for path in resolved_inputs:
        if not path.is_file():
            raise MergeError(f"input review JSON does not exist: {path}")
        metadata, images = load_batch(path)
        if base_metadata is None:
            base_metadata = metadata
        elif metadata != base_metadata:
            raise MergeError(
                f"{path}: top-level metadata differs from the first batch"
            )

        for index, image in enumerate(images):
            where = f"{path} images[{index}]"
            if not isinstance(image, dict):
                raise MergeError(f"{where}: image entry must be an object")
            try:
                image_id = safe_image_id(image.get("image_id"), where).casefold()
                file_name = safe_file_name(image.get("file_name"), where).casefold()
            except ConversionError as error:
                raise MergeError(str(error)) from error
            if image_id in seen_ids:
                raise MergeError(f"{where}: duplicate image_id across batches: {image['image_id']!r}")
            if file_name in seen_names:
                raise MergeError(f"{where}: duplicate file_name across batches: {image['file_name']!r}")
            seen_ids.add(image_id)
            seen_names.add(file_name)
            merged_images.append(image)

    result = dict(base_metadata)
    result["images"] = merged_images
    try:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise MergeError(f"Could not create output directory {resolved_output.parent}: {error}") from error

    created_output = False
    try:
        with resolved_output.open("x", encoding="utf-8", newline="\n") as stream:
            created_output = True
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    except FileExistsError as error:
        raise MergeError(f"output already exists; choose a new path: {resolved_output}") from error
    except (OSError, TypeError, ValueError) as error:
        if created_output:
            try:
                resolved_output.unlink(missing_ok=True)
            except OSError:
                pass
        raise MergeError(f"Could not write merged review JSON {resolved_output}: {error}") from error

    return len(merged_images), resolved_output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs", required=True, nargs="+", type=Path,
        help="Two or more browser helmet-vision-review-v7 JSON exports in merge order",
    )
    parser.add_argument("--output", required=True, type=Path, help="New merged review JSON path")
    args = parser.parse_args(argv)

    try:
        image_count, output_path = merge_review_json(args.inputs, args.output)
    except (ConversionError, MergeError) as error:
        print(f"Merge failed: {error}", file=sys.stderr)
        return 2

    print(f"Merged {image_count} reviewed images into {output_path}")
    print("Next: run convert_review_json_to_yolo.py with the original images directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
