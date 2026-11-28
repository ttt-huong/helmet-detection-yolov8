# Chạy inference bằng GPU local hoặc cloud

Dịch vụ này phục vụ checkpoint YOLO hardhat-only hai lớp đã huấn luyện: hardhat là mục tiêu, `depiction_region` là lớp phụ lọc poster. Huấn luyện chỉ chạy trong Google Colab theo notebook `notebooks/03_train_hat_types_colab.ipynb`. Container chỉ chạy dự đoán.

## Chuẩn bị trên máy ảo cloud

Tạo một máy ảo Linux có GPU NVIDIA, Docker và NVIDIA Container Toolkit. Notebook Colab ghi `best.pt` tại `MyDrive/helmet_project/runs/hardhat_only/hardhat_only_v1/weights/`; hai JSON phát hành nằm ở thư mục `hardhat_only_v1/` ngay phía trên. Sau khi đạt cổng test cho poster, ảnh in và màn hình, chuyển `best.pt` ra khỏi `weights/` và đặt cả ba file cạnh nhau trong `/mnt/models/` trên máy ảo. API tính hash của checkpoint và summary, yêu cầu summary ràng buộc đúng checkpoint đó, đối chiếu hash dataset giữa summary và biên nhận, rồi xác nhận độ phủ và cổng test theo từng loại bề mặt hiển thị trước khi nạp model. Biên nhận không phải chữ ký số. Không commit checkpoint hoặc artifact phát hành vào Git.

### Chuyển bộ artifact từ Drive sang VM

Chỉ chuyển artifact sau khi cell 11 của Notebook 03 báo `Deployment gate: approved` và ghi đường dẫn cho cả `deployment_test_summary.json` lẫn `deployment_release.json`. Tải ba file từ cùng thư mục run trên Drive về một thư mục staging trên máy vận hành: `weights/best.pt`, `deployment_release.json` và `deployment_test_summary.json`. Không ghép checkpoint hoặc JSON từ các run khác nhau.

