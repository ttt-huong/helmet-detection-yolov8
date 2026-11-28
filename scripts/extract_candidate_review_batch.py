#!/usr/bin/env python3
"""Extract a small, review-only image batch from the pinned Construction-PPE ZIP.

This tool uses source YOLO class 0 (``helmet``) only to select candidate images.
It never copies source labels or creates project annotations/rights/split/group/scene
metadata. The output is not a converter input. Pillow is required to check the
browser's per-image and per-session image limits.

Example::

    python scripts/extract_candidate_review_batch.py
    python scripts/extract_candidate_review_batch.py --limit 12
"""

import argparse
import csv
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
import warnings
import zipfile
from pathlib import Path, PurePosixPath

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as error:  # pragma: no cover - actionable CLI error
    raise SystemExit("Pillow is required; install it with `python -m pip install Pillow`.") from error


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_DIR = ROOT / "datasets" / "candidates"
DEFAULT_ARCHIVE = CANDIDATES_DIR / "ultralytics-construction-ppe.zip"
DEFAULT_OUTPUT = CANDIDATES_DIR / "construction-ppe-review-batch"
ARCHIVE_ROOT = "construction-ppe"
SOURCE_URL = "https://docs.ultralytics.com/datasets/detect/construction-ppe"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
EXPECTED_ARCHIVE_SIZE = 647_666_037
EXPECTED_ARCHIVE_SHA256 = "E5817AA9C73F33E525D76CA6BC6AF4E4EAC9DCEA9BCFEF1CFD1A71C09FBC1232"
EXPECTED_MEMBER_COUNT = 2_004
EXPECTED_SPLIT_COUNTS = {"train": 800, "val": 200}
SPLITS = ("train", "val")
MAX_BATCH_IMAGES = 20
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_SESSION_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_SESSION_PIXELS = 48_000_000
IMAGE_SUFFIXES = {".jpg"}
EXPECTED_CLASSES = {
    0: "helmet",
    1: "gloves",
    2: "vest",
    3: "boots",
    4: "goggles",
    5: "Person",
    6: "no_helmet",
    7: "no_goggle",
    8: "no_gloves",
    9: "no_boots",
    10: "forklift",
    11: "no_vest",
}
METADATA_MEMBERS = {
    f"{ARCHIVE_ROOT}/LICENSE.txt",
    f"{ARCHIVE_ROOT}/README.md",
    f"{ARCHIVE_ROOT}/data.yaml",
    f"{ARCHIVE_ROOT}/manifest.jsonl",
}


