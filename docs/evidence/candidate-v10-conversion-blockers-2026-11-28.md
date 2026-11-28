# Candidate v10 — conversion blockers and required inputs

## Scope

Read-only trace of `scripts/convert_review_json_to_yolo.py` and `scripts/validate_hat_dataset.py` against `datasets/candidates/construction-ppe-review-batch/candidate-review-v10-adjudicated-proposal.json` and its current image/rights metadata. The converter was **not run**; no data or labels were changed and no training was run. The existing [v9 conversion blocker report](candidate-v9-conversion-blockers-2026-11-28.md) is preserved.

## Current v10 state

- 19 images, 78 annotations: 65 `hard_hat_worn`, 4 `cap_worn`, 8 `bare_head`, 1 `loose_hat`, and 0 `depiction_region`; 77 annotations are confirmed and 1 is uncertain.
- All 19 `group_id` and project `split` fields are blank. The `train`/`val` labels in the source archive are source-archive splits, not project assignments.
- All images declare `scene_type=other`; no image declares a depiction surface or region.
- One boxed `bare_head` annotation in image #5 has `review_state=uncertain`. Four additional heads remain unboxed and uncertain: image #1, two candidates in #5, and the small person in #16. The converter can reject the explicit uncertain box, but it cannot discover the four unboxed candidates from JSON.
- Rights metadata declares `training_use=approved`, `basis=permission`, and a non-empty `source_reference` for each image. `license_id` and `attribution` are blank. The converter accepts this field combination for `basis=permission`; that code check does not independently verify source provenance, rights-holder authority, attribution/privacy, or the underlying permission.

## Invocation preconditions and data-check order

Invoke with a new `--output-dir` outside `--images-dir`. This is a required invocation precondition, but `main()` checks it after loading the review and assignments, then validating rights and resolving source images. Thus the first v10 data blockers are the blank split and group assignment below; the containment check follows them. `publish()` then rejects any existing output target before staging data or calling `write_dataset()`. No conversion command was issued, so no output path was created or tested.

The v10 data checks, in call order, are:

1. `load_review()` accepts v10’s `helmet-vision-review-v7` format, exact eight-class mapping, and unique image IDs.
2. `load_embedded_assignments()` is the first current data blocker. For image #1, `split=''` fails first because `validate_assignment()` requires `train`, `val`, or `test`. After split is populated, the same record’s blank `group_id` fails next. Every image needs an evidence-based project split and non-empty group ID; all members of a group must remain together in one split.
3. After assignments, `load_embedded_rights()` accepts the current permission-basis declarations because `training_use=approved`, `basis=permission`, and `source_reference` are present. It would require `license_id` and `attribution` if the basis were `license`. Project readiness still requires the unresolved source/right-holder/privacy evidence to be established.
4. `resolve_source_images()` checks the original images. Current hash checks cover all 19 files.
5. With assignments, rights, source images, and a valid new output path in place, per-image validation in `write_dataset()` reaches the explicit uncertain annotation in image #5 and rejects it because `review_state` is uncertain. The four unboxed uncertain heads are separate review-completeness blockers that the converter cannot infer from v10.
6. Only after per-image validation completes does `write_dataset()` require all three splits to be non-empty, at least one `depiction_only` and one `mixed_scene` image in locked test, and both model classes (`hard_hat_worn`, `depiction_region`) to have boxes in train and validation. Current v10 has only `other` scenes and no `depiction_region` boxes, so it cannot meet these requirements.

## Validator and release gates after conversion

`scripts/validate_hat_dataset.py` checks `data.yaml` class names/paths, image and label files for each split, valid boxes, no duplicate image IDs across splits, and presence of both classes in train and validation. It does not independently validate rights, group evidence, source-group tags, or depiction sidecars; the Colab preflight and release gates perform those checks.

The batch is also far below the plan quotas. The CSV inventory has **0/33 quota gates met** (33 quota rows plus one excluded discovery-lead row). CAP and SALSA were added separately to the public-source review as discovery leads only; neither was added to the CSV or counted toward quota. V10’s 65 hardhat annotations are not yet allocated to project splits; it has only four cap boxes, no traffic-helmet or beanie examples, no depiction regions, and no verified independent groups. It is therefore not a plan-compliant training or release dataset, even after code-level conversion blockers are resolved.

## Artifacts needed to resume conversion and Colab staging

Before conversion:

- A finalized v7-format review JSON with valid project `split` and `group_id` for all images, no unresolved/uncertain annotations, complete review of the four unboxed candidates, and retained per-image source/right declarations.
- The matching original JPEG directory. Current source hash checks cover the 19 files; preserve those bytes or refresh the source index if files change.
- A new output directory outside the source-image directory. It must not already exist.

On successful conversion, the converter writes:

- A dataset directory containing `data.yaml`, split `images/` and `labels/`, `split_manifest.csv`, and `dataset_image_sources.json` v4.
- A sibling dataset ZIP.
- `test_scene_metadata.csv` with columns `image_id`, `scene_type`, `depiction_surface_types`, `depiction_surfaces`, and `depiction_region_surfaces`.
- A pending `<output-dir-name>_hard_negative_source_groups.csv` template with columns `split`, `group_id`, `review_status`, `hard_negative_sources`, and `hat_type_negative_sources`. Every group must be reviewed and confirmed; the template must be completed and staged under the Colab input name `hard_negative_source_groups.csv`.

Before Colab preflight, stage the same-run inputs in Drive under the expected names: `datasets/hardhat_only_v1.zip`, `datasets/test_scene_metadata.csv`, and `datasets/hard_negative_source_groups.csv`. The scene sidecar must cover each test image and keep each declared display surface mapped one-to-one to a `depiction_region`; the source-group sidecar must provide reviewed group tags. Then run the dataset validator and notebook preflight. These steps prepare the future run; they do not substitute for the missing 33 quota gates or the remaining provenance/group evidence.
