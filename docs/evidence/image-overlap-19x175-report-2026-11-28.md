# Cross-batch image overlap check: 19 vs locked 175

Checked: 2026-11-28. This is a read-only image-byte/perceptual-hash comparison; it does not assign groups or splits.

## Result

- Compared the 19 original JPEGs listed in `datasets/candidates/construction-ppe-review-batch/source_index.csv` against all 175 JPEG members of the locked package `datasets/candidates/construction-ppe-pilot-draft/construction-ppe-pilot-review-package-locked.zip` (3,325 cross-batch pairs).
- **Exact SHA-256 overlaps: 0.** The 19 review files matched their source-index hashes (19/19). The 175 package images matched all unique hashes and dimensions in the locked 175-row roster (175/175). The package SHA-256 matched the lock record.
- **Perceptual candidates: 0** under either screening rule: 64-bit pHash Hamming distance ≤ 8, or 64-bit dHash Hamming distance ≤ 8. The closest pHash distance across any pair was 18/64; the closest dHash distance was 16/64.
- The 19 per-image nearest pHash links (using ascending Hamming distance, then locked member path as a tie-break) are listed below and in the exhaustive CSV. These are diagnostic nearest neighbors only; all are above the candidate threshold and are **not duplicate findings**.

## Nearest pHash check per reviewed image

| 19-image batch file | Nearest locked package member | pHash distance / 64 | dHash distance / 64 |
|---|---|---:|---:|
| `train_source-012007571544d108ad62099e53b8a827.jpg` | `batch-08/session-01/ultralytics-ppe-nov2026-535.jpg` | 22 | 25 |
| `train_source-01472cb50a6610833e564bd5add532ee.jpg` | `batch-06/session-01/ultralytics-ppe-nov2026-328.jpg` | 22 | 23 |
| `train_source-0271ab991bd2c3900528907e5ab2fa2c.jpg` | `batch-07/session-01/ultralytics-ppe-nov2026-021.jpg` | 20 | 29 |
| `train_source-0292c17e9ba0666451c96463de7eefe2.jpg` | `batch-03/session-01/source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` | 22 | 37 |
| `train_source-04c535fcc25148fcc46c3e4d36902d57.jpg` | `batch-05/session-01/source-305deca284bbf639bcdcc00671e240aa.jpg` | 18 | 22 |
| `train_source-04d90135ba9a6511d789035fa9021f31.jpg` | `batch-08/session-01/ultralytics-ppe-nov2026-602.jpg` | 20 | 25 |
| `train_source-0736c04fa3c777e89006eff256fe0a81.jpg` | `batch-02/session-02/source-5dc89b08baaaa3f5098e90ea8e5d5f7e.jpg` | 20 | 25 |
| `train_source-078aa002dcdc9f8ffd092bed4da44e59.jpg` | `batch-01/session-01/ultralytics-ppe-nov2026-285.jpg` | 20 | 34 |
| `train_source-08e4ee526a5ea46b79ae4b6da87e91a1.jpg` | `batch-02/session-01/ultralytics-ppe-nov2026-446.jpg` | 20 | 36 |
| `train_source-0c7d19330f0099fccf0318900a24806c.jpg` | `batch-07/session-01/ultralytics-ppe-nov2026-485.jpg` | 22 | 28 |
| `train_source-0d7c4741b4e34689fad8036e55a5e9e9.jpg` | `batch-06/session-01/source-55914bf88946606112f27e935d1f3200.jpg` | 20 | 22 |
| `train_source-0e2a4d4463396c949ccdf3a3253e1552.jpg` | `batch-07/session-02/ultralytics-ppe-nov2026-469.jpg` | 18 | 27 |
| `train_source-0e59077ef44d89df66fa8b340b15aca0.jpg` | `batch-04/session-01/source-fbb201fd66f289e3ad4e6f1a71c2a282.jpg` | 22 | 34 |
| `train_source-11843226483797f1c9e6d830452ddbcb.jpg` | `batch-05/session-01/source-305deca284bbf639bcdcc00671e240aa.jpg` | 20 | 29 |
| `train_source-122e66278827dc8846c75fb8c7a7a01b.jpg` | `batch-03/session-01/ultralytics-ppe-nov2026-335.jpg` | 20 | 33 |
| `train_source-14bd7cec4f45ba3526e8219b69f10d7a.jpg` | `batch-05/session-01/source-0f1bcf865e6c2db6ebdc47be3bb206b7.jpg` | 20 | 28 |
| `train_source-18b80081eef54601f12a1600ed5f700a.jpg` | `batch-04/session-02/source-3fcdab28d51a8a73673fd1bd1bf917c0.jpg` | 20 | 28 |
| `train_source-21b5c4f737564d611ad72bf77e9ff8fc.jpg` | `batch-01/session-01/ultralytics-ppe-nov2026-285.jpg` | 22 | 20 |
| `val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg` | `batch-04/session-01/source-5aef8f03a221e1d0f7dc1df4501dda5e.jpg` | 18 | 37 |

## Method and thresholds

- **Exact identity:** SHA-256 over original JPEG file bytes. No file was re-encoded or altered.
- **pHash:** EXIF orientation normalized, grayscale, Lanczos resize to 32×32, orthonormal 2-D DCT, top-left 8×8 coefficients thresholded at their median; compare 64-bit hashes by Hamming distance. Candidate threshold: **≤ 8/64 differing bits**.
- **dHash cross-check:** EXIF orientation normalized, grayscale, Lanczos resize to 9×8; compare each horizontal adjacent-pixel pair to form a 64-bit hash; candidate threshold: **≤ 8/64 differing bits**.
- Thresholds are screening heuristics, not calibrated probabilities. CSV has one row per cross-batch pair, SHA-256 and both perceptual hashes, both distances, candidate flags, and deterministic nearest-neighbor flags. Filter `candidate_link_by_rule=true` to see matches; currently that yields zero rows.

## Scope and limits

- The comparison establishes byte equality or similarity under these specified hashes only. Perceptual hashes can miss strongly cropped, mirrored, overlaid, or substantially edited copies and can flag unrelated images with similar global structure. A zero-match result is not proof that the images depict different people/scenes or belong to independent groups.
- **Different filenames or different SHA-256 hashes alone do not prove independent groups.** Do not infer `group_id`, assign a project split, or treat either set as independent from this report. Similarity/group adjudication still requires source/person/session evidence and human review.
- The 19-image source-selection metadata and locked roster/package were read only. No images, annotations, rights/provenance fields, package contents, group IDs, or split fields were changed.

## Inputs and integrity identifiers

- 19-image manifest: `datasets/candidates/construction-ppe-review-batch/source_index.csv` (each indexed JPEG SHA-256 verified).
- Locked roster: `datasets/candidates/construction-ppe-pilot-draft/pilot-roster.csv` (175 unique hashes).
- Locked package SHA-256: `aa386345b02f003e59a408afcf61a55e211cc468bd95981efd99b39d69f01ccf` (matches `PILOT_ROSTER_LOCK.md`).
- Exhaustive comparison CSV: `image-overlap-19x175-comparison-2026-11-28.csv` (3,325 rows plus header).
