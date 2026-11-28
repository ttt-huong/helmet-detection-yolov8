"""Cloud inference API for the two-class hardhat checkpoint."""

from __future__ import annotations

from io import BytesIO
import hashlib
import json
import math
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel


CLASS_NAMES = {
    0: "hard_hat_worn",
    1: "depiction_region",
}


class HealthPayload(BaseModel):
    class_names: dict[str, str]
    wearer_count_policy: str
    depiction_filter: str


class HealthReadyResponse(HealthPayload):
    status: Literal["ready"]
    model_loaded: bool


class HealthUnavailableResponse(HealthPayload):
    status: Literal["model_not_loaded"]
    model_loaded: bool
    error_code: str
    error_message: str


WORN_CLASSES = {"hard_hat_worn"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
DEFAULT_CONFIDENCE = 0.25
MIN_MODEL_CONFIDENCE = 0.001
MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH = 100
MIN_CLASS_BOX_COUNTS = {
    "train": {"hard_hat_worn": 300, "depiction_region": 300},
    "val": {"hard_hat_worn": 1, "depiction_region": 1},
    "test": {"hard_hat_worn": 100, "depiction_region": 100},
}
MIN_HARD_NEGATIVE_GROUP_COUNTS = {"train": 300, "test": 100}
MIN_HAT_TYPE_NEGATIVE_GROUP_COUNTS = {"train": 300, "val": 30, "test": 100}
MIN_HAT_TYPE_NEGATIVE_VALIDATION_GROUPS = 30
MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS = 100
VALIDATION_THRESHOLD_EVIDENCE_FORMAT = "helmet-vision-validation-threshold-v1"
VALIDATION_THRESHOLD_METHOD = "minimum_threshold_above_max_hardhat_score_on_subtype_only_validation_groups_v1"
VALIDATION_THRESHOLD_MARGIN = 1e-6
REQUIRED_HARD_NEGATIVE_SOURCES = (
    "poster", "printed_photo", "screen", "loose_hat", "mixed_scene", "empty_background",
)
REPORTED_HAT_TYPE_NEGATIVE_SOURCES = (
    "traffic_helmet_worn", "cap_worn", "beanie_worn",
)
RELEASE_MANIFEST_FORMAT = "helmet-vision-model-release-v9"
REQUIRED_DEPICTION_SURFACE_TYPES = ("poster", "printed_photo", "screen")
REQUIRED_DEPICTION_SCENES = ("depiction_only", "mixed_scene")

_model: Any | None = None
_locked_confidence_threshold: float | None = None
_model_lock = Lock()


class ModelLoadError(RuntimeError):
    """A safe, structured reason that the cloud checkpoint is unavailable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.public_message = message

app = FastAPI(title="Helmet scene inference", version="0.1.0")
APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"
if not WEB_DIR.is_dir():
    WEB_DIR = APP_DIR.parent / "web"


def normalized_names(names: Any) -> dict[int, str]:
    if isinstance(names, list):
        return {index: name for index, name in enumerate(names)}
    if isinstance(names, dict):
        return {int(index): name for index, name in names.items()}
    raise ValueError("Checkpoint has no supported class-name mapping")


def checkpoint_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def validate_training_runtime(summary: dict[str, Any]) -> None:
    runtime = summary.get("training_runtime")
    required_fields = {"python", "torch", "torchvision", "torch_cuda", "ultralytics"}
    if (not isinstance(runtime, dict)
            or set(runtime) != required_fields
            or any(not isinstance(value, str) or not value.strip() for value in runtime.values())):
        raise ModelLoadError(
            "release_runtime_mismatch",
            "The locked-test summary is missing valid training runtime version metadata.",
        )

    try:
        import torch
        import torchvision

        installed_runtime = {
            "torch": str(torch.__version__),
            "torchvision": str(torchvision.__version__),
            "torch_cuda": str(torch.version.cuda or ""),
        }
        from importlib.metadata import version as distribution_version

        installed_runtime["ultralytics"] = distribution_version("ultralytics")
    except Exception as error:
        raise ModelLoadError(
            "release_runtime_mismatch",
            "Could not determine the installed Torch, Torchvision, CUDA, and Ultralytics versions.",
        ) from error

    mismatches = [
        f"{field}: trained={runtime[field]!r}, inference={installed_runtime[field]!r}"
        for field in ("torch", "torchvision", "torch_cuda", "ultralytics")
        if runtime[field] != installed_runtime[field]
    ]
    if mismatches:
        raise ModelLoadError(
            "release_runtime_mismatch",
            "The inference runtime differs from the cloud training runtime recorded in the locked-test summary.",
        )


def require_inference_gpu() -> None:
    try:
        import torch

        gpu_available = torch.cuda.is_available()
    except Exception as error:
        raise ModelLoadError(
            "inference_gpu_unavailable",
            "Could not verify CUDA GPU availability for inference.",
        ) from error
    if not gpu_available:
        raise ModelLoadError(
            "inference_gpu_unavailable",
            "A CUDA GPU is required for inference; expose the GPU to the container.",
        )


def validate_release_manifest(checkpoint: Path) -> dict[str, Any]:
    global _locked_confidence_threshold

    release_path = Path(
        os.environ.get("MODEL_RELEASE_PATH", str(checkpoint.with_name("deployment_release.json")))
    )
    if not release_path.is_file():
        raise ModelLoadError(
            "release_manifest_missing",
            "A deployment_release.json declaring passing reviewed gates for posters, printed photos, and screens is required.",
        )

    try:
        release = json.loads(
            release_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ModelLoadError(
            "release_manifest_invalid",
            "The deployment release manifest is unreadable or invalid.",
        ) from error

    expected_names = [CLASS_NAMES[index] for index in range(len(CLASS_NAMES))]
    if not isinstance(release, dict) or release.get("format") != RELEASE_MANIFEST_FORMAT:
        raise ModelLoadError(
            "release_manifest_invalid",
            "The deployment release manifest has an unsupported format.",
        )
    if release.get("class_names") != expected_names:
        raise ModelLoadError(
            "release_manifest_invalid",
            "The deployment release manifest does not match the configured two classes.",
        )
    if (release.get("required_hat_type_negative_sources") != list(REPORTED_HAT_TYPE_NEGATIVE_SOURCES)
            or release.get("hat_type_negative_rejection_gate_status") != "pass"):
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The deployment receipt does not attest passing traffic-helmet, cap, and beanie rejection gates.",
        )
    if (release.get("depiction_surface_gate_status") != "pass_reviewed_metadata"
            or release.get("required_depiction_surface_types") != list(REQUIRED_DEPICTION_SURFACE_TYPES)
            or release.get("scene_metadata_source") != "reviewed_metadata_csv"
            or release.get("data_sufficiency_gate_status") != "pass"):
        raise ModelLoadError(
            "release_gate_not_passed",
            "The deployment receipt does not declare passing reviewed-surface and data-sufficiency gates.",
        )

    expected_digest = release.get("checkpoint_sha256")
    dataset_digest = release.get("dataset_archive_sha256")
    summary_digest = release.get("test_summary_sha256")
    hard_negative_groups_digest = release.get("hard_negative_source_groups_sha256")
    validation_threshold_digest = release.get("validation_threshold_evidence_sha256")
    locked_test_marker_digest = release.get("locked_test_start_marker_sha256")
    digest_values = (
        expected_digest, dataset_digest, summary_digest, hard_negative_groups_digest,
        validation_threshold_digest, locked_test_marker_digest,
    )
    if (any(not isinstance(value, str) or len(value) != 64 for value in digest_values)
            or any(any(character not in "0123456789abcdefABCDEF" for character in value) for value in digest_values)):
        raise ModelLoadError(
            "release_manifest_invalid",
            "The deployment release manifest is missing valid checkpoint/data/test hashes.",
        )
    try:
        actual_digest = checkpoint_digest(checkpoint)
    except OSError as error:
        raise ModelLoadError(
            "checkpoint_load_failed",
            "Could not read the configured checkpoint file.",
        ) from error
    if actual_digest.casefold() != expected_digest.casefold():
        raise ModelLoadError(
            "release_checkpoint_hash_mismatch",
            "The checkpoint does not match the SHA-256 recorded in the deployment receipt.",
        )

    summary_path = Path(
        os.environ.get("MODEL_TEST_SUMMARY_PATH", str(checkpoint.with_name("deployment_test_summary.json")))
    )
    if not summary_path.is_file():
        raise ModelLoadError(
            "release_test_summary_missing",
            "The locked-test summary required by the deployment receipt is missing.",
        )
    try:
        summary_bytes = summary_path.read_bytes()
        summary = json.loads(
            summary_bytes.decode("utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ModelLoadError(
            "release_test_summary_invalid",
            "The locked-test summary required by the deployment receipt is unreadable or invalid.",
        ) from error
    actual_summary_digest = hashlib.sha256(summary_bytes).hexdigest()
    if actual_summary_digest.casefold() != summary_digest.casefold():
        raise ModelLoadError(
            "release_test_summary_hash_mismatch",
            "The locked-test summary does not match the SHA-256 in the deployment receipt.",
        )
    if not isinstance(summary, dict):
        raise ModelLoadError(
            "release_test_summary_invalid",
            "The locked-test summary root must be a JSON object.",
        )

    validate_training_runtime(summary)

    surface_gates = summary.get("depiction_surface_test_gates", {})
    summary_dataset_digest = summary.get("dataset_archive_sha256")
    summary_checkpoint_digest = summary.get("checkpoint_sha256")
    summary_hard_negative_groups_digest = summary.get("hard_negative_source_groups_sha256")
    hardhat_ground_truth_count = summary.get("locked_test_hardhat_ground_truth_count")
    hardhat_ground_truth_minimum = summary.get("minimum_locked_test_hardhat_ground_truth")
    box_counts = summary.get("class_box_counts_by_split")
    hard_negative_group_gates = summary.get("hard_negative_source_group_gates")
    hat_type_negative_counts = summary.get("hat_type_negative_group_counts")
    hat_type_rejection_gates = summary.get("hat_type_negative_rejection_gates")
    frozen_confidence_threshold = summary.get("confidence_threshold_frozen_before_test")
    if (summary.get("status") != "complete"
            or summary.get("deployment_gate_status") != "approved"
            or summary.get("data_sufficiency_gate_status") != "pass"
            or summary.get("scene_metadata_source") != "reviewed_metadata_csv"
            or summary.get("required_depiction_surface_types") != list(REQUIRED_DEPICTION_SURFACE_TYPES)
            or type(hardhat_ground_truth_count) is not int
            or hardhat_ground_truth_count < MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH
            or type(hardhat_ground_truth_minimum) is not int
            or hardhat_ground_truth_minimum != MIN_LOCKED_TEST_HARDHAT_GROUND_TRUTH
            or summary.get("hardhat_ground_truth_gate_status") != "pass"
            or hardhat_ground_truth_count != (
                box_counts.get("test", {}).get("hard_hat_worn")
                if isinstance(box_counts, dict) and isinstance(box_counts.get("test"), dict)
                else None
            )
            or not isinstance(summary_checkpoint_digest, str)
            or summary_checkpoint_digest.casefold() != actual_digest.casefold()
            or not isinstance(summary_dataset_digest, str)
            or summary_dataset_digest.casefold() != dataset_digest.casefold()
            or not isinstance(summary_hard_negative_groups_digest, str)
            or summary_hard_negative_groups_digest.casefold() != hard_negative_groups_digest.casefold()
            or summary.get("hat_type_negative_rejection_gate_status") != "pass"
            or type(frozen_confidence_threshold) not in (int, float)
            or not math.isfinite(frozen_confidence_threshold)
            or not MIN_MODEL_CONFIDENCE <= frozen_confidence_threshold <= 1
            or not isinstance(surface_gates, dict)):
        raise ModelLoadError(
            "release_test_summary_gate_mismatch",
            "The locked-test summary does not match the checkpoint/dataset or fails reviewed surface/hardhat gates.",
        )

    validation_evidence = summary.get("validation_threshold_evidence")
    summary_validation_digest = summary.get("validation_threshold_evidence_sha256")
    locked_test_marker = summary.get("locked_test_start_marker")
    summary_locked_test_marker_digest = summary.get("locked_test_start_marker_sha256")
    locked_test_started_at = summary.get("locked_test_started_at_utc")
    if (not isinstance(validation_evidence, dict)
            or not isinstance(summary_validation_digest, str)
            or summary_validation_digest.casefold() != validation_threshold_digest.casefold()
            or not isinstance(locked_test_marker, dict)
            or not isinstance(summary_locked_test_marker_digest, str)
            or summary_locked_test_marker_digest.casefold() != locked_test_marker_digest.casefold()
            or validation_evidence.get("format") != VALIDATION_THRESHOLD_EVIDENCE_FORMAT
            or validation_evidence.get("status") != "pass"
            or validation_evidence.get("selection_method") != VALIDATION_THRESHOLD_METHOD
            or validation_evidence.get("confidence_threshold") != frozen_confidence_threshold
            or validation_evidence.get("minimum_model_confidence") != MIN_MODEL_CONFIDENCE
            or validation_evidence.get("minimum_validation_groups_per_subtype") != MIN_HAT_TYPE_NEGATIVE_VALIDATION_GROUPS
            or validation_evidence.get("checkpoint_sha256") != expected_digest
            or validation_evidence.get("dataset_archive_sha256") != dataset_digest
            or validation_evidence.get("hard_negative_source_groups_sha256") != hard_negative_groups_digest):
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The release is missing validation threshold evidence bound to this checkpoint and dataset.",
        )
    try:
        canonical_validation_evidence = json.dumps(
            validation_evidence, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        actual_validation_digest = hashlib.sha256(canonical_validation_evidence).hexdigest()
        validation_created_at = datetime.fromisoformat(validation_evidence["created_at_utc"])
        locked_test_started = datetime.fromisoformat(locked_test_started_at)
        maximum_validation_score = validation_evidence.get(
            "maximum_validation_negative_hard_hat_confidence"
        )
        expected_frozen_threshold = (
            MIN_MODEL_CONFIDENCE
            if maximum_validation_score is None
            else min(1.0, max(MIN_MODEL_CONFIDENCE, maximum_validation_score + VALIDATION_THRESHOLD_MARGIN))
        )
        canonical_locked_test_marker = json.dumps(
            locked_test_marker, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        actual_locked_test_marker_digest = hashlib.sha256(canonical_locked_test_marker).hexdigest()
        marker_started_at = datetime.fromisoformat(locked_test_marker["started_at_utc"])
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The validation threshold evidence is malformed.",
        ) from error
    if (actual_validation_digest.casefold() != validation_threshold_digest.casefold()
            or actual_locked_test_marker_digest.casefold() != locked_test_marker_digest.casefold()
            or locked_test_marker.get("format") != "helmet-vision-locked-test-start-v1"
            or locked_test_marker.get("validation_threshold_evidence_sha256") != validation_threshold_digest
            or locked_test_marker.get("checkpoint_sha256") != expected_digest
            or locked_test_marker.get("dataset_archive_sha256") != dataset_digest
            or locked_test_marker.get("hard_negative_source_groups_sha256") != hard_negative_groups_digest
            or locked_test_marker.get("started_at_utc") != locked_test_started_at
            or validation_created_at.tzinfo is None
            or locked_test_started.tzinfo is None
            or marker_started_at.tzinfo is None
            or validation_created_at >= locked_test_started
            or marker_started_at != locked_test_started
            or type(maximum_validation_score) not in (int, float, type(None))
            or (maximum_validation_score is not None
                and (not math.isfinite(maximum_validation_score)
                     or not MIN_MODEL_CONFIDENCE <= maximum_validation_score <= 1))
            or expected_frozen_threshold > 1
            or expected_frozen_threshold != frozen_confidence_threshold):
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The validation threshold evidence hash, timestamp, or selection rule does not match the locked-test summary.",
        )
    for field in (
        "image_source_metadata_sha256", "split_manifest_sha256",
        "validation_images_and_labels_sha256",
    ):
        digest = validation_evidence.get(field)
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdefABCDEF" for character in digest)):
            raise ModelLoadError(
                "release_hat_type_rejection_gate_mismatch",
                "The validation evidence is missing valid hashes for reviewed metadata or validation inputs.",
            )
    validation_group_gates = validation_evidence.get("validation_group_gates")
    if (not isinstance(validation_group_gates, dict)
            or set(validation_group_gates) != set(REPORTED_HAT_TYPE_NEGATIVE_SOURCES)):
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The validation evidence is missing subtype-only group gates.",
        )
    for source in REPORTED_HAT_TYPE_NEGATIVE_SOURCES:
        gate = validation_group_gates.get(source)
        if (not isinstance(gate, dict)
                or set(gate) != {
                    "eligible_validation_image_count", "eligible_validation_group_count",
                    "minimum_validation_groups", "maximum_hard_hat_confidence_before_selected_threshold",
                    "hard_hat_prediction_box_count_at_selected_threshold",
                    "images_with_hard_hat_prediction_count_at_selected_threshold", "status",
                }
                or type(gate.get("eligible_validation_image_count")) is not int
                or type(gate.get("eligible_validation_group_count")) is not int
                or gate["eligible_validation_image_count"] < gate["eligible_validation_group_count"]
                or gate["eligible_validation_group_count"] < MIN_HAT_TYPE_NEGATIVE_VALIDATION_GROUPS
                or type(gate.get("minimum_validation_groups")) is not int
                or gate["minimum_validation_groups"] != MIN_HAT_TYPE_NEGATIVE_VALIDATION_GROUPS
                or type(gate.get("maximum_hard_hat_confidence_before_selected_threshold"))
                not in (int, float, type(None))
                or (gate["maximum_hard_hat_confidence_before_selected_threshold"] is not None
                    and (not math.isfinite(gate["maximum_hard_hat_confidence_before_selected_threshold"])
                         or not MIN_MODEL_CONFIDENCE <= gate["maximum_hard_hat_confidence_before_selected_threshold"]
                         < frozen_confidence_threshold))
                or type(gate.get("hard_hat_prediction_box_count_at_selected_threshold")) is not int
                or gate["hard_hat_prediction_box_count_at_selected_threshold"] != 0
                or type(gate.get("images_with_hard_hat_prediction_count_at_selected_threshold")) is not int
                or gate["images_with_hard_hat_prediction_count_at_selected_threshold"] != 0
                or gate.get("status") != "pass"):
            raise ModelLoadError(
                "release_hat_type_rejection_gate_mismatch",
                f"Validation threshold selection fails for {source}.",
            )

    if (not isinstance(box_counts, dict)
            or set(box_counts) != {"train", "val", "test"}
            or any(not isinstance(box_counts.get(split), dict)
                   or set(box_counts[split]) != set(CLASS_NAMES.values())
                   or any(type(box_counts[split].get(class_name)) is not int
                          or box_counts[split][class_name] < 0
                          for class_name in CLASS_NAMES.values())
                   for split in ("train", "val", "test"))
            or any(box_counts[split][class_name] < minimum
                   for split, class_counts in MIN_CLASS_BOX_COUNTS.items()
                   for class_name, minimum in class_counts.items())):
        raise ModelLoadError(
            "release_data_sufficiency_gate_mismatch",
            "The release summary does not meet the required train/validation/test box-count floors.",
        )

    if (not isinstance(hard_negative_group_gates, dict)
            or set(hard_negative_group_gates) != set(REQUIRED_HARD_NEGATIVE_SOURCES)):
        raise ModelLoadError(
            "release_data_sufficiency_gate_mismatch",
            "The release summary is missing one or more required hard-negative source group gates.",
        )
    for source in REQUIRED_HARD_NEGATIVE_SOURCES:
        gate = hard_negative_group_gates.get(source)
        if (not isinstance(gate, dict)
                or set(gate) != {
                    "train_group_count", "locked_test_group_count",
                    "minimum_train_groups", "minimum_locked_test_groups", "status",
                }
                or type(gate.get("train_group_count")) is not int
                or gate["train_group_count"] < MIN_HARD_NEGATIVE_GROUP_COUNTS["train"]
                or type(gate.get("locked_test_group_count")) is not int
                or gate["locked_test_group_count"] < MIN_HARD_NEGATIVE_GROUP_COUNTS["test"]
                or type(gate.get("minimum_train_groups")) is not int
                or gate["minimum_train_groups"] != MIN_HARD_NEGATIVE_GROUP_COUNTS["train"]
                or type(gate.get("minimum_locked_test_groups")) is not int
                or gate["minimum_locked_test_groups"] != MIN_HARD_NEGATIVE_GROUP_COUNTS["test"]
                or gate.get("status") != "pass"):
            raise ModelLoadError(
                "release_data_sufficiency_gate_mismatch",
                f"The release summary fails the independent-group floor for {source}.",
            )

    if (not isinstance(hat_type_negative_counts, dict)
            or set(hat_type_negative_counts) != set(REPORTED_HAT_TYPE_NEGATIVE_SOURCES)
            or any(not isinstance(hat_type_negative_counts.get(hat_type), dict)
                   or set(hat_type_negative_counts[hat_type]) != {"train", "val", "test"}
                   or any(type(hat_type_negative_counts[hat_type].get(split)) is not int
                          or hat_type_negative_counts[hat_type][split] < 0
                          for split in ("train", "val", "test"))
                   for hat_type in REPORTED_HAT_TYPE_NEGATIVE_SOURCES)
            or any(hat_type_negative_counts[hat_type][split] < minimum
                   for hat_type in REPORTED_HAT_TYPE_NEGATIVE_SOURCES
                   for split, minimum in MIN_HAT_TYPE_NEGATIVE_GROUP_COUNTS.items())):
        raise ModelLoadError(
            "release_data_sufficiency_gate_mismatch",
            "The release summary does not meet the independent-group floors for traffic-helmet, cap, and beanie negatives.",
        )

    if (not isinstance(hat_type_rejection_gates, dict)
            or set(hat_type_rejection_gates) != set(REPORTED_HAT_TYPE_NEGATIVE_SOURCES)):
        raise ModelLoadError(
            "release_hat_type_rejection_gate_mismatch",
            "The locked-test summary is missing one or more traffic-helmet, cap, and beanie rejection gates.",
        )
    for source in REPORTED_HAT_TYPE_NEGATIVE_SOURCES:
        gate = hat_type_rejection_gates.get(source)
        if (not isinstance(gate, dict)
                or set(gate) != {
                    "eligible_locked_test_image_count", "eligible_locked_test_group_count",
                    "minimum_locked_test_groups", "confidence_threshold",
                    "hard_hat_prediction_box_count", "images_with_hard_hat_prediction_count", "status",
                }
                or type(gate.get("eligible_locked_test_image_count")) is not int
                or gate["eligible_locked_test_image_count"] < 0
                or type(gate.get("eligible_locked_test_group_count")) is not int
                or gate["eligible_locked_test_group_count"] < MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS
                or gate["eligible_locked_test_image_count"] < gate["eligible_locked_test_group_count"]
                or type(gate.get("minimum_locked_test_groups")) is not int
                or gate["minimum_locked_test_groups"] != MIN_HAT_TYPE_NEGATIVE_REJECTION_GROUPS
                or type(gate.get("confidence_threshold")) not in (int, float)
                or not math.isfinite(gate["confidence_threshold"])
                or gate["confidence_threshold"] != frozen_confidence_threshold
                or type(gate.get("hard_hat_prediction_box_count")) is not int
                or gate["hard_hat_prediction_box_count"] != 0
                or type(gate.get("images_with_hard_hat_prediction_count")) is not int
                or gate["images_with_hard_hat_prediction_count"] != 0
                or gate.get("status") != "pass"):
            raise ModelLoadError(
                "release_hat_type_rejection_gate_mismatch",
                f"The locked-test summary fails the model rejection gate for {source}.",
            )

    for surface_type in REQUIRED_DEPICTION_SURFACE_TYPES:
        per_scene = surface_gates.get(surface_type)
        if not isinstance(per_scene, dict):
            raise ModelLoadError(
                "release_test_summary_gate_mismatch",
                "The locked-test summary does not include every required depiction surface.",
            )
        for scene_type in REQUIRED_DEPICTION_SCENES:
            gate = per_scene.get(scene_type)
            if (not isinstance(gate, dict)
                    or type(gate.get("image_count")) is not int
                    or gate["image_count"] <= 0
                    or type(gate.get("depiction_surface_instance_image_count")) is not int
                    or gate["depiction_surface_instance_image_count"] != gate["image_count"]
                    or type(gate.get("false_unverified_worn_candidates")) is not int
                    or gate["false_unverified_worn_candidates"] != 0
                    or gate.get("status") != "pass_reviewed_metadata"):
                raise ModelLoadError(
                    "release_test_summary_gate_mismatch",
            "The locked-test summary does not pass all poster/photo/screen gates with one reviewed region per declared physical surface instance.",
                )
    _locked_confidence_threshold = float(frozen_confidence_threshold)
    return release


def load_model() -> Any:
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        model_path = os.environ.get("MODEL_PATH", "").strip()
        if not model_path:
            raise ModelLoadError(
                "model_path_not_configured",
                "Set MODEL_PATH to the trained two-class hardhat checkpoint.",
            )
        checkpoint = Path(model_path)
        if not checkpoint.is_file():
            raise ModelLoadError(
                "checkpoint_missing",
                "The configured checkpoint file does not exist.",
            )

        validate_release_manifest(checkpoint)
        require_inference_gpu()

        try:
            from ultralytics import YOLO

            model = YOLO(str(checkpoint))
        except Exception as error:
            raise ModelLoadError(
                "checkpoint_load_failed",
                "Could not load the checkpoint or inference dependencies.",
            ) from error

        try:
            compatible = normalized_names(model.names) == CLASS_NAMES and model.task == "detect"
        except Exception as error:
            raise ModelLoadError(
                "checkpoint_incompatible",
                "Checkpoint must be a detection model with the configured two classes and class order.",
            ) from error
        if not compatible:
            raise ModelLoadError(
                "checkpoint_incompatible",
                "Checkpoint must be a detection model with the configured two classes and class order.",
            )

        _model = model
        return _model


def decode_image(raw: bytes, content_type: str | None) -> Any:
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Image must be at most {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB")
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")

    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")
            source_width, source_height = source.size
            if source_width <= 0 or source_height <= 0 or source_width * source_height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the 24-megapixel limit")
            oriented = ImageOps.exif_transpose(source)
            width, height = oriented.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the 24-megapixel limit")
            rgb = oriented.convert("RGB")
    except HTTPException:
        raise
    except Image.DecompressionBombError as error:
        raise HTTPException(status_code=413, detail="Image dimensions exceed the 24-megapixel limit") from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a readable image") from error

    import cv2
    import numpy as np

    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    return bgr


def box_area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def rectangle_union_area(boxes: list[list[float]]) -> float:
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


def depiction_overlap(first: list[float], regions: list[list[float]]) -> tuple[bool, float, list[list[float]]]:
    """Measure candidate coverage by the union of all depiction regions."""
    first_area = box_area(first)
    if first_area <= 0:
        return False, 0.0, []
    center_x = (first[0] + first[2]) / 2
    center_y = (first[1] + first[3]) / 2
    center_inside = any(
        region[0] <= center_x <= region[2] and region[1] <= center_y <= region[3]
        for region in regions
    )
    intersections = [
        [max(first[0], region[0]), max(first[1], region[1]),
         min(first[2], region[2]), min(first[3], region[3])]
        for region in regions
        if min(first[2], region[2]) > max(first[0], region[0])
        and min(first[3], region[3]) > max(first[1], region[1])
    ]
    coverage = rectangle_union_area(intersections) / first_area
    return center_inside, coverage, intersections


def extract_detections(result: Any, image_width: int, image_height: int) -> list[dict[str, Any]]:
    detections = []
    for row in result.boxes.data.tolist():
        x1, y1, x2, y2, confidence, class_id = map(float, row[:6])
        class_index = int(class_id)
        values = (x1, y1, x2, y2, confidence)
        if class_index not in CLASS_NAMES or not all(math.isfinite(value) for value in values):
            continue
        box = [
            max(0.0, min(float(image_width), x1)),
            max(0.0, min(float(image_height), y1)),
            max(0.0, min(float(image_width), x2)),
            max(0.0, min(float(image_height), y2)),
        ]
        if box_area(box) <= 0:
            continue
        detections.append({
            "class_id": class_index,
            "class_name": CLASS_NAMES[class_index],
            "confidence": confidence,
            "box_xyxy": box,
        })
    return detections


def apply_depiction_filter(
    detections: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    regions = [item for item in detections if item["class_name"] == "depiction_region"]
    candidates = []
    suppressed = []
    uncertain = []
    for item in detections:
        if item["class_name"] not in WORN_CLASSES:
            continue
        center_inside, coverage, intersections = depiction_overlap(
            item["box_xyxy"], [region["box_xyxy"] for region in regions]
        )
        if center_inside or coverage >= 0.5:
            suppressed.append({
                **item,
                "suppression_reason": (
                    "wearer_center_inside_depiction_region"
                    if center_inside else "at_least_half_of_wearer_box_covered_by_depiction_union"
                ),
                "depiction_region_intersections_xyxy": intersections,
                "wearer_box_coverage_by_depiction_union": coverage,
                "counted": False,
            })
            continue

        if coverage > 0:
            uncertain.append({
                **item,
                "source_status": "uncertain_partial_depiction_overlap",
                "depiction_region_intersections_xyxy": intersections,
                "wearer_box_coverage_by_depiction_union": coverage,
                "counted": False,
            })
        else:
            candidates.append({**item, "source_status": "unverified", "counted": False})
    return candidates, suppressed, uncertain


@app.get("/livez")
def livez() -> dict[str, str]:
    """Report that the ASGI process can serve requests; this is not model readiness."""
    return {"status": "alive"}


@app.get(
    "/health",
    response_model=HealthReadyResponse,
    responses={503: {"model": HealthUnavailableResponse}},
)
def health() -> HealthReadyResponse | JSONResponse:
    try:
        load_model()
        require_inference_gpu()
    except ModelLoadError as error:
        return JSONResponse(
            status_code=503,
            content=jsonable_encoder(HealthUnavailableResponse(
                status="model_not_loaded",
                model_loaded=False,
                error_code=error.code,
                error_message=error.public_message,
                class_names={str(class_id): name for class_id, name in CLASS_NAMES.items()},
                wearer_count_policy="zero_until_scene_source_review",
                depiction_filter=(
                    "suppress_center_inside_or_at_least_half_covered; "
                    "smaller_positive_overlap_is_uncertain; zero_overlap_is_unverified"
                ),
            )),
        )

    return HealthReadyResponse(
        status="ready",
        model_loaded=True,
        class_names={str(class_id): name for class_id, name in CLASS_NAMES.items()},
        wearer_count_policy="zero_until_scene_source_review",
        depiction_filter=(
            "suppress_center_inside_or_at_least_half_covered; "
            "smaller_positive_overlap_is_uncertain; zero_overlap_is_unverified"
        ),
    )


@app.post("/predict")
async def predict(image: UploadFile = File(...), confidence: float = DEFAULT_CONFIDENCE) -> dict[str, Any]:
    if not 0.01 <= confidence <= 1.0:
        raise HTTPException(status_code=422, detail="Confidence must be between 0.01 and 1.00")

    try:
        model = load_model()
        require_inference_gpu()
    except ModelLoadError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": error.code, "message": error.public_message},
        ) from error

    if _locked_confidence_threshold is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "release_threshold_unavailable",
                "message": "The validated release confidence threshold is unavailable.",
            },
        )
    confidence = max(confidence, _locked_confidence_threshold)

    raw = await image.read(MAX_UPLOAD_BYTES + 1)
    frame = decode_image(raw, image.content_type)
    image_height, image_width = frame.shape[:2]

    try:
        with _model_lock:
            result = model.predict(
                source=frame,
                imgsz=640,
                conf=MIN_MODEL_CONFIDENCE,
                device=0,
                verbose=False,
            )[0]
    except Exception as error:
        raise HTTPException(status_code=500, detail="Model inference failed") from error

    detections = extract_detections(result, image_width, image_height)
    depiction_regions = [
        item for item in detections
        if item["class_name"] == "depiction_region" and item["confidence"] >= MIN_MODEL_CONFIDENCE
    ]
    displayed = [
        item for item in detections
        if item["confidence"] >= confidence or item["class_name"] == "depiction_region"
    ]
    raw_candidates = [item for item in detections if item["class_name"] in WORN_CLASSES and item["confidence"] >= confidence]
    raw_for_filter = [*raw_candidates, *depiction_regions]
    candidates, suppressed, uncertain = apply_depiction_filter(raw_for_filter)
    uncertain_by_box = {tuple(item["box_xyxy"]): item for item in uncertain}
    candidate_by_box = {tuple(item["box_xyxy"]): item for item in candidates}
    effective = []
    for item in displayed:
        if item["class_name"] in WORN_CLASSES:
            key = tuple(item["box_xyxy"])
            if key in uncertain_by_box:
                effective.append(uncertain_by_box[key])
            elif key in candidate_by_box:
                effective.append(candidate_by_box[key])
            continue
        effective.append(item)

    return {
        "image": {"width": image_width, "height": image_height},
        "confidence_threshold": confidence,
        "detections": effective,
        "raw_detections_for_review": detections,
        "suppressed_wearer_candidates": suppressed,
        "uncertain_wearer_candidates": uncertain,
        "wearer_candidates_for_review": candidates,
        "wearer_count": 0,
        "review_required": True,
        "review_reason": "scene_source_not_verified",
        "source_status": "unverified",
        "policy": {
            "depiction_regions_detected": len(depiction_regions),
            "center_inside_depiction_region": "suppressed",
            "minimum_depiction_region_coverage_for_suppression": 0.5,
            "coverage_definition": "union_of_depiction_region_intersections_divided_by_worn_box_area",
            "smaller_positive_overlap": "uncertain_and_not_counted",
            "zero_overlap": "unverified_and_not_counted",
            "automatic_wearer_count": 0,
            "limitation": (
                "A missed or borderless poster, photograph, or screen cannot be ruled out by this detector alone. "
                "Inspect every unverified wearer candidate in the full scene before counting it. "
                "Partial overlap with a depiction region is marked uncertain; a candidate is never auto-counted."
            ),
        },
    }


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
