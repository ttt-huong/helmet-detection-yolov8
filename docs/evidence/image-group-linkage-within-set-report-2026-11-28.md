# Within-set image group-linkage evidence — 2026-11-28

Read-only diagnostic for the 175 locked originals and the 19 reviewed candidate JPEGs. No annotation, roster, rights/provenance field, `group_id`, or split was changed. The grouping rule follows [the project labeling definition](../../configs/helmet_types_labeling.md): shared traceable person, video/session/scene, poster or screen content, original image/derivative, and indirect links belong together; missing evidence keeps independence unresolved.

## Scope and integrity

- The 175 JPEGs were read from `datasets/candidates/construction-ppe-pilot-draft/construction-ppe-pilot-review-package-locked.zip`. All 175 computed SHA-256 values and dimensions matched the locked roster. The existing [19×175 report](image-overlap-19x175-report-2026-11-28.md) records the package digest and prior cross-set comparison; **this work did not recompute cross-set pairs**.
- The 19 JPEGs were read from `datasets/candidates/construction-ppe-review-batch/`; all 19 SHA-256 values and dimensions matched `source_index.csv`.
- This report compares only unordered pairs within each set. The exhaustive hashes and distances are in [the CSV](image-group-linkage-within-set-2026-11-28.csv).

## Hash results

| Set | Images | Within-set pairs | Exact SHA-256 pairs | pHash ≤8/64 | dHash ≤8/64 | Closest pHash | Closest dHash |
|---|---:|---:|---:|---:|---:|---:|---:|
| Locked originals | 175 | 15,225 | 0 | 0 | 0 | 14/64 | 11/64 |
| Reviewed candidates | 19 | 171 | 0 | 0 | 0 | 18/64 | 20/64 |

The per-image byte hashes were all unique within each set. The screening rule marks a pair if **either** perceptual distance is ≤8; there were no flagged pairs.

## Method

- SHA-256 was computed over the original JPEG bytes.
- pHash: EXIF orientation normalized, grayscale, Lanczos resize to 32×32, orthonormal 2-D DCT, top-left 8×8 coefficients thresholded at their median; 64-bit Hamming distance.
- dHash: EXIF orientation normalized, grayscale, Lanczos resize to 9×8, horizontal adjacent-pixel comparisons; 64-bit Hamming distance.
- The ≤8-bit thresholds match the existing cross-set report and are screening heuristics, not calibrated probabilities.
- Visual review was limited to the union of the five lowest-distance pairs by pHash and five by dHash in each set (deduplicated): 9 locked-set pairs and 10 candidate-set pairs. No other pair was visually adjudicated.

## Closest-pair visual evidence

“No visible link” below describes only the inspected full-frame images. It does not establish that two images depict different people or independent groups.

