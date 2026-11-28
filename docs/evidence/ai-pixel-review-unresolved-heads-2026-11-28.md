# Focused AI pixel review: unresolved heads

Date: 2026-11-28
Scope: visual review of the original JPEG pixels for five prompted head candidates in the 19-image batch. The image IDs and approximate candidate locations were supplied by the coordinator from the stable batch mapping and prior audit. No annotation JSON, YOLO labels, overlays, source metadata, or rights records were consulted or changed.

Reviewer: AI subagent. This is **not a human reviewer ID** and the review was **not blind** to the candidate IDs or supplied locations. Findings are limited to visible pixels and are not provenance or source facts.

| Candidate | Original JPEG (SHA-256) | Approximate location | Pixel-only finding |
|---|---|---|---|
| #1, far-left worker | [`train_source-012007571544d108ad62099e53b8a827.jpg`](../../datasets/candidates/construction-ppe-review-batch/train_source-012007571544d108ad62099e53b8a827.jpg) · `c01f98b97d0d9ca25253424259db6df3f99e3a81988c79d4135599758ad0f8fc` | `[241,160,258,182]` | **Uncertain.** The head is a small dark shape; the pixels do not show enough contour detail to distinguish helmet from cap or hair. |
| #5, forklift operator | [`train_source-04c535fcc25148fcc46c3e4d36902d57.jpg`](../../datasets/candidates/construction-ppe-review-batch/train_source-04c535fcc25148fcc46c3e4d36902d57.jpg) · `48e2e971bf0a41e1ae608e10866a0ae52108471cfde33d51259f184de6d8dd01` | `[623,671,644,695]` | **Uncertain.** The head pixels are too small and dark to distinguish hardhat from cap or hair. |
| #5, rear-right pallet worker | Same original JPEG and SHA-256 as the preceding row | `[799,588,821,614]` | **Uncertain.** A small blue/dark headgear-like patch is visible, but its outline and material do not establish hardhat versus cap. |
| #16, extra small person | [`train_source-14bd7cec4f45ba3526e8219b69f10d7a.jpg`](../../datasets/candidates/construction-ppe-review-batch/train_source-14bd7cec4f45ba3526e8219b69f10d7a.jpg) · `29dbc094ca7bbb3c9d755017d2eada9230aabfffcb86f7247ed00cf87660607a` | Approximately normalized `(x=0.28, y=0.22–0.24)`; no candidate box | **Uncertain.** The person and head are too small at this scale for a confident class. |
| #19, central loading-bay doorway | [`val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg`](../../datasets/candidates/construction-ppe-review-batch/val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg) · `caf419a0881a9c970141b2f917a81aef7bd65d6b71c30c8b4c0f9ea229cdcddc` | `[587,216,605,236]` | **Pixels support `hard_hat_worn`.** A light rounded shell with a projecting rim is visible on the head. This is a separate focused AI pixel finding; it does not replace or revise the earlier unresolved-head audit. |

No candidate JSON or labels were edited during this original focused pixel-review pass. #1, both #5 cases, and #16 remain uncertain. The separate #19 finding was later adjudicated in v10 as `hard_hat_worn`; see the [v10 adjudication report](../../datasets/candidates/construction-ppe-review-batch/candidate-review-v10-adjudication-2026-11-28.md).
