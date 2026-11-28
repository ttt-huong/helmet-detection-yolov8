# Quota reconciliation — 2026-11-28

## Result

The floors in the plan, the checklist’s “valid quota = 0” statement, and the readiness inventory reconcile. The CSV contains 33 quota rows plus one explicitly excluded upstream discovery lead. Every quota row is `not met`, has `eligible_current=0`, and has `remaining` equal to its full minimum.

The public-source review subsequently added CAP and SALSA as discovery-only leads; they were not staged or added to any quota row. The current result remains **0/33 quota gates met**.

## Floors by unit and split

| Requirement | Unit | Train floor | Validation floor | Locked-test floor | Current eligible |
|---|---|---:|---:|---:|---:|
| `hard_hat_worn` | YOLO box | 300 | 1 | 100 | 0 / 0 / 0 |
| `depiction_region` | YOLO box | 300 | 1 | 100 | 0 / 0 / 0 |
| Each of `traffic_helmet_worn`, `cap_worn`, `beanie_worn` | Independent confirmed wearer group, per subtype | 300 | 30 | 100 | 0 / 0 / 0 per subtype |
| Each of `poster`, `printed_photo`, `screen`, `loose_hat`, `mixed_scene`, `empty_background` | Independent source group, per source | 300 | — | 100 | 0 / — / 0 per source |

The six locked-test strata each require one reviewed project image with a valid 1:1 physical-surface to `depiction_region` mapping:

| Stratum | Floor | Current eligible |
|---|---:|---:|
| `poster × depiction_only` | 1 image + valid mapping | 0 |
| `poster × mixed_scene` | 1 image + valid mapping | 0 |
| `printed_photo × depiction_only` | 1 image + valid mapping | 0 |
| `printed_photo × mixed_scene` | 1 image + valid mapping | 0 |
| `screen × depiction_only` | 1 image + valid mapping | 0 |
| `screen × mixed_scene` | 1 image + valid mapping | 0 |

Interpretation: the plan’s 100 `hard_hat_worn` test-box floor and the checklist’s separate wording requiring at least 100 ground-truth `hard_hat_worn` test boxes appear to describe the same locked-test minimum, not 200 boxes. The documents do not define them as additive. The six image strata are a separate coverage gate. The source-group table has no validation floor; `—` is intentional.

## What is not countable yet

- The latest [19-image v10 proposal](../../datasets/candidates/construction-ppe-review-batch/candidate-review-v10-adjudicated-proposal.json) has 78 annotations: 65 `hard_hat_worn`, 4 `cap_worn`, 8 `bare_head`, and 1 `loose_hat` (77 confirmed, 1 uncertain). Four additional unboxed head candidates (#1, both candidates in #5, and #16) remain uncertain. All 19 project `group_id` and `split` fields are blank; the source archive split does not allocate project groups. EXIF/JPEG-marker scans found no capture-time, camera, or group metadata in the 1,000-image construction archive or 19-image batch. Therefore the v10 batch contributes zero to every quota. Four `cap_worn` boxes do not establish four independent wearer groups, and the loose-hat box does not establish a project source group.
- The v7 candidate has no `depiction_region` boxes or physical-surface inventory. The v8/v9 `bare_head` additions are proposals and do not count toward the hardhat-only YOLO class floor.
- The checklist’s synthetic browser matrix demonstrates UI/schema behavior only. It does not count as reviewed locked-test images or valid project mappings for the six strata.
- The inventory’s public archive lead (800 train images, 200 validation images, 1,576 generic `helmet` boxes) is explicitly not a project quota: it has no subtype distinction, project group allocation, or independent locked test. The 175-image AI pilot is review evidence, not a split/group allocation.

## Evidence checked

- [Completion plan](../ke_hoach_hoan_tat_du_lieu.md), especially “Ngưỡng dữ liệu và bàn giao Colab”.
- [Validation checklist](../checklist_kiem_thu.md), especially “Mức đủ dữ liệu theo kế hoạch” and the six locked-test strata.
- [Readiness gap inventory](data_readiness_gap_inventory_2026-11-28.csv): 33 quota rows and one discovery-lead row.

This was a read-only reconciliation. No inventory, split, group, annotation, or review JSON was changed.
