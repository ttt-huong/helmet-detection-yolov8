"""Validate the locked 175-image browser review package without extracting it.

Run from the repository root with:

    python scripts/validate_pilot_review_package.py

The ZIP and roster fingerprints are pinned in the lock record and this script.
JPEG bytes are read one member at a time and decoded in memory; no files are
written and this check does not approve image rights or training use.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = REPO_ROOT / "datasets" / "candidates" / "construction-ppe-pilot-draft"
ZIP_PATH = PILOT_DIR / "construction-ppe-pilot-review-package-locked.zip"
ROSTER_PATH = PILOT_DIR / "pilot-roster.csv"
LOCK_PATH = PILOT_DIR / "PILOT_ROSTER_LOCK.md"

EXPECTED_ROSTER_SHA256 = "fbd330cfcfcecdd39a3314898c35ca2eac2b9b75c3f86ba92e3122beb4ba4205"
EXPECTED_ZIP_SHA256 = "aa386345b02f003e59a408afcf61a55e211cc468bd95981efd99b39d69f01ccf"
EXPECTED_IMAGE_COUNT = 175
EXPECTED_BATCH_COUNT = 9
EXPECTED_SESSION_COUNTS = {
    "batch-01/session-01": 15,
    "batch-01/session-02": 5,
    "batch-02/session-01": 17,
    "batch-02/session-02": 3,
    "batch-03/session-01": 15,
    "batch-03/session-02": 5,
    "batch-04/session-01": 16,
    "batch-04/session-02": 4,
    "batch-05/session-01": 15,
    "batch-05/session-02": 5,
    "batch-06/session-01": 17,
    "batch-06/session-02": 3,
    "batch-07/session-01": 15,
    "batch-07/session-02": 5,
    "batch-08/session-01": 17,
    "batch-08/session-02": 3,
    "batch-09/session-01": 15,
}

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_SESSION_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_SESSION_PIXELS = 48_000_000
REQUIRED_ROSTER_COLUMNS = ["sha256", "width", "height", "file_name_a", "file_name_b"]
SESSION_IMAGE_RE = re.compile(r"(batch-\d{2}/session-\d{2})/([^/]+\.jpg)", re.IGNORECASE)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_README_MEMBER = "README.md"


def expected_directory_members() -> set[str]:
    directories = {f"batch-{number:02d}/" for number in range(1, EXPECTED_BATCH_COUNT + 1)}
    directories.update(f"{session}/" for session in EXPECTED_SESSION_COUNTS)
    return directories


class PreflightError(Exception):
    """A package validation failure that should result in a nonzero exit."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_roster() -> dict[str, dict[str, object]]:
    if not ROSTER_PATH.is_file():
        raise PreflightError(f"Roster not found: {ROSTER_PATH}")

    try:
        with ROSTER_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != REQUIRED_ROSTER_COLUMNS:
                raise PreflightError(
                    "Roster columns must be exactly: " + ",".join(REQUIRED_ROSTER_COLUMNS)
                )

            by_name: dict[str, dict[str, object]] = {}
            hashes: set[str] = set()
            for line, row in enumerate(reader, start=2):
                where = f"{ROSTER_PATH.name}:{line}"
                filename_a = (row.get("file_name_a") or "").strip()
                filename_b = (row.get("file_name_b") or "").strip()
                if not filename_a or filename_a != filename_b:
                    raise PreflightError(f"{where}: package expects identical nonempty A/B filenames")
                if (PurePosixPath(filename_a).name != filename_a
                        or "\\" in filename_a or filename_a in {".", ".."}
                        or Path(filename_a).suffix.lower() != ".jpg"):
                    raise PreflightError(f"{where}: unsafe or non-JPEG roster filename {filename_a!r}")

                sha = (row.get("sha256") or "").strip().lower()
                if not SHA256_RE.fullmatch(sha):
                    raise PreflightError(f"{where}: invalid SHA-256")
                name_key = filename_a.casefold()
                if name_key in by_name:
                    raise PreflightError(f"{where}: duplicate roster filename {filename_a!r}")
                if sha in hashes:
                    raise PreflightError(f"{where}: duplicate roster SHA-256 {sha}")

                try:
                    width = int(row.get("width", ""))
                    height = int(row.get("height", ""))
                except (TypeError, ValueError) as error:
                    raise PreflightError(f"{where}: width and height must be integers") from error
                if width < 1 or height < 1:
                    raise PreflightError(f"{where}: width and height must be positive")

                by_name[name_key] = {
                    "file_name": filename_a,
                    "sha256": sha,
                    "width": width,
                    "height": height,
                }
                hashes.add(sha)

    except (OSError, UnicodeError, csv.Error) as error:
        raise PreflightError(f"Cannot read roster: {error}") from error

    if len(by_name) != EXPECTED_IMAGE_COUNT:
        raise PreflightError(
            f"Expected {EXPECTED_IMAGE_COUNT} unique roster rows, found {len(by_name)}"
        )
    return by_name