| Pair | Files | pHash / dHash | Visual observation |
|---|---|---:|---|
| L01 | `batch-01/session-01/ultralytics-ppe-nov2026-159.jpg` ↔ `batch-02/session-01/ultralytics-ppe-nov2026-600.jpg` | 14 / 20 | Different outdoor worksite compositions with workers in common PPE; no distinctive person, capture, poster, or screen continuity is visible. |
| L02 | `batch-06/session-02/ultralytics-ppe-nov2026-669.jpg` ↔ `batch-08/session-02/ultralytics-ppe-nov2026-631.jpg` | 26 / 11 | Construction worker in a doorway versus a person in a plain indoor room; no visible shared person, scene, poster, or video cue. |
| L03 | `batch-06/session-01/ultralytics-ppe-nov2026-385.jpg` ↔ `batch-07/session-01/ultralytics-ppe-nov2026-485.jpg` | 16 / 13 | Similar orange forklift type, but the solar-panel yard and building frontage differ; equipment similarity alone does not establish a linked scene. |
| L04 | `batch-01/session-01/ultralytics-ppe-nov2026-285.jpg` ↔ `batch-06/session-01/ultralytics-ppe-nov2026-385.jpg` | 14 / 26 | Orange forklift photographed against greenhouse glazing versus solar panels. Vehicle type and viewpoint are similar, but backgrounds differ; same equipment is only a possibility, not a group link. |
| L05 | `batch-02/session-01/ultralytics-ppe-nov2026-490.jpg` ↔ `batch-04/session-01/ultralytics-ppe-nov2026-626.jpg` | 18 / 13 | Both show a similar older worker in a white hard hat and orange vest handling lumber beside an orange forklift. This is a plausible recurring-person/task lead; exact person, session, and capture relationship are unverified. |
| L06 | `batch-02/session-01/ultralytics-ppe-nov2026-097.jpg` ↔ `batch-02/session-01/ultralytics-ppe-nov2026-446.jpg` | 16 / 15 | Timber-frame interior with several workers versus a separate worker with a toolbox near machinery; no visible shared person or scene cue. |
| L07 | `batch-01/session-01/source-5fae4385b524dc38fa23bc4423a17c29.jpg` ↔ `batch-02/session-01/source-a36439d05ebf0f383997aed40d295074.jpg` | 28 / 14 | Both show high-angle warehouse aisles and small workers, but rack geometry and aisle layouts differ; warehouse-type similarity only. |
| L08 | `batch-03/session-01/source-2e27333e41769f0937c3111892af7957.jpg` ↔ `batch-05/session-01/source-d9f9c995d964d8a06df134b5637ad554.jpg` | 16 / 15 | Both depict stocked warehouses and forklifts, but inventory, layout, equipment, and camera angle differ; no clear shared person or capture cue. |
| L09 | `batch-04/session-01/ultralytics-ppe-nov2026-685.jpg` ↔ `batch-09/session-01/ultralytics-ppe-nov2026-601.jpg` | 30 / 14 | Forklift indoors versus a worker at an electrical cabinet; no visible shared person, scene, poster, or video cue. |
| C01 | `train_source-0271ab991bd2c3900528907e5ab2fa2c.jpg` ↔ `train_source-078aa002dcdc9f8ffd092bed4da44e59.jpg` | 18 / 25 | Group at a ground-mounted solar array versus a worker on a rooftop; common construction PPE only, with no clear person or scene continuity. |
| C02 | `train_source-04c535fcc25148fcc46c3e4d36902d57.jpg` ↔ `train_source-122e66278827dc8846c75fb8c7a7a01b.jpg` | 32 / 20 | Warehouse aisle versus a lone worker outdoors in muddy rows; no visible shared scene/person cue. |
| C03 | `train_source-0271ab991bd2c3900528907e5ab2fa2c.jpg` ↔ `train_source-0e59077ef44d89df66fa8b340b15aca0.jpg` | 26 / 21 | Solar-array work group versus three workers walking beside a fence; distinct layouts and no recognizable shared person or scene. |
| C04 | `train_source-08e4ee526a5ea46b79ae4b6da87e91a1.jpg` ↔ `train_source-18b80081eef54601f12a1600ed5f700a.jpg` | 24 / 27 | Concrete multi-storey frame versus workers on open scaffolding; construction-site subject matter is shared, but no matching site/person detail is visible. |
| C05 | `train_source-0c7d19330f0099fccf0318900a24806c.jpg` ↔ `train_source-0e2a4d4463396c949ccdf3a3253e1552.jpg` | 24 / 27 | Excavation with a digger and crew versus bricklaying beside a building; no clear matching person or capture scene. |
| C06 | `train_source-04d90135ba9a6511d789035fa9021f31.jpg` ↔ `train_source-0d7c4741b4e34689fad8036e55a5e9e9.jpg` | 36 / 22 | Close group doing formwork versus a distant crew around a tall structure at night; common workwear only, no shared scene cue. |
| C07 | `train_source-0292c17e9ba0666451c96463de7eefe2.jpg` ↔ `train_source-0e59077ef44d89df66fa8b340b15aca0.jpg` | 26 / 23 | Wet construction work area with machinery versus a separate group walking beside a fence; no visible person or scene match. |
| C08 | `train_source-04d90135ba9a6511d789035fa9021f31.jpg` ↔ `train_source-08e4ee526a5ea46b79ae4b6da87e91a1.jpg` | 24 / 30 | Workers doing formwork versus a concrete building frame; both are construction imagery, but the structures and people do not visibly match. |
| C09 | `train_source-0c7d19330f0099fccf0318900a24806c.jpg` ↔ `val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg` | 30 / 23 | Excavation crew versus an indoor warehouse with machinery; visually distinct locations and no shared person/display cue. |
| C10 | `train_source-0c7d19330f0099fccf0318900a24806c.jpg` ↔ `train_source-11843226483797f1c9e6d830452ddbcb.jpg` | 24 / 30 | Excavation crew versus two workers walking on a raised structure; no clear same-person or same-scene clue. |

## Interpretation and limits

- No exact-byte duplicates or ≤8-bit pHash/dHash candidates were found within either set. These results cover only the specified hashes; crops, mirrored/overlaid edits, adjacent video frames, or substantially changed copies can evade them.
- L05 is the only inspected pair with a notable possible same-worker/task hint. Treat it as unresolved pending source/person/session evidence. Similar forklifts, PPE, warehouses, and construction settings in other inspected pairs are not evidence of shared groups by themselves.
- The selected visual review found no visible poster, printed-photo, or screen-content match. It was not a visual audit of all 15,396 pairs.
- Neither different filenames nor different SHA-256 values prove independent groups. No `group_id` or split can be assigned from this diagnostic; unresolved links must remain pending review under the project definition.
