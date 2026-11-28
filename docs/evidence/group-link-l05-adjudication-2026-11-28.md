# L05 image-pair adjudication

## Finding

**Outcome: unresolved.** The two images provide a plausible same-worker/task lead, but do not establish the same person or capture session. Confidence is **high (judgmental, about 0.85)** that the available evidence is insufficient to assign a shared project group. This is not an 85% estimate that the people are the same or different.

## Locked originals

Both images were read directly from the locked pilot ZIP and checked against `pilot-roster.csv`:

| Image | Archive member | Dimensions | SHA-256 |
|---|---|---:|---|
| `ultralytics-ppe-nov2026-490.jpg` | `batch-02/session-01/ultralytics-ppe-nov2026-490.jpg` | 2048×1152 | `5e9614384efc6869f614a7250be995e84d34649e6cef712093a1eb24e0d92402` |
| `ultralytics-ppe-nov2026-626.jpg` | `batch-04/session-01/ultralytics-ppe-nov2026-626.jpg` | 2048×1360 | `a75ea31fe6f1bace0658b1019e42aeb5f95c683819d1ca3cc4a7b15a4e4abcf1` |

The hashes differ, so they are not byte-identical files. Different hashes do not establish that the people or source sessions are distinct.

## Pixel evidence

**Similarities:** both frames show an older male-presenting worker wearing a white hard hat, orange high-visibility vest, dark long-sleeved top, and clear eye protection. In each, he is bent over timber beside an orange forklift with a dark mast. The task, PPE, and forklift configuration make the recurring-worker hypothesis plausible.

**Differences and limits:** 490 is a close crop with the worker’s head clipped at the top edge; his face does not provide enough distinctive detail for a reliable identity comparison. 626 is a wider view with the worker’s face more visible, different pose, and a broader open-yard composition. The visible surroundings and camera framing do not show a shared background landmark or an unmistakable continuous capture. The forklift colors and general shape are similar, but no unique marking or serial detail is legible. Similar PPE, equipment type, and task are not proof of identity or session.

## Source and archive evidence

- The ZIP README says the package contains no per-image provenance or source-stratum map. It also says the nested `batch-*` / `session-*` directories are deterministic import partitions for browser limits. Thus `session-01` in both archive paths describes package organization, not a verified photo-capture session.
- Both JPEGs have empty EXIF. Their ZIP member timestamps are identical (`2026-11-27 00:00:00`) and the entries have no comments or extra fields; these are package metadata and do not supply capture dates or location.
- Exact-filename web searches did not surface an indexed per-image source record. The [Ultralytics Construction-PPE documentation](https://docs.ultralytics.com/datasets/detect/construction-ppe) describes the public dataset as combining human-collected and generated images, but does not provide per-image person, location, or session links for these filenames. That general dataset description cannot resolve L05.
- The within-set screening report lists L05 at pHash/dHash distances 18/13. These are candidate-generation distances only and are not identity evidence.

## Decision and limits

Treat the pair as an unresolved possible recurring worker/task. Available pixels do not support calling them distinct, and the cropped face plus lack of per-image provenance prevent confirming the same person or session. Keep any group/split decision pending a traceable source record, a stronger full-face comparison, or capture-sequence metadata. No `group_id` or split is proposed here.
