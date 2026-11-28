# Browser demo readiness (2026-11-28)

## Finding

A safe, model-free smoke path is available in the manual labeler at `/` (`web/index.html`). The documented server command is `python -m http.server 8765 --bind 127.0.0.1 --directory web`; the README says this page accepts local images, manual boxes/labels, and JSON export, and does not upload images or run AI ([README.md:71-74](../../README.md#L71)). The labeler creates browser object URLs for selected files and keeps its draft in `localStorage` ([app.js:122-147](../../web/app.js#L122), [app.js:413-450](../../web/app.js#L413)); static inspection found no network request in `web/app.js`.

`web/` contains no dedicated fixture. Use a locally generated synthetic PNG (one isolated hardhat-shaped object on a plain background, no person/poster/photo/screen), kept outside the dataset. Use a fresh private window or empty browser profile so an old local draft cannot affect the smoke. The file input accepts PNG/JPEG/WEBP and enforces a 10 MB per-file limit ([app.js:28-33](../../web/app.js#L28), [app.js:1076-1094](../../web/app.js#L1076)).

## Minimal labeled smoke steps

1. Start the documented static server from the repository root and open `http://127.0.0.1:8765/`. Do not open `demo.html` for this smoke.
2. Select the synthetic PNG through `#file-input` (or the “Thêm ảnh” control). Wait for its asset row and dimensions to appear.
3. Choose `button.label-choice[data-class="loose_hat"]`, then drag once over the isolated hat on `#image-canvas`. This label exercises manual box creation without marking a wearer or asserting a real person.
4. Set `#image-scene-type` to `other`. Review the whole synthetic frame, confirm it contains no people in a poster, printed photo, or screen using `#other-scene-review`, then click `#review-scene`. The app requires this explicit check for `other` before it clears the frame source ([index.html:81-85](../../web/index.html#L81), [app.js:1840-1885](../../web/app.js#L1840)). A `loose_hat` box does not require depiction-surface inventory; those requirements apply to depiction scenes and `depicted_hat`/`depiction_region` annotations ([app.js:718-729](../../web/app.js#L718)).
5. Click `#mark-reviewed-with-labels`, then `#export-json` ([index.html:36, 76-84](../../web/index.html#L36), [app.js:1899-1914](../../web/app.js#L1899)).

Expected download: `helmet-vision-review-v7.json` with one image in `reviewed_with_labels`, `frame_source_status: "clear"`, one class `loose_hat` annotation, and `real_wearer_count: 0` ([app.js:2026-2065](../../web/app.js#L2026)).

## Gates and limits

- The export button remains disabled until each image has a terminal image-review status. Export also stops on unresolved depiction inventory/region problems. Missing `group_id`, `split`, and rights metadata do **not** stop the download: they produce a post-download warning ([app.js:1973-2024](../../web/app.js#L1973), [app.js:2065-2108](../../web/app.js#L2065)). Leave these project fields blank/unknown for this synthetic smoke; do not label the fixture as project-approved or pass its JSON to the converter or training pipeline.
- `demo.html` is the model-inference page. It probes `/livez` and `/health` on load and only posts an image to `/predict` when its run control is used ([demo.js:184-220](../../web/demo.js#L184), [demo.js:679-707](../../web/demo.js#L679)). It is unnecessary for the static labeler smoke and requires an inference API/model to produce results.
- The agent portion of this report is a code-and-documentation review only; it did not change production behavior. The isolated port-8794 attempt below timed out during box drawing; that failed attempt was superseded by the successful port-18765 smoke recorded at the end of this report.

## Live browser supplement — coordinator — 2026-11-28

- A separate browser interaction loaded the existing local synthetic fixture `helmet-uncertain-export-fixture.jpg` (640×480) at `http://127.0.0.1:8793/`. The UI showed one image in the session and reported that its draft was saved locally; it also states the image is not uploaded. This confirms image import only, not annotation/export or inference.
- The browser view of `http://127.0.0.1:8793/demo.html` showed “Chưa có inference API tại origin này” and a disabled run button. No image was submitted. The earlier 03:46 +07 no-listener observation and later `checkpoint_missing` preview status are time-scoped in `docs/evidence/live-api-readiness-2026-11-28.md`.
- Historical failed attempt, superseded by the successful port-18765 smoke below: at temporary port 8794, a purpose-made synthetic loose-hardhat fixture was imported and `loose_hat` selected, but drag-to-draw timed out before a box was created. No annotation or export was produced in that attempt. The temporary server was stopped. This was an automation-control failure, not evidence of an application defect.
- Browser state was confirmed through the DOM/accessibility snapshot. Screenshot capture was unavailable in this session, so this note does not claim screenshot evidence.

## Current local readiness snapshot — 2026-11-28

Snapshot: 15:52–15:53 +07; GET rechecked at 15:57 +07. This is point-in-time; listeners and container health can change after the check.

- The hidden static server PID `2168` is serving `web/` at `http://127.0.0.1:8793/`. `GET /` and `/demo.html` return **200**; `/health` returns **404**. The `demo.html` confidence slider is **1–100%**. At this origin the page is only a static manual-labeler/demo UI; its run control stays disabled because this origin has no inference API. No image was sent to the inference API during this status check.
- A separate Docker preview container, `helmet-scene-api-preview`, is mapped to `127.0.0.1:7860`. `/livez` returns **200**, while `/health` returns **503** with `status=model_not_loaded`, `model_loaded=false`, and `error_code=checkpoint_missing`. Its config sets `MODEL_PATH=/models/best.pt`, has zero mounts, and `/models` plus the checkpoint are absent inside the container; this explains the readiness error. The API process is alive, but inference stays disabled because no released checkpoint is available.
- At this check, port `7861` (SSH tunnel) and static-server port `8765` were off. The 8793 UI and the 7860 API preview are separate origins; the 8793 `/health` 404 must not be read as API readiness.

## Isolated browser label-and-export smoke — coordinator — 2026-11-28

- Served the unchanged `web/` directory on loopback at `http://127.0.0.1:18765/`, a separate origin. Generated a 640×480 synthetic loose-hat PNG in the system temp directory; no project or user image was used.
- In the browser, imported the synthetic image, drew one box using `loose_hat`, selected scene `other`, checked the full-frame/no-depicted-people review, marked the frame-source review clear, marked the image and its labels reviewed, and exported the v7 JSON. This did not verify image provenance or rights.
- Readback confirmed one image and one annotation: `class_id=6`, `class_name=loose_hat`, `image_review_status=reviewed_with_labels`, `frame_source_status=clear`, `real_wearer_count=0`, `counts_as_real_wearer=false`, and `rights.training_use=unknown`; `group_id` and `split` remained blank. The UI warned that the synthetic record lacked project metadata/rights, as expected. This is only a manual-labeler/export smoke; it is not project data, was not passed to the converter/training pipeline, and says nothing about model accuracy or inference.
- The temporary server was stopped and the browser tab closed. Generated synthetic fixtures and the test export remain in the local temporary directory. The browser draft is isolated to origin `127.0.0.1:18765`; no other origin or project draft was touched.