def validate_lock_record() -> None:
    if not LOCK_PATH.is_file():
        raise PreflightError(f"Lock record not found: {LOCK_PATH}")
    try:
        lock_text = LOCK_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise PreflightError(f"Cannot read lock record: {error}") from error

    if "Status: **locked for independent pilot review only**." not in lock_text:
        raise PreflightError("Lock record does not declare the expected locked-review status")

    checks = (
        ("roster", EXPECTED_ROSTER_SHA256,
         r"- Roster SHA-256: `([0-9a-f]{64})`"),
        ("locked review ZIP", EXPECTED_ZIP_SHA256,
         r"- Browser review package SHA-256: `([0-9a-f]{64})`"),
    )
    for label, expected, pattern in checks:
        match = re.search(pattern, lock_text, re.IGNORECASE)
        if not match:
            raise PreflightError(f"Lock record is missing the {label} SHA-256")
        if match.group(1).lower() != expected:
            raise PreflightError(f"Lock record {label} SHA-256 differs from the pinned value")


def session_sort_key(name: str) -> tuple[int, int]:
    batch_number, session_number = re.search(r"batch-(\d{2})/session-(\d{2})", name).groups()
    return int(batch_number), int(session_number)


def validate_package(roster: dict[str, dict[str, object]]) -> tuple[list[dict[str, object]], list[str]]:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as error:
        raise PreflightError(
            "Pillow is required to decode and verify dimensions; install it in the current Python environment."
        ) from error

    if not ZIP_PATH.is_file():
        raise PreflightError(f"Locked review ZIP not found: {ZIP_PATH}")
    actual_zip_sha = sha256_file(ZIP_PATH)
    if actual_zip_sha != EXPECTED_ZIP_SHA256:
        raise PreflightError(
            f"Locked ZIP SHA-256 mismatch: expected {EXPECTED_ZIP_SHA256}, got {actual_zip_sha}"
        )

    stats = {
        name: {
            "count": 0,
            "bytes": 0,
            "pixels": 0,
            "max_file_bytes": 0,
            "max_image_pixels": 0,
            "max_image_dimensions": (0, 0),
            "errors": 0,
        }
        for name in EXPECTED_SESSION_COUNTS
    }
    errors: list[str] = []
    seen_names: set[str] = set()
    seen_hashes: set[str] = set()
    seen_members: set[str] = set()
    image_entry_count = 0

    def add_error(message: str, session: str | None = None) -> None:
        errors.append(message)
        if session in stats:
            stats[session]["errors"] += 1

    try:
        with ZipFile(ZIP_PATH) as archive:
            for info in archive.infolist():
                if info.filename in seen_members:
                    add_error(f"Duplicate ZIP member path: {info.filename}")
                    continue
                seen_members.add(info.filename)

                if info.is_dir():
                    if info.filename not in expected_directory_members():
                        add_error(f"Unexpected directory in ZIP: {info.filename}")
                    if info.file_size != 0:
                        add_error(f"Directory member has nonzero size: {info.filename}")
                    continue
                extension = PurePosixPath(info.filename).suffix.lower()
                if extension not in IMAGE_EXTENSIONS:
                    if info.filename != EXPECTED_README_MEMBER:
                        add_error(f"Unexpected non-image ZIP member: {info.filename}")
                    continue

                image_entry_count += 1
                match = SESSION_IMAGE_RE.fullmatch(info.filename)
                if not match:
                    add_error(f"Image entry is outside the expected batch/session layout: {info.filename}")
                    continue

                session, filename = match.groups()
                if session not in stats:
                    add_error(f"Unexpected session directory: {session}")
                    continue
                stats[session]["count"] += 1
                stats[session]["max_file_bytes"] = max(
                    int(stats[session]["max_file_bytes"]), info.file_size
                )

                name_key = filename.casefold()
                if name_key in seen_names:
                    add_error(f"Duplicate ZIP filename: {filename}", session)
                    continue
                seen_names.add(name_key)

                if extension != ".jpg":
                    add_error(f"Expected .jpg package member: {info.filename}", session)
                if info.file_size > MAX_FILE_BYTES:
                    add_error(
                        f"{info.filename}: {info.file_size} bytes exceeds {MAX_FILE_BYTES}", session
                    )
                    continue

                try:
                    raw = archive.read(info)
                except (OSError, BadZipFile, RuntimeError) as error:
                    add_error(f"Cannot read {info.filename}: {error}", session)
                    continue
                if len(raw) != info.file_size:
                    add_error(f"{info.filename}: ZIP size metadata differs from bytes read", session)
                if len(raw) > MAX_FILE_BYTES:
                    add_error(f"{info.filename}: uncompressed file exceeds 10 MiB", session)
                    continue

                digest = hashlib.sha256(raw).hexdigest()
                if digest in seen_hashes:
                    add_error(f"Duplicate image SHA-256 in ZIP: {filename}", session)
                seen_hashes.add(digest)

                expected = roster.get(name_key)
                if expected is None:
                    add_error(f"ZIP image is absent from the roster: {filename}", session)
                else:
                    if filename != expected["file_name"]:
                        add_error(f"Filename case differs from roster: {filename}", session)
                    if digest != expected["sha256"]:
                        add_error(f"SHA-256 mismatch for {filename}", session)

                try:
                    with Image.open(io.BytesIO(raw)) as image:
                        image_format = image.format
                        width, height = image.size
                        image.load()
                except (
                    OSError,
                    ValueError,
                    UnidentifiedImageError,
                    Image.DecompressionBombError,
                ) as error:
                    add_error(f"JPEG decode failed for {filename}: {error}", session)
                    continue

                if image_format != "JPEG":
                    add_error(f"{filename}: decoded format is {image_format}, expected JPEG", session)
                pixels = width * height
                stats[session]["bytes"] += len(raw)
                stats[session]["pixels"] += pixels
                if pixels > int(stats[session]["max_image_pixels"]):
                    stats[session]["max_image_pixels"] = pixels
                    stats[session]["max_image_dimensions"] = (width, height)
                if pixels > MAX_IMAGE_PIXELS:
                    add_error(f"{filename}: {pixels} pixels exceeds {MAX_IMAGE_PIXELS}", session)
                if expected is not None and (width, height) != (expected["width"], expected["height"]):
                    add_error(
                        f"{filename}: dimensions {width}x{height} differ from roster "
                        f"{expected['width']}x{expected['height']}",
                        session,
                    )

    except (OSError, BadZipFile, RuntimeError) as error:
        raise PreflightError(f"Cannot read locked review ZIP: {error}") from error

    if image_entry_count != EXPECTED_IMAGE_COUNT:
        add_error(f"Expected {EXPECTED_IMAGE_COUNT} package images, found {image_entry_count}")
    actual_directories = {
        name for name in seen_members if name.endswith("/")
    }
    missing_directories = expected_directory_members() - actual_directories
    if missing_directories:
        add_error(
            "ZIP is missing expected directories: "
            + ", ".join(sorted(missing_directories))
        )
    missing_names = set(roster) - seen_names
    extra_names = seen_names - set(roster)
    if missing_names:
        add_error(f"ZIP is missing {len(missing_names)} roster filenames")
    if extra_names:
        add_error(f"ZIP contains {len(extra_names)} filenames absent from the roster")
    if seen_hashes != {str(item["sha256"]) for item in roster.values()}:
        add_error("ZIP image SHA-256 set does not equal the locked roster hash set")

    actual_sessions = {name for name, item in stats.items() if int(item["count"]) > 0}
    if len(actual_sessions) != 17 or actual_sessions != set(EXPECTED_SESSION_COUNTS):
        add_error(
            f"Expected exactly 17 planned session folders; found {len(actual_sessions)}: "
            + ", ".join(sorted(actual_sessions, key=session_sort_key))
        )
    if len({name.split("/")[0] for name in actual_sessions}) != EXPECTED_BATCH_COUNT:
        add_error(f"Expected {EXPECTED_BATCH_COUNT} top-level batches")

    for session, expected_count in EXPECTED_SESSION_COUNTS.items():
        item = stats[session]
        if int(item["count"]) != expected_count:
            add_error(
                f"{session}: expected {expected_count} images, found {item['count']}", session
            )
        if int(item["bytes"]) > MAX_SESSION_BYTES:
            add_error(f"{session}: total bytes exceed 50 MiB", session)
        if int(item["pixels"]) > MAX_SESSION_PIXELS:
            add_error(f"{session}: total pixels exceed 48 MP", session)

    return [
        {"session": name, **stats[name]} for name in sorted(stats, key=session_sort_key)
    ], errors


