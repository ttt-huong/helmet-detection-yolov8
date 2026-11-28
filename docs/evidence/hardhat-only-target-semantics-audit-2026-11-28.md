# Hardhat-only target semantics audit

## Finding

The checked-in ontology, converter, generated `data.yaml` definition, API, and inference UI agree on the intended semantics:

- `hard_hat_worn` is the sole wearer-target class and the only class used to create wearer candidates or contribute to `real_wearer_count`.
- `depiction_region` is the second model class, retained as an auxiliary source-filtering class for posters, printed photos, and screens. It is not a wearer target.
- The other six browser review classes—`traffic_helmet_worn`, `cap_worn`, `beanie_worn`, `bare_head`, `depicted_hat`, and `loose_hat`—do not become YOLO output classes.
- A fully reviewed image containing only those non-target headwear examples can remain in the dataset as hardhat-negative context. If it has no `depiction_region`, the converter writes an empty YOLO label file; if it has a display region, that support box is retained as model class 1.

## Trace through the pipeline

### Ontology

`configs/helmet_types_labeling.md:5-24` defines eight review classes and two model classes. Review ID 0 `hard_hat_worn` maps to model ID 0; review IDs 1–6 are explicitly non-target review labels; review ID 7 `depiction_region` maps to model ID 1 as the support region. The same passage says that reviewed non-target-only images can remain with an empty label file as negative context.

The full-frame/source gates are explicit in `configs/helmet_types_labeling.md:40-47,73-75`: uncertain source is not accepted as a confirmed wearer, depiction-region overlap suppresses or marks candidates uncertain, and only `hard_hat_worn` may be counted. The release checklist reiterates the two generated model names and the hard-negative groups at lines 108–123.

### Converter and negative-context handling

In `scripts/convert_review_json_to_yolo.py:34-52`, the eight-class review map is separate from `TRAIN_CLASSES = ("hard_hat_worn", "depiction_region")`, with `REVIEW_TO_TRAIN_CLASS = {0: 0, 7: 1}` and `TARGET_WORN_IDS = {0}`.

The converter rejects any image whose `frame_source_status` is not `clear`, whose `image_review_status` is not terminal (`reviewed_empty` or `reviewed_with_labels`), or whose annotation remains `uncertain` (`scripts/convert_review_json_to_yolo.py:578-605,655-664`). It also applies source/depiction checks before export: image-head boxes covered by a depiction region are suppressed, partial overlap is rejected for resolution, and only class 0 may count as a wearer (`710-745`).

For each surviving annotation, the converter looks up the review-to-train mapping and skips classes without one (`scripts/convert_review_json_to_yolo.py:747-755`). It copies every included image and writes the resulting label list; an empty list becomes an empty `.txt` file (`797-800`). Therefore a fully reviewed image annotated only with the six excluded classes remains available as a negative example for the hardhat target. A class-7 depiction region is deliberately retained as support even when no class-0 target is present.

### Dataset YAML

The converter creates `data.yaml` from `TRAIN_CLASSES` at `scripts/convert_review_json_to_yolo.py:835-837`, so its `names` entries are class 0 `hard_hat_worn` and class 1 `depiction_region`. The README describes the same mapping and negative-image behavior at `README.md:78-98`.

There is no generated `data.yaml` or released dataset artifact checked into this repository (`datasets/hardhat_only_v1/data.yaml` is absent). This audit therefore verifies the YAML-generation code and documented contract, not a built dataset artifact.

### Inference output

`service/app.py:22-46` configures exactly those two class names and sets `WORN_CLASSES = {"hard_hat_worn"}`. Release manifests must list the same ordered names (`193-203`), and the loaded checkpoint is rejected unless its detection task and `model.names` match that mapping (`425-434`). `extract_detections` maps only class IDs in this two-class allowlist (`527-549`).

`service/app.py:552-588,665-710` treats `depiction_region` as an auxiliary filter: only `hard_hat_worn` detections enter wearer candidates; candidates inside a depiction region or with at least 50% union coverage are suppressed, smaller positive overlap remains uncertain, and zero-overlap candidates remain unverified. A successful API response still fixes `wearer_count` at 0, sets `review_required=true`, and marks `source_status=unverified` pending full-scene review.

The browser inference client uses the same two expected class names and only `hard_hat_worn` in its worn-target set (`web/demo.js:2-11`). It filters hardhat candidates separately from the depiction-region boxes and independently checks the zero-count / review-required / unverified-source response contract (`612-622,464-475,714-719`).

## Limits

- This was a static code/documentation audit. No tests, converter run, training, or live inference were performed.
- No built `data.yaml`, released dataset, or checkpoint is present in the repository, so actual artifact contents and remote model behavior were not observed. The repository README notes the hardhat-only dataset/checkpoint/release artifacts are not checked in (`README.md:23`).
- “Fully reviewed” is enforced through declared `frame_source_status` and terminal `image_review_status`; the converter validates these values but cannot independently verify that a human actually inspected the whole image. It also cannot infer whether a declared label is visually correct.
- The runtime contract is two-class, but no checkpoint is currently available or deployed. Thus a future compatible model may return `depiction_region` in raw/API detections for source filtering; it is auxiliary, not a PPE class. Only `hard_hat_worn` is the wearer-target class, and the API keeps the confirmed wearer count at zero until scene-source review.
