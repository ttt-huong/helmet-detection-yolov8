"""Verify locked pilot image bytes against their publisher-linked source archive.

This is a read-only integrity check. It never extracts archive members and does
not make any decision about image rights, reviewer assignment, or training use.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import struct
import sys
import zlib
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "datasets/candidates/construction-ppe-pilot-draft/pilot-rights-manifest-draft.csv"
DEFAULT_ROSTER = ROOT / "datasets/candidates/construction-ppe-pilot-draft/pilot-roster.csv"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
MEBIBYTE = 1024 * 1024
MAX_SOURCE_ARCHIVE_BYTES = 700 * MEBIBYTE
MAX_ARCHIVE_ENTRIES = 10_000
MAX_CENTRAL_DIRECTORY_BYTES = 16 * MEBIBYTE
MAX_MEMBER_UNCOMPRESSED_BYTES = 10 * MEBIBYTE
MAX_TOTAL_SELECTED_MEMBER_BYTES = 250 * MEBIBYTE


def sha256_stream(stream: BinaryIO, *, max_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    total_bytes = 0
    while True:
        read_size = 1024 * 1024
        if max_bytes is not None:
            read_size = min(read_size, max_bytes - total_bytes + 1)
        chunk = stream.read(read_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if max_bytes is not None and total_bytes > max_bytes:
            raise ValueError(f"Stream exceeds the {max_bytes}-byte verification limit")
        digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = set(reader.fieldnames or [])
        missing = required_columns - columns
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def preflight_zip_directory(path: Path) -> list[str]:
    """Bound ZIP central-directory metadata before zipfile builds an entry list."""
    eocd_signature = b"PK\x05\x06"
    eocd_min_size = 22
    max_comment_size = 65_535
    tail_size = eocd_min_size + max_comment_size
    try:
        with path.open("rb") as source:
            source.seek(0, 2)
            file_size = source.tell()
            source.seek(max(0, file_size - tail_size))
            tail = source.read(tail_size)
    except OSError as error:
        return [f"Could not inspect ZIP directory: {error}"]

    eocd_candidates: list[int] = []
    search_from = 0
    while True:
        candidate = tail.find(eocd_signature, search_from)
        if candidate < 0:
            break
        if len(tail) - candidate >= eocd_min_size:
            candidate_comment_size = struct.unpack_from("<H", tail, candidate + 20)[0]
            if candidate + eocd_min_size + candidate_comment_size == len(tail):
                eocd_candidates.append(candidate)
        search_from = candidate + len(eocd_signature)

    if not eocd_candidates:
        return ["ZIP end-of-central-directory record is missing or truncated"]
    if len(eocd_candidates) != 1:
        return ["ZIP end-of-central-directory record is ambiguous"]
    eocd_index = eocd_candidates[0]

    try:
        disk_number, directory_disk, disk_entries, total_entries, directory_size, directory_offset, comment_size = (
            struct.unpack_from("<4H2IH", tail, eocd_index + len(eocd_signature))
        )
    except struct.error as error:
        return [f"Could not read ZIP directory bounds: {error}"]

    eocd_end = eocd_index + eocd_min_size + comment_size
    if eocd_end != len(tail):
        return ["ZIP end-of-central-directory comment length is inconsistent"]
    if disk_number != 0 or directory_disk != 0 or disk_entries != total_entries:
        return ["Multi-disk ZIP archives are not supported"]
    if total_entries == 0xFFFF or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
        return ["ZIP64 source archives are not supported by this bounded verifier"]
    if total_entries > MAX_ARCHIVE_ENTRIES:
        return [f"Source archive exceeds the {MAX_ARCHIVE_ENTRIES}-entry limit"]
    if directory_size > MAX_CENTRAL_DIRECTORY_BYTES:
        return [f"ZIP central directory exceeds the {MAX_CENTRAL_DIRECTORY_BYTES}-byte limit"]

    eocd_absolute_offset = file_size - len(tail) + eocd_index
    if directory_offset + directory_size > eocd_absolute_offset:
        return ["ZIP central-directory bounds overlap the end record"]
    return []


def verify(archive_path: Path, manifest_path: Path, roster_path: Path) -> list[str]:
    problems: list[str] = []
    if not archive_path.is_file():
        return [f"Source archive not found: {archive_path}"]

    try:
        manifest_rows = load_rows(
            manifest_path,
            {"sha256", "source_archive_sha256", "archive_member"},
        )
        roster_rows = load_rows(roster_path, {"sha256"})
    except (OSError, ValueError, csv.Error) as error:
        return [str(error)]

    if not manifest_rows:
        problems.append("Rights manifest has no image rows")

    manifest_hashes = [row["sha256"].strip().lower() for row in manifest_rows]
    roster_hashes = [row["sha256"].strip().lower() for row in roster_rows]
    for label, hashes in (("manifest", manifest_hashes), ("roster", roster_hashes)):
        invalid = [value for value in hashes if not SHA256_PATTERN.fullmatch(value)]
        if invalid:
            problems.append(f"{label} contains {len(invalid)} invalid SHA-256 value(s)")
        if len(hashes) != len(set(hashes)):
            problems.append(f"{label} contains duplicate SHA-256 values")
    if set(manifest_hashes) != set(roster_hashes):
        problems.append("Rights-manifest SHA set does not match the locked pilot roster")

    expected_archive_hashes = {
        row["source_archive_sha256"].strip().lower() for row in manifest_rows
    }
    if len(expected_archive_hashes) != 1 or not all(
        SHA256_PATTERN.fullmatch(value) for value in expected_archive_hashes
    ):
        problems.append("Manifest must contain one valid source_archive_sha256 value")

    try:
        archive_size = archive_path.stat().st_size
        if archive_size > MAX_SOURCE_ARCHIVE_BYTES:
            return [f"Source archive exceeds the {MAX_SOURCE_ARCHIVE_BYTES}-byte limit"]
        with archive_path.open("rb") as source:
            actual_archive_hash = sha256_stream(source, max_bytes=MAX_SOURCE_ARCHIVE_BYTES)
    except OSError as error:
        return problems + [f"Could not read source archive: {error}"]
    except ValueError as error:
        return problems + [f"Could not hash source archive: {error}"]

    if expected_archive_hashes and actual_archive_hash not in expected_archive_hashes:
        problems.append("Source archive SHA-256 does not match the rights manifest")

    if problems:
        print(f"Source archive SHA-256: {actual_archive_hash}")
        print(f"Manifest rows: {len(manifest_rows)}; locked roster rows: {len(roster_rows)}")
        print("Archive members were not inspected because an archive/manifest preflight failed.")
        print("Rights-manifest hashes match locked roster: " + ("yes" if set(manifest_hashes) == set(roster_hashes) else "no"))
        return problems

    directory_problems = preflight_zip_directory(archive_path)
    if directory_problems:
        return directory_problems

    matched = 0
    missing = 0
    mismatched = 0
    invalid_members = 0
    seen_members: set[str] = set()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive_infos = archive.infolist()
            if len(archive_infos) > MAX_ARCHIVE_ENTRIES:
                return [f"Source archive exceeds the {MAX_ARCHIVE_ENTRIES}-entry limit"]

            requested_infos: dict[str, list[zipfile.ZipInfo]] = {}
            requested_members = {
                row["archive_member"].strip() for row in manifest_rows
            }
            for info in archive_infos:
                if info.filename in requested_members:
                    requested_infos.setdefault(info.filename, []).append(info)

            selected_infos: dict[str, zipfile.ZipInfo] = {}
            total_selected_bytes = 0
            for row_number, row in enumerate(manifest_rows, start=2):
                member = row["archive_member"].strip()
                expected_image_hash = row["sha256"].strip().lower()
                member_path = PurePosixPath(member)
                if (
                    not member
                    or "\\" in member
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or not SHA256_PATTERN.fullmatch(expected_image_hash)
                ):
                    invalid_members += 1
                    problems.append(f"Manifest row {row_number} has an unsafe/invalid member or image SHA")
                    continue
                if member in seen_members:
                    invalid_members += 1
                    problems.append(f"Manifest row {row_number} repeats archive member {member!r}")
                    continue
                seen_members.add(member)
                infos = requested_infos.get(member, [])
                if not infos:
                    missing += 1
                    problems.append(f"Manifest row {row_number}: archive member is missing: {member}")
                    continue
                if len(infos) != 1:
                    invalid_members += 1
                    problems.append(f"Manifest row {row_number}: archive has duplicate entries for {member}")
                    continue
                info = infos[0]
                if info.is_dir():
                    missing += 1
                    problems.append(f"Manifest row {row_number}: archive member is a directory: {member}")
                    continue
                if info.file_size > MAX_MEMBER_UNCOMPRESSED_BYTES:
                    invalid_members += 1
                    problems.append(f"Manifest row {row_number}: member exceeds the per-image size limit: {member}")
                    continue
                total_selected_bytes += info.file_size
                if total_selected_bytes > MAX_TOTAL_SELECTED_MEMBER_BYTES:
                    problems.append(
                        f"Selected archive members exceed the {MAX_TOTAL_SELECTED_MEMBER_BYTES}-byte total limit"
                    )
                    break
                selected_infos[member] = info

            if problems:
                return problems

            for row_number, row in enumerate(manifest_rows, start=2):
                member = row["archive_member"].strip()
                expected_image_hash = row["sha256"].strip().lower()
                info = selected_infos[member]
                with archive.open(info) as image_stream:
                    actual_image_hash = sha256_stream(
                        image_stream,
                        max_bytes=MAX_MEMBER_UNCOMPRESSED_BYTES,
                    )
                if actual_image_hash == expected_image_hash:
                    matched += 1
                else:
                    mismatched += 1
                    problems.append(f"Manifest row {row_number}: member SHA-256 mismatch: {member}")
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as error:
        problems.append(f"Could not inspect ZIP members: {error}")

    print(f"Source archive SHA-256: {actual_archive_hash}")
    print(f"Manifest rows: {len(manifest_rows)}; locked roster rows: {len(roster_rows)}")
    print(
        f"Member bytes matched: {matched}; missing: {missing}; mismatched: {mismatched}; "
        f"invalid/duplicate entries: {invalid_members}"
    )
    print("Rights-manifest hashes match locked roster: " + ("yes" if set(manifest_hashes) == set(roster_hashes) else "no"))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Publisher-linked source ZIP")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    args = parser.parse_args()

    problems = verify(args.archive, args.manifest, args.roster)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("SOURCE ARCHIVE INTEGRITY PASSED. This does not approve rights, provenance, reviewers, or training use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
