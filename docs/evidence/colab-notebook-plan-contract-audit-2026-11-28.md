# Notebook 03 plan-contract audit — 2026-11-28

## Scope

Static inspection only: Notebook 03 source cells, the data completion plan/checklist, `service/README.md`, `service/Dockerfile`, `service/requirements.txt`, and the API release/runtime checks. The notebook has 8 code cells, all with `execution_count=null` and no saved outputs. I did not open it in Colab/Jupyter or run any cell, training, or test.

## Contract alignment

- **Inputs/schema:** The plan’s `hardhat_only_v1.zip` plus `test_scene_metadata.csv` and confirmed `hard_negative_source_groups.csv` matches the notebook’s Drive inputs. The ZIP is expected to contain `data.yaml`, three splits, `split_manifest.csv`, and `dataset_image_sources.json`. The notebook requires two model classes in order: `hard_hat_worn`, `depiction_region`; its image-source metadata contract is `image-sources-v4` tied to review-v7. It validates `training_use=approved` and per-image rights fields as project declarations, not independent proof of third-party rights, matching the plan’s caveat.
- **Floors/gates:** Notebook constants match the plan/checklist: each model class has 300 train / 1 validation / 100 locked-test boxes; each of the three worn-hat negative subtypes has 300 / 30 / 100 independent groups; each of the six hard-negative source types has 300 train / 100 locked-test groups and no validation floor. The test also requires at least 100 ground-truth `hard_hat_worn` boxes, and all six surface-type × scene-type strata must have reviewed metadata, positive image coverage, complete 1:1 surface-to-region mapping, and zero false unverified candidates.
- **Artifacts:** Notebook outputs `weights/best.pt`, `deployment_test_summary.json`, and `deployment_release.json` under one Drive run; it also persists `training_runtime.json` for resume. The service instructions transfer the same three release artifacts together, and API checks bind checkpoint, dataset, hard-negative-group CSV, and test-summary hashes. On a blocked final gate, the notebook preserves the diagnostic report but removes deployable summary/receipt files.
- **Runtime:** Notebook requires the Colab release tag and an available GPU. It records `python`, `torch`, `torchvision`, `torch_cuda`, and `ultralytics`; resume requires an exact match for all five. The API requires all five strings but compares exactly Torch, Torchvision, CUDA, and Ultralytics; Python is recorded but is not compared at inference, as the service README states. Notebook and service requirements both pin Ultralytics `8.4.202`.

## Findings and remaining conditions

1. **False-candidate gate scope is ambiguous in the written checklist.** Notebook 03 computes false unverified candidates per image, but the release predicate gates them only within the six required surface × scene strata. The checklist says “no false unverified hardhat candidate” without limiting that sentence to those strata. If the intended gate is test-wide, add a separate locked-test-wide predicate (and API check); otherwise scope the checklist wording to the six strata.
2. **Runtime fingerprint remains a deployment blocker until an actual Colab run.** The notebook uses the Colab Torch/Torchvision/CUDA versions available at execution; it pins only Ultralytics. The Dockerfile defaults to Torch 2.11.0, Torchvision 0.26.0, CUDA 13.0. The service README correctly instructs operators to reconcile those pins to the recorded Colab fingerprint before deployment. No fingerprint, trained checkpoint, test summary, receipt, dataset ZIP, or sidecar inputs exist at the checked workspace paths; this audit therefore confirms source contracts, not a successful run or release.
3. **Rights are checked as declarations.** Notebook preflight verifies approved per-image rights metadata, but does not independently establish source provenance or rights-holder authority. This matches the plan’s stated limitation and remains a separate release prerequisite.

## References

- [Data completion plan](../ke_hoach_hoan_tat_du_lieu.md), sections “Các việc cần hoàn thành” and “Ngưỡng dữ liệu và bàn giao Colab”.
- [Validation checklist](../checklist_kiem_thu.md), sections “Mức đủ dữ liệu theo kế hoạch” and “Chờ đủ dữ liệu · chưa train”.
- Notebook source: `../../notebooks/03_train_hat_types_colab.ipynb` (cells 0–11).
- [Deployment instructions and model contract](../../service/README.md); runtime pins: `../../service/Dockerfile`, `../../service/requirements.txt`.

No source or plan files were changed.
