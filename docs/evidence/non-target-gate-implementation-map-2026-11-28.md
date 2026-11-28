# Non-target hat rejection gate implementation map — 2026-11-28

> **Historical design proposal:** statements about existing code below describe the source state when this map was drafted. Later source changes added subtype-only group rejection gates; this proposal is not evidence that a dataset or model has passed them.

## Proposed eligibility and metric

Use the locked-test `dataset_image_sources.json` v4 records as per-image reviewed evidence; they already carry `split`, `group_id`, `scene_type`, surface types, and `review_class_counts`. Do not derive subtype truth from the two-class YOLO labels or from group-level tags alone.

For subtype `S` in `{traffic_helmet_worn, cap_worn, beanie_worn}`, an eligible image is in `test`, has `scene_type=other` and no depiction surfaces, has `review_class_counts[S] > 0`, and has zero counts for `hard_hat_worn`, the other two worn-hat subtypes, `bare_head`, `depicted_hat`, `loose_hat`, and `depiction_region`. Count distinct `group_id`s among eligible images. At the locked-test confidence threshold already frozen on validation, count every emitted class-0 `hard_hat_worn` box on eligible images as a false hardhat prediction. Require at least 100 eligible independent test groups per subtype and zero false hardhat boxes for each. Keep the existing 300/30/100 group sufficiency gate separate.

## Field map

| Layer/file | Add or change | Gate behavior |
|---|---|---|
| `scripts/evaluate_hat_types.py` | Load/cross-check per-image `dataset_image_sources.json` metadata for test image IDs and group IDs. Add `hat_type_negative_rejection_gates` to `summary.json`; optionally write `hat_type_negative_rejection_metrics.csv`. Per-subtype fields: `eligible_locked_test_image_count`, `eligible_locked_test_group_count`, `minimum_locked_test_groups`, `confidence_threshold`, `hard_hat_prediction_box_count`, `images_with_hard_hat_prediction_count`, `status`. Add aggregate `hat_type_negative_rejection_gate_status`. | Mark each subtype `pass` only when eligible group count ≥100 and both false-prediction counts are zero; otherwise `blocked`. A missing/mismatched per-image source record blocks this gate. The evaluator currently reports overall class metrics and surface gates but takes no subtype metadata input and does not gate this result. |
| `notebooks/03_train_hat_types_colab.ipynb` | In the locked-test cell, calculate the same per-subtype fields from the already loaded source metadata and test predictions. Include the details and aggregate status in `deployment_test_summary.json`. Include subtype gate failures in `deployment_gate_reasons` and in the `deployment_gate_status` predicate. | Do not write `deployment_release.json` when any subtype is missing, has <100 eligible independent groups, or has a false class-0 prediction. Keep diagnostic test outputs. Existing `hat_type_negative_group_gates` continue to represent only data sufficiency. |
| Receipt / summary contract | Bump receipt format to `helmet-vision-model-release-v9`. Add `required_hat_type_negative_sources` with the exact three subtype names and `hat_type_negative_rejection_gate_status: "pass"` to `deployment_release.json`. Keep the full per-subtype counts in the summary; the receipt’s existing `test_summary_sha256` binds them. | V8 receipts cannot attest this new condition and should not bypass the v9 gate. No separate subtype digest is needed if the summary hash is checked as today. |
| `service/app.py` | Change `RELEASE_MANIFEST_FORMAT` to v9. In release validation, require the exact source list and aggregate pass status, then require all three summary entries, exact threshold consistency with the frozen test threshold, ≥100 eligible unique groups, zero false boxes/images, and matching computed status. Use a specific error such as `release_hat_type_rejection_gate_mismatch`. | Fail closed before model load. `/health` must return 503 when the gate is absent/blocked; `POST /predict` must not serve predictions. `/livez` remains process liveness only. |

The existing `hat_type_negative_group_counts` remains a separate count-only field: it proves there are enough confirmed source groups, not that the model rejects their hats. The overall `class_metrics_after_wearer_filter` may show aggregate false positives but cannot substitute for the three subtype-specific gates.

## Test scope for implementation

- **Eligibility/evaluator:** exercise each subtype independently; require 100 unique eligible groups; verify zero predictions passes, one class-0 box fails only that subtype, and missing metadata, duplicate/mismatched image IDs, insufficient eligible groups, a hardhat-positive image, another worn-hat subtype, or a depiction surface cannot silently enter the subtype-only subset.
- **Notebook release gate:** a synthetic test fixture with all three subtype gates passing may produce a v9 summary/receipt; make each subtype fail in turn and verify no receipt is produced while diagnostics remain.
- **API contract/routes:** valid v9 receipt + summary loads; reject v8 format, absent/wrong subtype list, missing subtype stats, threshold mismatch, fewer than 100 groups, nonzero box/image count, false status, or summary hash mismatch. Exercise `/health` and `/predict` to confirm fail-closed behavior before inference.

## Existing code touchpoints

- Notebook: cell 2 validates source metadata; cell 3 counts `hat_type_negative_group_counts`; cell 11 computes locked-test and depiction-surface gates.
- Evaluator: `scripts/evaluate_hat_types.py` currently emits `class_metrics_after_wearer_filter`, `scene_groups`, and `depiction_surface_test_gates`; its CLI has no subtype source input.
- API: `service/app.py::validate_release_manifest` checks group floors and the six surface gates; `/health` and `/predict` call the model-loading path that validates the release.
- Current release format is v8. `service/README.md` documents only subtype group floors, not subtype rejection performance.

This is a design note only. No code, plan, tests, or release artifacts were changed or run.
