# Notebook 03 subtype-rejection gate review — 2026-11-28

> **Historical source snapshot:** this review describes the Notebook 03 version inspected at the time. Later source changes added group-level subtype-only eligibility; retain the findings as audit history and re-check the current source before acting on them. Neither this code review nor the later gate code proves a model has passed or rejects non-target hats in runtime.

Static, read-only review of Notebook 03 cell 11 against `docs/evidence/non-target-gate-implementation-map-2026-11-28.md` and the subtype-only acceptance rule in `configs/helmet_types_labeling.md:100-106`. No notebook, service, evaluator, data, or model was changed. No tests or training were run.

## Findings

### [P1] Eligibility is per image, so a contaminated group can count as subtype-only

Cell 11’s `is_subtype_only_test_record` filters one v4 image record (`cell 11, source lines 241-250`). The prediction loop adds that image’s `group_id` to the eligible set and counts predictions only for that qualifying image (`371-380`). It never aggregates all records in a group before deciding eligibility.

If one locked-test `group_id` contains a qualifying traffic-helmet frame and another frame with a hardhat, another worn subtype, or a depiction surface, the first frame still contributes the group to the 100-group floor. Predictions from the contaminating frame are not included in that subtype’s false-box count. This is not a subtype-only **group** under the project rule. Exclude the whole group unless every image assigned to it satisfies that subtype’s eligibility predicate, and include predictions from every image admitted to that eligible group.

This follows the per-image wording of the implementation map, but the map’s final distinct-group count does not enforce group purity required by the acceptance definition.

### [P2] Source metadata mismatch is only partially checked before the gate

Cell 11 verifies the v4 format and that image IDs are unique and their `(split, group_id, scene_type)` assignments match the split manifest (`29-45`, `228-234`). The subtype predicate then trusts `review_class_counts` and checks only `depiction_surface_types == []` (`237-250`). It does not check the v4 `depiction_surfaces` inventory, compare v4 per-image scene/surface fields with `test_scene_metadata.csv`, or reconcile candidate `scene_type="other"` hardhat counts with that image’s YOLO target labels.

The Notebook 03 preflight validates the v4 `depiction_surface_types` list and count-map shape, but does not validate the v4 physical-surface inventory (`cell 2, source lines 163-178`). The separate scene CSV loader validates its own inventory, and the early cross-check compares surface-source types by group, not each v4 record to that CSV (`cell 4, source lines 168-261 and 272-285`). Thus a mismatched v4 record can still drive subtype eligibility even when the other per-image source representation disagrees. For example, a test record with `depiction_surfaces` nonempty but `depiction_surface_types=[]` passes the predicate if its counts otherwise qualify. The project map calls for missing/mismatched source records to block the gate; extend validation to require per-image agreement and consistent inventory/types before classification.

### [P2] Validation-threshold provenance is descriptive, not enforced

Cell 11 sets `CONFIDENCE_THRESHOLD = 0.25` in the locked-test cell (`source line 50`) and labels it “Freeze this using validation.” The summary records that value as `confidence_threshold_frozen_before_test` (`740`). The service requires each subtype gate threshold to equal the summary value (`service/app.py:287-312, 384-406`), but neither the notebook nor the service verifies a validation-selection artifact or immutable threshold declaration. The v9 contract can therefore prove threshold consistency, but not that the threshold was selected and locked before viewing locked-test results. Keep this as an evidence gap unless a separately controlled, pre-test threshold record is bound into the run.

## Checks that match the map

- The per-image class exclusions include hardhat, the other worn subtypes, bare head, depicted hat, loose hat, and depiction region; it requires a positive count for the subtype and `scene_type="other"` with no declared surface types (`cell 11, source lines 237-250`).
- It deduplicates qualifying IDs with a set, counts class-0 predictions at the configured hardhat confidence threshold, records affected images, and blocks a subtype unless it has at least 100 groups and zero boxes/images with predictions (`371-380, 650-683`).
- Missing/invalid reviewed scene metadata blocks the overall deployment path; missing or duplicate test image/source IDs and split/group/scene assignment mismatches raise before evaluation (`29-45, 228-234, 282-292, 711-717`).
- On failure, it keeps the timestamped diagnostic report while removing deployment summary/receipt files (`813-820`). On pass, it emits a v9 manifest with the three required subtype names and aggregate pass status; the summary hash binds per-subtype counts (`823-845`). `service/app.py` is aligned with the v9 contract and validates the per-subtype count/status fields and threshold equality (`67, 195-214, 380-410`).

## Scope note

The separate evaluator implementation was not reviewed in this pass. The implementation map treats it as a separate required surface; this Notebook 03 review does not establish evaluator parity.