def main() -> int:
    try:
        validate_lock_record()
        actual_roster_sha = sha256_file(ROSTER_PATH)
        if actual_roster_sha != EXPECTED_ROSTER_SHA256:
            raise PreflightError(
                f"Roster SHA-256 mismatch: expected {EXPECTED_ROSTER_SHA256}, got {actual_roster_sha}"
            )
        roster = read_roster()
        rows, errors = validate_package(roster)
    except (OSError, PreflightError) as error:
        print(f"PILOT PREFLIGHT FAILED: {error}", file=sys.stderr)
        return 1

    print(f"Roster SHA-256: {EXPECTED_ROSTER_SHA256}")
    print(f"ZIP SHA-256:    {EXPECTED_ZIP_SHA256}")
    print(
        "session              images   uncompressed MiB   total MP   max file MiB   max image MP   dimensions"
    )
    for row in rows:
        width, height = row["max_image_dimensions"]
        status = "FAIL" if row["errors"] else "OK"
        print(
            f"{row['session']:<21} {row['count']:>3}"
            f" {int(row['bytes']) / (1024 * 1024):>17.3f}"
            f" {int(row['pixels']) / 1_000_000:>9.3f}"
            f" {int(row['max_file_bytes']) / (1024 * 1024):>14.3f}"
            f" {int(row['max_image_pixels']) / 1_000_000:>12.3f}"
            f" {width}x{height:<12} {status}"
        )

    total_images = sum(int(row["count"]) for row in rows)
    total_bytes = sum(int(row["bytes"]) for row in rows)
    total_pixels = sum(int(row["pixels"]) for row in rows)
    print(
        f"TOTAL: {len(rows)} sessions, {total_images} JPEGs, "
        f"{total_bytes / (1024 * 1024):.3f} MiB, {total_pixels / 1_000_000:.3f} MP"
    )

    if errors:
        print(f"PILOT PREFLIGHT FAILED: {len(errors)} issue(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "PILOT PACKAGE-INTEGRITY PREFLIGHT PASSED: pinned roster, filenames, hashes, dimensions, "
        "JPEG decoding, and browser import caps match. This confirms technical package integrity only; "
        "it does not approve review completion, image rights, converter eligibility, or training use."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