Trên Windows, có thể chạy `ssh`/`scp` từ PowerShell nhưng hãy thay `/path/to/staging/...` bằng đường dẫn Windows, đặt từng đường dẫn trong dấu nháy kép và viết lệnh `scp` trên một dòng (`\` không tiếp tục dòng trong PowerShell). Các lệnh `docker` và `sudo install` bên dưới chạy trong shell Linux của VM sau khi SSH vào; lệnh tunnel chạy trên máy đang mở trình duyệt.

Từ máy vận hành, tạo thư mục nhận rồi gửi đúng ba file qua SSH:

```sh
ssh USER@CLOUD_HOST 'mkdir -p /tmp/helmet-release'
scp /path/to/staging/best.pt \
  /path/to/staging/deployment_release.json \
  /path/to/staging/deployment_test_summary.json \
  USER@CLOUD_HOST:/tmp/helmet-release/
```

Trong PowerShell, mở thư mục staging chứa đúng ba file rồi dùng lệnh một dòng này thay cho lệnh `scp` nhiều dòng phía trên:

```powershell
scp ".\best.pt" ".\deployment_release.json" ".\deployment_test_summary.json" "USER@CLOUD_HOST:/tmp/helmet-release/"
```

Sau khi truyền file, từ PowerShell mở một shell tương tác trên VM. Chạy các lệnh `docker` và `sudo install` bên dưới trong shell Linux đó:

```powershell
ssh USER@CLOUD_HOST
```

Trên VM, cài ba file cạnh nhau. Nếu đang thay release của một API chạy sẵn, dừng container trước khi cài:

```sh
docker stop helmet-scene-api
```

Cài cả ba file vào thư mục được mount chỉ đọc cho container:

```sh
sudo install -d -m 0750 /mnt/models
sudo install -m 0440 /tmp/helmet-release/best.pt /mnt/models/best.pt
sudo install -m 0440 /tmp/helmet-release/deployment_release.json /mnt/models/deployment_release.json
sudo install -m 0440 /tmp/helmet-release/deployment_test_summary.json /mnt/models/deployment_test_summary.json
```

Sau khi thay release, khởi động lại container hiện có:

```sh
docker start helmet-scene-api
```

Với lần cài đầu, bỏ qua các lệnh dừng/khởi động container và chạy lệnh `docker run` bên dưới sau khi cài xong. Chỉ mở demo khi `GET /health` trả HTTP 200 và `model_loaded=true`; API kiểm tra hash checkpoint, receipt, summary và fingerprint runtime trước khi nạp model. Nếu health chưa sẵn sàng, đọc `error_code` để phân biệt thiếu file, sai hash, gate hoặc runtime.

Từ thư mục gốc repository trên máy ảo, build UI và API cùng origin. `.dockerignore` chỉ đưa `service/` và `web/` vào build context; checkpoint, dữ liệu và notebook không được gửi vào image:

```sh
docker build -f service/Dockerfile -t helmet-scene-api .
```

Trước khi chạy API, kiểm tra GPU passthrough ngay trong image; bước này không cần checkpoint hoặc receipt và không chạy inference:

```sh
docker run --rm --gpus all --entrypoint python3 helmet-scene-api -c 'import torch; print("torch=", torch.__version__, "cuda=", torch.version.cuda, "available=", torch.cuda.is_available()); assert torch.cuda.is_available(), "CUDA is not visible inside the container"'
```

Lệnh thành công chỉ xác nhận CUDA nhìn thấy được bên trong container. Nó không xác nhận model/release readiness; health endpoint vẫn yêu cầu checkpoint và hai artifact phát hành hợp lệ.

### Preview giao diện trước khi có model phát hành

Để kiểm tra trang demo và tiến trình API trước release, có thể chạy image không gắn volume/checkpoint:

```sh
docker run --rm --detach --name helmet-scene-api-preview \
  --gpus all \
  --publish 127.0.0.1:7860:7860 \
  helmet-scene-api
```

Mở `http://127.0.0.1:7860/demo.html`. `/livez` phải trả HTTP 200; `/health` trả HTTP 503 với `error_code=checkpoint_missing` là kết quả dự kiến vì container không có `/models/best.pt`. Docker `HEALTHCHECK` cũng sẽ báo container `unhealthy`; tiến trình UI/API vẫn có thể trả lời. Đây chỉ là preview giao diện và process, không xác minh CUDA hoặc model, không chạy inference. Không chọn ảnh hay bấm nút chạy trong chế độ này; chạy phép CUDA smoke riêng ở trên để kiểm tra GPU passthrough.

### Inference GPU local trên Windows sau khi Colab phát hành model

Huấn luyện vẫn chỉ chạy trên Notebook 03 trong Colab. Sau khi cell 11 báo `Deployment gate: approved`, có thể chạy API inference trên máy Windows có Docker GPU passthrough để thử bằng trình duyệt. Tạo `C:\helmet-release` và đặt đúng ba artifact cùng một run vào đó: `best.pt`, `deployment_release.json` và `deployment_test_summary.json`. Không đưa dataset vào container. Trước khi chạy, đối chiếu runtime trong summary với Dockerfile; nếu `torch`, `torchvision`, `torch_cuda` hoặc `ultralytics` lệch thì chỉnh Dockerfile và build lại trước.

Từ PowerShell ở thư mục gốc repository, kiểm tra đủ artifact rồi chạy container. Cổng `7861` giữ nguyên preview hiện tại ở `7860`; thư mục model chỉ được mount đọc:

```powershell
$release = 'C:\helmet-release'
$models = (Resolve-Path -LiteralPath $release).Path.Replace('\', '/')
$required = @('best.pt', 'deployment_release.json', 'deployment_test_summary.json')
$missing = $required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $release $_) -PathType Leaf) }
if ($missing) { throw "Missing release files: $($missing -join ', ')" }

docker run --rm --detach --name helmet-scene-api-local --gpus all `
  --publish 127.0.0.1:7861:7860 `
  --env MODEL_PATH=/models/best.pt `
  --mount "type=bind,source=$models,target=/models,readonly" `
  helmet-scene-api
```

Mở `http://127.0.0.1:7861/demo.html`. Chỉ thử inference sau khi `curl.exe -i http://127.0.0.1:7861/health` trả HTTP 200 và JSON có `model_loaded=true`. HTTP 503 nghĩa là release hoặc GPU chưa sẵn sàng; xem `error_code` và log bằng `docker logs helmet-scene-api-local`. Dừng API local bằng `docker stop helmet-scene-api-local`.

Chạy API với thư mục checkpoint được mount chỉ đọc:

```sh
docker run --detach --name helmet-scene-api \
  --gpus all \
  --restart unless-stopped \
  --publish 127.0.0.1:7860:7860 \
  --env MODEL_PATH=/models/best.pt \
  --volume /mnt/models:/models:ro \
  helmet-scene-api
```

## Health probes

`GET /livez` returns HTTP 200 when the ASGI process can answer requests. It does not inspect the GPU, checkpoint, release receipt, or model. Use it only to distinguish a live process from a stopped/unreachable one.

`GET /health` is the inference-readiness check used by the Docker `HEALTHCHECK` and browser demo. It returns HTTP 200 only when the GPU and released model are ready (`model_loaded=true`); a 503 can mean the process is alive but inference is not ready. Check `/health` before using `/predict` or the demo. A successful `/livez` must never be treated as model readiness.

The browser demo waits up to 10 seconds for `/livez`, 180 seconds for `/health` (which may load the model on the first request), and 120 seconds for `/predict`. If prediction times out, the browser stops waiting, but the API may still be processing the image; check the API status/logs before submitting again.

Container hiện pin PyTorch 2.11.0 và Torchvision 0.26.0 với CUDA 13.0 làm mặc định. Notebook ghi chính xác Torch, Torchvision, `torch.version.cuda`, Ultralytics và Python vào `training_runtime` trong summary, đồng thời lưu fingerprint cạnh run trên Google Drive để chặn resume bằng runtime khác. Trước khi nạp YOLO, API so khớp chính xác bốn phiên bản Torch/Torchvision/CUDA/Ultralytics với summary; thiếu metadata hoặc lệch phiên bản trả `release_runtime_mismatch`. Mỗi lần gọi `/health` và `/predict` đều kiểm tra CUDA kể cả khi model đã nằm trong cache; `/predict` truyền `device=0`, và GPU không sẵn sàng trả `inference_gpu_unavailable`. Python được ghi để truy xuất nhưng API không so sánh phiên bản này; hãy giữ Python major/minor tương thích với runtime Colab khi triển khai checkpoint. Notebook không tự ghim một biến thể CUDA wheel; hãy dùng runtime Colab có sẵn và điều chỉnh PyTorch/Torchvision trong Dockerfile cho khớp fingerprint sau khi notebook ghi nhận nó. Không triển khai nếu runtime không khớp. Máy cloud cần NVIDIA driver tương thích với CUDA được ghi trong fingerprint. Dockerfile dựa trên image CUDA/cuDNN chính thức của NVIDIA. [Lệnh cài PyTorch CUDA chính thức](https://pytorch.org/get-started/previous-versions/) · [Docker GPU Spaces của Hugging Face](https://huggingface.co/docs/hub/spaces-sdks-docker)

## Thử API trong trình duyệt

Từ máy đang mở trình duyệt, tạo SSH tunnel đến máy ảo cloud. Ví dụ dùng cổng loopback `7861` ở máy mở browser để không đụng dịch vụ local có thể đang chiếm `7860`; phía VM vẫn giữ API ở `127.0.0.1:7860`:

```sh
ssh -L 127.0.0.1:7861:127.0.0.1:7860 USER@CLOUD_HOST
```

Mở `http://127.0.0.1:7861/demo.html` để tải ảnh lên và xem hộp dự đoán, vùng poster bị loại, ứng viên chưa xác minh và số đếm vẫn bằng 0. Ảnh chỉ được gửi đến API host khi bấm chạy: nếu trang được mở qua SSH tunnel thì host là VM GPU cloud; nếu API chạy trực tiếp trên máy local thì ảnh ở trên máy đó. `/docs` vẫn có thể dùng để thử `POST /predict`; `/health` trả HTTP 503 cùng `model_loaded=false` nếu model chưa sẵn sàng, kèm `error_code` để phân biệt cấu hình `MODEL_PATH`, checkpoint, biên nhận/cổng test, hash checkpoint, runtime mismatch hoặc GPU không được expose vào container (`inference_gpu_unavailable`).

FastAPI phục vụ các trang trong `web/` và API cùng một origin, nên trang demo không cần CORS. Tunnel giữ cổng dịch vụ chỉ trên loopback của máy ảo. Không mở cổng công khai nếu chưa đặt dịch vụ sau HTTPS và cơ chế xác thực; API hiện chưa có xác thực riêng.

## Hợp đồng model

`MODEL_PATH` phải trỏ tới `best.pt` hardhat-only có đúng hai lớp theo thứ tự sau. `depiction_region` là lớp phụ để lọc poster/ảnh/màn hình, không phải loại mũ thứ hai. Mặc định, cùng thư mục phải có `deployment_release.json` và `deployment_test_summary.json`; có thể đổi vị trí bằng `MODEL_RELEASE_PATH` và `MODEL_TEST_SUMMARY_PATH`.

| ID | Lớp |
| ---: | --- |
| 0 | `hard_hat_worn` |
| 1 | `depiction_region` |

API yêu cầu `deployment_release.json` và `deployment_test_summary.json` cạnh checkpoint. Biên nhận phải là `helmet-vision-model-release-v9`, có đúng thứ tự hai lớp, `depiction_surface_gate_status=pass_reviewed_metadata`, đúng danh sách `poster`, `printed_photo`, `screen`, `scene_metadata_source=reviewed_metadata_csv`, hash dataset/test summary/source-group metadata và SHA-256 khớp với `best.pt`. API tự tính SHA-256 checkpoint và summary; checkpoint hash trong summary phải trùng checkpoint đang nạp. Hash dataset và `hard_negative_source_groups.csv` được đối chiếu giữa summary với biên nhận; API không đọc lại archive dữ liệu hoặc CSV này tại thời điểm inference. Summary phải ghi test hoàn tất, metadata đã rà với ảnh thuộc từng loại bề mặt trong cả `depiction_only` lẫn `mixed_scene`, và `training_runtime` gồm chuỗi `python`, `torch`, `torchvision`, `torch_cuda`, `ultralytics`. API yêu cầu metadata đúng schema và so khớp chính xác `torch`, `torchvision`, `torch_cuda`, `ultralytics` runtime trước khi tạo YOLO; Python chỉ được lưu, không so sánh. Lệch hoặc thiếu version sẽ chặn model với `release_runtime_mismatch`. Cả sáu cổng phải có số ảnh dương, `depiction_surface_instance_image_count == image_count` trong từng cổng, và không có false unverified hardhat candidates. Summary v9 còn phải chứng minh ≥300 train/≥100 test boxes cho mỗi lớp model và ≥300 train/≥100 locked-test `group_id` độc lập cho từng nguồn `poster`, `printed_photo`, `screen`, `loose_hat`, `mixed_scene`, `empty_background`; API fail-closed với `release_data_sufficiency_gate_mismatch` nếu thiếu quota hoặc stats. Negative theo loại mũ có floor riêng cho `traffic_helmet_worn`, `cap_worn`, `beanie_worn`: mỗi loại cần ≥300 group train, ≥30 group val và ≥100 group locked-test. Counts là số `group_id` duy nhất trong từng split, không nhân theo frame/ảnh/box; một group chỉ thuộc một split. Summary phải ghi `hat_type_negative_group_counts`; API kiểm tra trực tiếp count, không tin status khai báo, và fail closed nếu thiếu hoặc thấp hơn floor. Notebook chỉ cấp summary pass sau khi kiểm tra inventory `{surface_id,surface_type}` và từng record `depiction_region_surfaces` `{surface_id,surface_type,box}`, đúng một model class-1 GT label mỗi instance, box normalized YOLO khớp chính xác multiset label ở độ chính xác 8 chữ số và không có geometry trùng. Thiếu mapping/vùng GT, độ phủ, sai hash hoặc test gate không đạt thì model không được nạp; biên nhận v2–v8 cũ bị từ chối. Các hash/báo cáo chỉ được kiểm tra nhất quán, không có chữ ký số xác thực nguồn phát hành. API cũng kiểm tra thứ tự lớp khi nạp checkpoint. Hộp hardhat có tâm nằm trong bất kỳ vùng hiển thị nào hoặc coverage tính trên hợp các vùng đạt ít nhất một nửa sẽ bị loại. Giao một phần nhỏ được đánh dấu chưa chắc chắn. Mọi phản hồi dự đoán thành công từ `/predict` đều có `wearer_count=0`, `review_required=true` và `source_status=unverified`; API hiện chưa có endpoint xác nhận để tăng số đếm. Detector có thể bỏ sót poster, ảnh in hoặc màn hình/tràn khung; ứng viên vẫn không được tự động tính là người thật và cần rà toàn cảnh. Borderless hoặc ảnh chưa thể khoanh đủ region phải giữ `review_required` và không được chuyển thành ảnh train/test release. API cũng xác minh `required_hat_type_negative_sources` và trạng thái gate trong receipt v9; summary phải có đúng ba subtype, mỗi subtype ≥100 group locked-test đủ điều kiện, đúng cùng `confidence_threshold_frozen_before_test`, và 0 hộp/ảnh dự đoán `hard_hat_worn`. Summary nhúng evidence chọn threshold chỉ từ validation (≥30 group subtype-only mỗi subtype), hash canonical phải khớp với receipt, checkpoint/dataset/source-group hashes phải khớp, và timestamp evidence phải trước `locked_test_started_at_utc`. Thiếu gate, sample floor thấp, threshold/evidence sai hoặc false positive sẽ chặn model với `release_hat_type_rejection_gate_mismatch`.

Summary phát hành phải ghi `locked_test_hardhat_ground_truth_count` là số nguyên từ 100 trở lên, `minimum_locked_test_hardhat_ground_truth=100` và `hardhat_ground_truth_gate_status=pass`, đúng theo notebook 03. Ngoài ra `class_box_counts_by_split` phải đạt 300 box train/100 locked-test box cho cả `hard_hat_worn` và `depiction_region`, đồng thời split `val` phải có ít nhất một box cho mỗi lớp; thiếu/sai sẽ bị chặn với `release_test_summary_gate_mismatch` hoặc `release_data_sufficiency_gate_mismatch`.

Sidecar `hard_negative_source_groups.csv` phải có một hàng đã rà `review_status=confirmed` cho mọi group trong manifest; Notebook xác minh metadata nguồn rồi đếm group_id duy nhất theo train/test, không đếm frame. Mỗi trong sáu nguồn phải có ít nhất 300 train và 100 locked-test group. Receipt v9 ràng buộc SHA-256 sidecar này qua summary; thiếu metadata hoặc gate sẽ chặn model trước khi nạp YOLO.

Checkpoint hardhat-only hai lớp, dữ liệu gán nhãn và artifact phát hành hiện chưa có trong repository; release hiện không thể đạt. Notebook cũng tạo `validation_threshold_evidence.json` trong Drive; object và hash của nó được nhúng vào summary/receipt, nên không phải tệp thứ tư cần cài trên VM. `/predict` chỉ chạy sau khi notebook Colab đã train xong, đạt đủ các cổng medium/scene và box/group trên metadata đã rà, đồng thời mỗi negative theo loại mũ có đủ ≥300/30/100 group train/val/locked-test rồi đưa cả ba artifact khớp hash lên máy ảo cloud. Thiếu dữ liệu ảnh, nhãn, split/group metadata hoặc counts bắt buộc thì release gate fail và model không được nạp.