class BatchError(Exception):
    """An actionable archive, selection, or output error."""


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_data_yaml(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError as error:
        raise BatchError("data.yaml is not valid UTF-8") from error

    required_paths = {"train": "images/train", "val": "images/val"}
    seen_paths = {}
    class_map = {}
    reading_names = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == "names:":
            if reading_names:
                raise BatchError("data.yaml has duplicate names blocks")
            reading_names = True
            continue
        if reading_names:
            if not stripped or stripped.startswith("#"):
                continue
            if not line[:1].isspace():
                reading_names = False
            else:
                match = re.fullmatch(r"\s+(\d+):\s*([A-Za-z0-9_-]+)\s*", line)
                if not match:
                    raise BatchError(f"data.yaml has an unsupported class entry on line {line_number}")
                class_id, class_name = int(match.group(1)), match.group(2)
                if class_id in class_map:
                    raise BatchError(f"data.yaml repeats class ID {class_id}")
                class_map[class_id] = class_name
        for key, expected in required_paths.items():
            if stripped.startswith(f"{key}:"):
                value = stripped.split(":", 1)[1].strip()
                if key in seen_paths:
                    raise BatchError(f"data.yaml repeats the {key} path")
                seen_paths[key] = value

    if seen_paths != required_paths:
        raise BatchError(f"data.yaml train/val paths must be exactly {required_paths}")
    if class_map != EXPECTED_CLASSES:
        raise BatchError("data.yaml class map differs from the pinned 12-class archive")


def safe_member_name(name):
    if "\\" in name:
        raise BatchError(f"ZIP member uses a non-portable path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BatchError(f"ZIP member has an unsafe path: {name!r}")
    if not path.parts or path.parts[0] != ARCHIVE_ROOT:
        raise BatchError(f"Unexpected ZIP root for member: {name!r}")
    return path


def parse_label_file(content, member_name):
    try:
        text = content.decode("ascii")
    except UnicodeError as error:
        raise BatchError(f"Label file is not ASCII: {member_name}") from error
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if not rows:
        raise BatchError(f"Unexpected empty source label file: {member_name}")

    class_zero_count = 0
    for row_number, fields in enumerate(rows, start=1):
        if len(fields) != 5 or not re.fullmatch(r"\d+", fields[0]):
            raise BatchError(f"Malformed YOLO row {row_number} in {member_name}")
        class_id = int(fields[0])
        if class_id not in EXPECTED_CLASSES:
            raise BatchError(f"Unknown source class ID {class_id} in {member_name}")
        try:
            box = [float(value) for value in fields[1:]]
        except ValueError as error:
            raise BatchError(f"Non-numeric YOLO box in {member_name}, row {row_number}") from error
        if (not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in box)
                or box[2] <= 0.0 or box[3] <= 0.0):
            raise BatchError(f"Invalid normalized YOLO box in {member_name}, row {row_number}")
        class_zero_count += class_id == 0
    return len(rows), class_zero_count


def parse_source_manifest(content, image_members):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError as error:
        raise BatchError("manifest.jsonl is not valid UTF-8") from error

    rows = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise BatchError(f"manifest.jsonl has an empty row at line {line_number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise BatchError(f"manifest.jsonl has invalid JSON at line {line_number}") from error
        required_keys = frozenset({"file", "split", "sha256", "annotations"})
        dimension_keys = frozenset({"width", "height"})
        record_keys = frozenset(record) if isinstance(record, dict) else frozenset()
        if record_keys not in {required_keys, required_keys | dimension_keys}:
            raise BatchError(f"manifest.jsonl row {line_number} has an unexpected schema")
        file_name, split = record["file"], record["split"]
        digest, annotation_count = record["sha256"], record["annotations"]
        if (not isinstance(file_name, str) or PurePosixPath(file_name).name != file_name
                or split not in SPLITS or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or type(annotation_count) is not int or annotation_count < 1):
            raise BatchError(f"manifest.jsonl row {line_number} has invalid source fields")
        if ("width" in record and (type(record["width"]) is not int or record["width"] <= 0
                                    or type(record["height"]) is not int or record["height"] <= 0)):
            raise BatchError(f"manifest.jsonl row {line_number} has invalid source dimensions")
        key = (split, file_name)
        if key in rows:
            raise BatchError(f"manifest.jsonl repeats {split}/{file_name}")
        rows[key] = {
            "sha256": digest,
            "annotation_count": annotation_count,
            "width": record.get("width"),
            "height": record.get("height"),
        }
    if set(rows) != set(image_members):
        raise BatchError("manifest.jsonl does not map one-to-one to the archive images")
    counts = {split: sum(key[0] == split for key in rows) for split in SPLITS}
    if counts != EXPECTED_SPLIT_COUNTS:
        raise BatchError(f"manifest image counts differ from the pinned archive: {counts}")
    return rows


def inspect_archive(archive_path):
    if archive_path.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise BatchError("archive size differs from the pinned Construction-PPE candidate")
    archive_digest = sha256_file(archive_path)
    if archive_digest.upper() != EXPECTED_ARCHIVE_SHA256:
        raise BatchError("archive SHA-256 differs from the pinned Construction-PPE candidate")

    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as error:
        raise BatchError(f"Cannot open candidate ZIP: {error}") from error

    with archive:
        infos = archive.infolist()
        if len(infos) != EXPECTED_MEMBER_COUNT:
            raise BatchError(f"Expected {EXPECTED_MEMBER_COUNT} ZIP members, found {len(infos)}")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BatchError("ZIP contains duplicate member names")

        image_members = {}
        label_members = {}
        all_file_names = set()
        for info in infos:
            path = safe_member_name(info.filename)
            parts = path.parts
            all_file_names.add(info.filename)
            if len(parts) == 2 and info.filename in METADATA_MEMBERS:
                continue
            if len(parts) == 4 and parts[1] in {"images", "labels"}:
                _, kind, split, file_name = parts
                if split not in SPLITS:
                    raise BatchError(f"Unexpected source split in ZIP: {info.filename}")
                suffix = Path(file_name).suffix.lower()
                expected_suffix = IMAGE_SUFFIXES if kind == "images" else {".txt"}
                if suffix not in expected_suffix or Path(file_name).name != file_name:
                    raise BatchError(f"Unexpected file type or nested path in ZIP: {info.filename}")
                mapping = image_members if kind == "images" else label_members
                key = (split, file_name if kind == "images" else Path(file_name).stem)
                if key in mapping:
                    raise BatchError(f"ZIP repeats a {kind} member for {split}/{file_name}")
                mapping[key] = info
                continue
            raise BatchError(f"Unexpected ZIP member: {info.filename}")

        if all_file_names != METADATA_MEMBERS | {
            info.filename for info in image_members.values()
        } | {
            info.filename for info in label_members.values()
        }:
            raise BatchError("ZIP structure contains missing or unexpected files")
        image_keys = set(image_members)
        label_keys = set(label_members)
        image_stem_keys = {(split, Path(file_name).stem) for split, file_name in image_keys}
        if image_stem_keys != label_keys:
            raise BatchError("ZIP images and labels do not have an exact one-to-one pairing")
        split_counts = {split: sum(key[0] == split for key in image_keys) for split in SPLITS}
        if split_counts != EXPECTED_SPLIT_COUNTS:
            raise BatchError(f"ZIP image counts differ from the pinned archive: {split_counts}")

        data_yaml = archive.read(f"{ARCHIVE_ROOT}/data.yaml")
        parse_data_yaml(data_yaml)
        source_readme = archive.read(f"{ARCHIVE_ROOT}/README.md").decode("utf-8", "replace")
        if "CC BY 4.0" not in source_readme:
            raise BatchError("Archive README no longer declares CC BY 4.0")
        if not archive.read(f"{ARCHIVE_ROOT}/LICENSE.txt").strip():
            raise BatchError("Archive LICENSE.txt is empty")
        manifest = parse_source_manifest(
            archive.read(f"{ARCHIVE_ROOT}/manifest.jsonl"), image_members
        )

        candidates = []
        for split, file_name in sorted(
            image_keys, key=lambda item: (SPLITS.index(item[0]), item[1].casefold(), item[1])
        ):
            image_info = image_members[(split, file_name)]
            label_info = label_members[(split, Path(file_name).stem)]
            label_count, class_zero_count = parse_label_file(
                archive.read(label_info), label_info.filename
            )
            manifest_row = manifest[(split, file_name)]
            if label_count != manifest_row["annotation_count"]:
                raise BatchError(f"Label row count disagrees with manifest for {split}/{file_name}")
            if class_zero_count:
                candidates.append({
                    "source_split": split,
                    "source_file": file_name,
                    "image_info": image_info,
                    "source_class_box_count": class_zero_count,
                    "source_sha256": manifest_row["sha256"],
                    "source_width": manifest_row["width"],
                    "source_height": manifest_row["height"],
                })
        if not candidates:
            raise BatchError("No images contain source class 0 ('helmet')")

        return zipfile.ZipFile(archive_path), archive_digest, candidates, len(candidates)


def select_browser_compatible_images(archive, candidates, limit):
    selected = []
    seen_hashes = set()
    rejected = {"file_bytes": 0, "image_pixels": 0, "session_bytes": 0,
                "session_pixels": 0, "duplicate_content": 0}
    total_bytes = 0
    total_pixels = 0

    for candidate in candidates:
        if len(selected) >= limit:
            break
        info = candidate["image_info"]
        if info.file_size > MAX_FILE_BYTES:
            rejected["file_bytes"] += 1
            continue
        if total_bytes + info.file_size > MAX_SESSION_BYTES:
            rejected["session_bytes"] += 1
            continue

        try:
            raw = archive.read(info)
            if len(raw) != info.file_size:
                raise BatchError(f"Image size mismatch for {info.filename}")
            digest = hashlib.sha256(raw).hexdigest()
            if digest != candidate["source_sha256"]:
                raise BatchError(f"Image SHA-256 disagrees with manifest for {info.filename}")
            if digest in seen_hashes:
                rejected["duplicate_content"] += 1
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format != "JPEG":
                        raise BatchError(f"Expected JPEG source image: {info.filename}")
                    width, height = image.size
                    if width * height <= MAX_IMAGE_PIXELS:
                        image.load()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            rejected["image_pixels"] += 1
            continue
        except (OSError, UnidentifiedImageError) as error:
            raise BatchError(f"Cannot verify source image {info.filename}: {error}") from error

        pixels = width * height
        if (candidate["source_width"] is not None
                and (width != candidate["source_width"] or height != candidate["source_height"])):
            raise BatchError(f"Image dimensions disagree with manifest for {info.filename}")
        if pixels <= 0:
            raise BatchError(f"Invalid image dimensions for {info.filename}")
        if pixels > MAX_IMAGE_PIXELS:
            rejected["image_pixels"] += 1
            continue
        if total_pixels + pixels > MAX_SESSION_PIXELS:
            rejected["session_pixels"] += 1
            continue

        output_name = f"{candidate['source_split']}_{candidate['source_file']}"
        selected.append({
            **candidate,
            "output_file": output_name,
            "image_bytes": raw,
            "width": width,
            "height": height,
            "sha256": digest,
        })
        seen_hashes.add(digest)
        total_bytes += len(raw)
        total_pixels += pixels

    return selected, rejected, total_bytes, total_pixels


def write_batch(output_dir, archive_path, archive_digest, selected, candidate_count,
                requested_limit, rejected, total_bytes, total_pixels):
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() or output_dir.is_symlink():
        raise BatchError(f"Output already exists; choose a new directory: {output_dir}")
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.stage-", dir=output_dir.parent))
    try:
        for item in selected:
            (stage / item["output_file"]).write_bytes(item["image_bytes"])

        with (stage / "source_index.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "selection_order", "output_file", "archive_member", "source_split",
                "source_class_id", "source_class_name", "source_class_box_count",
                "source_sha256", "source_image_bytes", "source_width", "source_height",
            ])
            writer.writeheader()
            for order, item in enumerate(selected, start=1):
                writer.writerow({
                    "selection_order": order,
                    "output_file": item["output_file"],
                    "archive_member": item["image_info"].filename,
                    "source_split": item["source_split"],
                    "source_class_id": 0,
                    "source_class_name": "helmet",
                    "source_class_box_count": item["source_class_box_count"],
                    "source_sha256": item["sha256"],
                    "source_image_bytes": len(item["image_bytes"]),
                    "source_width": item["width"],
                    "source_height": item["height"],
                })

        try:
            archive_display = archive_path.relative_to(ROOT).as_posix()
        except ValueError:
            archive_display = archive_path.as_posix()
        readme = f"""# Construction-PPE candidate image batch — review only

This folder contains {len(selected)} JPEG images selected from the pinned archive by the presence of **source class 0, `helmet`**. The source class is used only to select candidates; its label boxes were not copied. No project annotations, rights approval, final split, group ID, scene type, or depiction-surface metadata were created.

- Source archive path: `{archive_display}`
- Source archive SHA-256: `{archive_digest}`
- Source dataset page: {SOURCE_URL}
- Dataset-level license declared in the archive README: CC BY 4.0 ({LICENSE_URL})
- Rights status: **UNVERIFIED per image**. The dataset-level license declaration is not a per-image rights or provenance review.
- Provenance status: **UNVERIFIED per image**. The archive manifest provides source filename, source split, image hash, and annotation count, but no source-group or image-origin review attestation.
- Candidate selection: {len(selected)} of {candidate_count} images containing source class 0, deterministic by `train` then `val` and filename, up to the requested limit of {requested_limit}. Source split is recorded only for reference and is not a final project split.
- Browser limits: each selected image is at most 10 MiB and 24 megapixels; the batch is at most 50 MiB, 48 megapixels, and 20 images. Candidates with exact duplicate bytes or incompatible dimensions/size were skipped as needed. Skipped candidate counts: `{json.dumps(rejected, sort_keys=True)}`.
- `source_index.csv` records source selection and integrity details only. Do not treat it as a v6 review export or as converter input.

Open the local labeling page, choose **Thêm ảnh**, and select only the JPEG files in this folder. Review each image manually. The browser creates its own empty annotations and starts rights/source metadata unresolved; it does not import the original YOLO labels or this index. Keep rights unverified until you have evidence for the individual image.

The source YOLO label files were not copied. `source_index.csv` contains only the limited source-selection and integrity fields listed above; it does not certify image origin, rights, or project labels. This batch is not approved training data.
"""
        (stage / "README.md").write_text(readme, encoding="utf-8", newline="\n")

        if output_dir.exists() or output_dir.is_symlink():
            raise BatchError(f"Output appeared during extraction; refusing to replace: {output_dir}")
        stage.rename(output_dir)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                        help="Pinned raw Construction-PPE ZIP")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                        help="New output directory inside datasets/candidates")
    parser.add_argument("--limit", type=int, default=MAX_BATCH_IMAGES,
                        help="Maximum source-class-0 images to select (1-20; default 20)")
    args = parser.parse_args(argv)

    try:
        if not 1 <= args.limit <= MAX_BATCH_IMAGES:
            raise BatchError(f"--limit must be between 1 and {MAX_BATCH_IMAGES}")
        archive_path = args.archive.expanduser().resolve()
        if not archive_path.is_file():
            raise BatchError(f"Candidate archive does not exist: {archive_path}")
        output_dir = args.output_dir.expanduser().resolve()
        candidates_root = CANDIDATES_DIR.resolve()
        if output_dir == candidates_root or candidates_root not in output_dir.parents:
            raise BatchError("--output-dir must be a new directory under datasets/candidates")
        if output_dir == archive_path or output_dir.exists() or output_dir.is_symlink():
            raise BatchError(f"Output already exists or conflicts with input: {output_dir}")
        if not output_dir.parent.is_dir():
            raise BatchError(f"Output parent must already exist: {output_dir.parent}")

        archive, archive_digest, candidates, candidate_count = inspect_archive(archive_path)
        with archive:
            selected, rejected, total_bytes, total_pixels = select_browser_compatible_images(
                archive, candidates, args.limit
            )
        if not selected:
            raise BatchError("No source class-0 images fit the browser batch limits; no output created")
        write_batch(
            output_dir, archive_path, archive_digest, selected, candidate_count,
            args.limit, rejected, total_bytes, total_pixels,
        )
    except (BatchError, OSError, zipfile.BadZipFile) as error:
        parser.exit(2, f"Batch creation failed: {error}\n")

    print(f"Created review-only batch: {output_dir}")
    print(f"Selected {len(selected)} / {candidate_count} images containing source class 0 'helmet'.")
    print(f"Image files: {len(selected)}; total image bytes: {total_bytes}; total pixels: {total_pixels}.")
    print("No source YOLO labels or project review metadata were created.")
    print(f"Index: {output_dir / 'source_index.csv'}")
    print(f"Instructions: {output_dir / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
