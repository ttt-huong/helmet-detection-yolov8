# Non-target hat rejection gate audit — 2026-11-28

> **Historical source snapshot:** this audit records the plan/release path before the later per-subtype rejection-gate changes. Its finding that no locked-test rejection gate existed applies to that earlier snapshot, not the current source contract. The added source gate is not proof of model behavior: dataset, checkpoint, and passing runtime test results are still absent.

## Finding

The hardhat-only output contract is clear: model class 0 is `hard_hat_worn`; traffic helmets, caps, and beanies are negative examples, not model classes. However, the current plan and release path **do not have a separate locked-test performance gate for rejecting each of those three subtypes**. They require subtype negative-group coverage, then gate deployment on other conditions. This proves examples were allocated; it does not prove the model avoids emitting `hard_hat_worn` on subtype-only images.

## Evidence checked

- **Plan and rubric:** The data plan says the target is `hard_hat_worn`, with traffic/cap/beanie as negatives, and sets 300/30/100 independent groups for each subtype. The labeling rubric says those hats are not exported as model classes and that subtype-only images can be empty YOLO examples. Neither specifies a per-subtype false-hardhat acceptance threshold.
- **Notebook 03:** Preflight counts subtype groups and blocks if a subtype is below the train/validation/locked-test floor. The locked-test release predicate checks class-box sufficiency, ≥100 hardhat ground-truth boxes, and the six poster/photo/screen × scene gates. The subtype data in `deployment_test_summary.json` is group counts and group-floor statuses; there is no per-subtype hardhat false-positive count or rejection status.
- **Standalone evaluator:** `scripts/evaluate_hat_types.py` reports overall hardhat class metrics and scene-group/surface gates. Its CLI takes the two-class `data.yaml` and optional scene-metadata CSV; it has no per-image subtype evaluation input. Its `deployment_gate_status` requires the six depiction gates and the hardhat ground-truth minimum, not a subtype rejection metric.
- **API:** `service/app.py` validates `hat_type_negative_group_counts` against 300/30/100 for each subtype. Its prediction/release validation checks the six depiction surface gates, but does not require subtype-specific false-positive statistics. `service/README.md` describes the same group floors and surface gates.

Thus, the hard-negative subtype is covered by a **data sufficiency gate only**, not a model rejection gate. Overall class FP metrics may expose false positives in reports, but they are not broken down by subtype and do not block release on this basis.

## Minimum plan change recommended

Add an explicit locked-test rejection gate for each of `traffic_helmet_worn`, `cap_worn`, and `beanie_worn`, separate from the existing group-count floors:

1. Define subtype-only locked-test images from reviewed per-image source metadata: the named subtype is confirmed present, no `hard_hat_worn` ground truth is present, no other worn-hat subtype is present, and the scene has no depiction surface. The existing `dataset_image_sources.json` v4 contains per-image review-class counts; group-level source tags alone are insufficient to identify these images safely.
2. Use the confidence threshold frozen on validation. For each subtype, report eligible image/group counts plus the number of `hard_hat_worn` prediction boxes and images with any such prediction. Require the existing ≥100 independent locked-test groups for that subtype and zero hardhat predictions on its eligible subtype-only test images if “must reject” is the acceptance rule.
3. Make Notebook 03 include the three per-subtype results in the locked-test summary and block the release receipt if any subtype is missing or has a false hardhat prediction. Require API release validation to check those per-subtype gates as well. Keep this performance gate distinct from the 300/30/100 source-group sufficiency counts.

If a nonzero false-positive allowance is preferred, the owner should set that threshold before examining locked-test results; the current documents do not define one.

## Static-review scope and references

No code, plan, or model artifact was changed or executed. References: [data completion plan](../ke_hoach_hoan_tat_du_lieu.md); [labeling rubric](../../configs/helmet_types_labeling.md); [Notebook 03](../../notebooks/03_train_hat_types_colab.ipynb), subtype-group preflight and locked-test release cells; [standalone evaluator](../../scripts/evaluate_hat_types.py); [API](../../service/app.py) and [deployment contract](../../service/README.md).
