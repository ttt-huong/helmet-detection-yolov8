# Local API and cloud-tunnel readiness check

**Observed:** 2026-11-28 03:46 +07:00. Read-only checks only; no image or inference payload was sent.

## Current local endpoints

| GET request | Result |
|---|---|
| `http://127.0.0.1:7860/livez` | Timed out; no listening socket was present on port 7860. |
| `http://127.0.0.1:7860/health` | Timed out; no listening socket was present on port 7860. No API readiness response was obtained. |
| `http://127.0.0.1:7860/demo.html` | Timed out; no local API/demo server was listening on 7860. |
| `http://127.0.0.1:8765/` and `/demo.html` | Timed out; no listener was present on the documented static-review port 8765. |
| `http://127.0.0.1:8793/` and `/demo.html` | HTTP 200, HTML. A Python static server was listening on `127.0.0.1:8793`, serving the repository `web/` directory. `/demo.js` also returned HTTP 200. |
| `http://127.0.0.1:8793/health` and `/livez` | HTTP 404 HTML. This is a static file server, not the inference API. |

The demo client probes `/livez` and `/health` on its own origin (`web/demo.js:174-220`). Given the 8793 health response is a non-JSON 404, its code selects the `preview-only` state, **“Chưa có inference API tại origin này”**. This UI state is inferred from the observed GET responses and the client branch; the page was not opened in a browser during this check.

## Release artifacts and cloud connection

- A targeted workspace search under the repository, `runs/`, `models/`, `service/`, and `datasets/` found no `best.pt`, `deployment_release.json`, or `deployment_test_summary.json`. The expected top-level files are also absent. No local model path or cloud/API host variables (`MODEL_PATH`, `MODEL_DIR`, `CLOUD_HOST`, `SSH_HOST`, `API_BASE_URL`, `HF_SPACE_URL`) were set in this shell.
- No listener was present on the documented tunnel port 7861. The process query found no process named `ssh.exe`, `wsl.exe`, `docker.exe`, `cloudflared.exe`, or `ngrok.exe`. The repository’s cloud instructions still use the placeholder `USER@CLOUD_HOST`; they describe `ssh -L 127.0.0.1:7861:127.0.0.1:7860` as the tunnel (`service/README.md:96-103`). No active host/tunnel was available to check remotely.
- The cloud-side `/mnt/models` directory and any remote receipt/summary/checkpoint could not be inspected without a configured host and tunnel. The project documents that the three release artifacts must be installed together on the VM and that `/health` must report `model_loaded=true` before demo use (`service/README.md:7,58,86-90`).

## Comparison with repository status notes

At the **03:46 +07 snapshot recorded above**, local port 7860 had no listener and the documented 7861 tunnel was off. That observation predates the preview process below. A later snapshot at 15:52–15:53 +07 found the Docker preview on 7860 (`/livez` 200; `/health` 503 `checkpoint_missing`), and an independent GET at 15:57 +07 confirmed the same result. The training-readiness note records the newer preview state; it still reports no release artifacts and no verified remote VM/Drive state.

The checklist and training-readiness notes now distinguish the earlier no-listener observation from the later preview. At 15:52–15:53 +07, `/livez` returned 200 but `/health` returned 503 `checkpoint_missing`; the process was alive, while model inference remained unavailable. The separate GET recheck at 15:57 +07 returned the same statuses. No image was sent to `/predict`; the source calls `load_model()` before reading image bytes, so the missing-checkpoint behavior is source-derived. Remote VM/Drive status remains unknown, and the 7861 tunnel was off in the 15:52–15:53 snapshot.

## Conclusion

At the **03:46 +07 snapshot**, the inference API was not reachable on local port 7860, the documented 8765 static server was not running, and there was no active 7861 SSH tunnel. A static UI was available on port 8793, but its health paths were 404, so it could not provide inference readiness. No local checkpoint, v9 receipt, or test summary was found; cloud artifacts remained unverified at that time. No service, dataset, or release file was changed, and no training or inference was run in that snapshot.

## Newer local observation — 2026-11-28

**Snapshot:** 15:52–15:53 +07; independently rechecked at 15:57 +07.

The sections above preserve the earlier 03:46 +07 snapshot. A later point-in-time check found a Docker preview container, `helmet-scene-api-preview`, mapped to `127.0.0.1:7860`:

| GET request | Later result |
|---|---|
| `http://127.0.0.1:7860/livez` | HTTP 200, `{"status":"alive"}`. |
| `http://127.0.0.1:7860/health` | HTTP 503, `status=model_not_loaded`, `model_loaded=false`, `error_code=checkpoint_missing`. |
| `http://127.0.0.1:7861/` | No listener; SSH tunnel is off. |
| `http://127.0.0.1:8765/` | No listener; documented static-server port is off. |

Container inspection explains `checkpoint_missing`: `MODEL_PATH=/models/best.pt`, it has **zero mounts**, and `/models` is absent inside the container. No checkpoint file is present there. No container changes were made.

This is a preview process, not inference readiness: `/livez` proves the process responds, while `/health` blocks model use because the configured checkpoint is missing. Source inspection shows `/predict` calls `load_model()` before `image.read()` and would return HTTP 503 with `detail.code=checkpoint_missing`; no POST or image was sent, so that response is source-derived, not observed. A repository search found no `best.pt`, `deployment_release.json`, or `deployment_test_summary.json`. The remote Drive/VM state remains unknown because no remote host/tunnel is configured for inspection. No image was uploaded or sent to `/predict`; no training or inference was run. Listener and container health are point-in-time observations and can change.
