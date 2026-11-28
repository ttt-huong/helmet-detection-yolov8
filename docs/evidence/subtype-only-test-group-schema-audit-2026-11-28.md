# Static audit: subtype-only locked-test group metadata

> **Historical source snapshot:** the findings below describe the Notebook/API revision inspected for this audit, before later source changes to subtype-only group selection and rejection-gate validation. They are not the current code status and do not establish any model result. No qualifying dataset, checkpoint, or passing locked-test runtime result is available.

Date: 2026-11-28
Scope: static review of `dataset_image_sources.json` v4 generation and its Notebook 03 / API consumers. No data, code, or model was changed; no converter or training run was performed.

## Finding

The converter-generated v4 record contains enough **summary fields** to derive subtype-only candidate groups when the sidecar is trusted: image split and `group_id`, `scene_type`, surface inventory/types, and per-image counts for all eight review classes. The converter also checks the underlying v7 review before writing the sidecar.

The current Notebook 03 preflight does **not** enforce subtype-only eligibility. It counts every confirmed group tagged with a subtype when that subtype has any matching annotation count, even if the group also contains a hardhat, another worn subtype, or a depiction surface. Its summary and the API enforce subtype group-count floors, but the inspected code does not compute or gate the required zero false-hardhat boxes/groups on subtype-only locked-test groups. The existing code therefore cannot establish the rubric’s locked-test acceptance condition.

No generated `datasets/hardhat_only_v1/dataset_image_sources.json` or `datasets/hardhat_only_v1.zip` is currently present in this workspace, so this audit cannot identify or count actual eligible groups.

## v4 fields and converter checks

`scripts/convert_review_json_to_yolo.py:34-53` defines the eight review classes and the three project splits. At `:853-878`, the converter writes top-level `format="helmet-vision-image-sources-v4"`, `review_format="helmet-vision-review-v7"`, and an `images` array. Each image contains `image_id`, `file_name`, terminal `image_review_status`, the assignment fields (`split`, `group_id`, `scene_type`, `depiction_surface_types`, `depiction_surfaces`), `depiction_region_surfaces`, per-class `review_class_counts`, and `rights`.

The count map is a histogram of annotation class IDs (`:863-869`); it does not retain each annotation’s `review_state`, `counts_as_real_wearer`, or box. For a converter-produced archive, the earlier v7 checks provide important context: `:244-299` requires split/group/scene assignments and validates surface types against physical inventory; `:578-588` rejects non-clear frames and requires an explicit full-frame no-depicted-people review for `scene_type="other"`; annotation validation rejects uncertain and inconsistent headwear/source labels (`:655-740`). These source-review attestations are not serialized as individual fields in v4, so v4 alone cannot independently replay those checks.

The group/split fields are suitable for deduplicating by `(split, group_id)`. The converter validates that a group stays in one split; Notebook 03 also checks split-manifest assignments and rejects group IDs crossing splits (Notebook 03 cell 2, source lines 87-145). These checks validate consistency, not whether the human-created group IDs truly represent independent sources.

## Consumer gap

Notebook 03 cell 2 aggregates image `review_class_counts`, scene types, surfaces, and review status by group (source lines 115-185). It verifies the eight class-count keys, nonnegative integer counts, and consistency between counts and `image_review_status` (lines 163-178). It then derives expected subtype tags solely from whether each group’s summed `traffic_helmet_worn`, `cap_worn`, or `beanie_worn` count is greater than zero and checks that the sidecar tags match (lines 247-252). It does not require that the chosen subtype be the only worn subtype, that `hard_hat_worn` be absent, or that the group have no depiction surface / only `scene_type="other"`.

Notebook 03 cell 3 counts the tagged `(split, group_id)` records against the 300/30/100 floors (source lines 138-175). Its locked-test summary records subtype group counts and count-floor status (cell 11, source lines 560-570); the inspected code does not calculate per-subtype false-hardhat box/group counts on a subtype-only subset. `service/app.py:349-363` validates only the reported subtype group-count shape and floors. This is short of the acceptance definition in `configs/helmet_types_labeling.md:100-106`, which requires at least 100 independent subtype-only locked-test groups per subtype, zero predicted hardhat boxes and zero groups with a hardhat prediction, and excludes groups containing a hardhat, another worn subtype, or a depiction surface.

## Fields needed for an enforceable gate

For each subtype, a group-level eligibility selector can use trusted converter-produced v4 data to require: at least one reviewed worn instance of that subtype; zero `hard_hat_worn` count; zero counts for the other worn subtypes; no depiction surface in any group image; and unique `(test, group_id)` membership. The existing scene/surface fields support the no-depiction filter, while the count map supports the class-presence filters. The current consumer does not apply this selector, does not retain per-annotation confirmation evidence in v4, and does not evaluate zero false-hardhat predictions on the selected groups. Those gaps must be closed before the subtype-only test criterion can be certified.
