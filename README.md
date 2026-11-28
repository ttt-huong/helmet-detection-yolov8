<h1 align="center">
  <img src="docs/assets/readme-banner.webp" alt="Phát hiện mũ bảo hộ bằng YOLOv8" width="100%">
</h1>

<p align="center">
  <a href="https://github.com/ttt-huong/helmet-detection-yolov8/actions/workflows/ci.yml?query=branch%3Amain"><img alt="Trạng thái build của nhánh main" src="https://github.com/ttt-huong/helmet-detection-yolov8/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://www.python.org/"><img alt="Python 3.12+" src="https://img.shields.io/badge/Python-3.12%2B-306998?logo=python&amp;logoColor=FFD43B"></a>
  <a href="https://pytorch.org/"><img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-20232B?logo=pytorch&amp;logoColor=EE4C2C"></a>
</p>

<p align="center">
  <a href="https://colab.research.google.com/github/ttt-huong/helmet-detection-yolov8/blob/main/notebooks/03_train_hat_types_colab.ipynb"><img alt="Mở notebook trên Google Colab" src="https://img.shields.io/badge/Colab-M%E1%BB%9F%20notebook-9A5D00?logo=googlecolab&amp;logoColor=F9AB00"></a>
  <a href="https://www.kaggle.com/code/maika123/notebookc7801aaccc/output?scriptVersionId=366157817"><img alt="Kết quả đánh giá trên Kaggle" src="https://img.shields.io/badge/Kaggle-K%E1%BA%BFt%20qu%E1%BA%A3-146489?logo=kaggle&amp;logoColor=20BEFF"></a>
  <a href="#video"><img alt="Xem video demo trong README" src="https://img.shields.io/badge/GitHub-Video%20demo-15754C?logo=github&amp;logoColor=white"></a>
  <a href="https://docs.google.com/document/d/10zXsgy_0juhgdIpex2dbZ8Y8d3KVphTD/edit"><img alt="Đọc báo cáo trên Google Drive" src="https://img.shields.io/badge/Google%20Drive-B%C3%A1o%20c%C3%A1o-344968?logo=googledrive&amp;logoColor=62D394"></a>
</p>

<p align="center">
  Định vị vùng đầu trong ảnh và video công trường với hai nhãn <code>helmet</code> và <code>bare_head</code>.<br>
  So sánh YOLOv8n, YOLOv8s, YOLOv8m và YOLOv5su trên bộ dữ liệu SHWD.
</p>

> **Phân biệt hai luồng:** Benchmark SHWD hai lớp, checkpoint YOLOv8m, video/webcam và bảng kết quả bên dưới là tài liệu legacy; chúng không phải kết quả, tiến độ hay trạng thái triển khai của pipeline hardhat-only hiện tại. Pipeline hardhat-only hiện tại giữ ontology review tám lớp trong browser, nhưng chỉ huấn luyện hai lớp model (`hard_hat_worn`, `depiction_region`) trên GPU Google Colab. Sau release, inference browser có thể chạy qua API Docker GPU local trên Windows hoặc API GPU trên VM cloud. Không huấn luyện trên máy local. Máy chủ tĩnh ở cổng `8765` chỉ mở giao diện rà nhãn; snapshot ngày 28/11/2026 lúc 15:52–15:53 +07 (GET recheck lúc 15:57) ghi nhận preview API model-less ở `7860` (`/livez` 200, `/health` 503 `checkpoint_missing`), nên chưa sẵn sàng inference. Dataset, checkpoint và artifact release của pipeline hardhat-only hiện chưa có trong repository.

<p align="center">
  <a href="#kết-quả">Kết quả</a> · <a href="#chạy-nhanh">Chạy nhanh</a> · <a href="#dữ-liệu-và-huấn-luyện">Dữ liệu</a> · <a href="#tái-lập-đánh-giá">Tái lập</a> · <a href="#phân-tích-lỗi">Phân tích lỗi</a>
</p>

## Demo video

https://github.com/user-attachments/assets/18b9df0f-b2cf-4409-93cb-5e2a1b83a708

**YOLOv8m phát hiện mũ bảo hộ tại công trường** (29 giây, 1080p).

[Chạy lại demo](#video) · [Clip gốc của aksinfo7 universe trên Pexels](https://www.pexels.com/video/construction-workers-building-urban-skyscraper-29888510/)

## Kết quả

Kết quả chính trên `test_clean` (1.087 ảnh). YOLOv8m đạt mAP cao nhất, còn YOLOv8n có tốc độ xử lý ảnh cao nhất.

| Mô hình | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | FPS trên ảnh |
| --- | ---: | ---: | ---: | ---: | ---: |
| YOLOv8n | 92,40% | 86,81% | 93,25% | 63,14% | **107,24** |
| YOLOv8s | **92,62%** | 89,79% | 94,60% | 65,11% | 54,95 |
| YOLOv8m | 92,43% | **90,73%** | **95,07%** | **65,48%** | 22,24 |
| YOLOv5su | 92,40% | 89,68% | 94,68% | 64,78% | 62,44 |

Đo FPS trên cùng GPU Tesla T4, batch 1, 300 lượt mỗi mô hình sau khi làm nóng, với ảnh đã giải mã. Demo video YOLOv8m đạt **16,79 FPS** khi tính cả đọc, thu nhỏ, suy luận, vẽ khung, ghi video trung gian và lưu ảnh mẫu. Mã hóa H.264 được thực hiện sau phép đo.

[Bảng kết quả cả ba tập](results/helmet_test_summary.csv) · [Bảng đo tốc độ](results/helmet_speed_summary.csv) · [Cấu hình huấn luyện](configs/experiment_config.json)

## Chạy nhanh

> **Lưu ý:** Bước cài Python/PyTorch và checkpoint `weights/v8m/best.pt` ngay dưới đây thuộc demo YOLOv8m legacy. Với pipeline hardhat-only hai lớp hiện tại, huấn luyện chỉ chạy trên Colab; sau khi có release, có thể thử inference qua Docker GPU trên Windows hoặc triển khai API GPU cloud.

Cần Python 3.12 trở lên và bản PyTorch phù hợp với máy. Các lệnh dưới đây chạy từ thư mục repo.

```sh
git clone https://github.com/ttt-huong/helmet-detection-yolov8.git
cd helmet-detection-yolov8
python -m pip install -r requirements.txt
```

Lấy checkpoint YOLOv8m đã huấn luyện, đặt tại `weights/v8m/best.pt`. Các tài liệu và checkpoint trên Drive hoặc Kaggle có thể cần quyền truy cập. [Thư mục checkpoint](https://drive.google.com/drive/folders/16BKDss7JgPP565ayg1fow6ZEUUdVbbzh)

### Bản thử gán nhãn trên trình duyệt

Mở giao diện rà soát ảnh từ thư mục gốc repo:

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory web
```

Truy cập `http://127.0.0.1:8765`. Giao diện cho phép tải ảnh vào phiên trình duyệt, vẽ hộp, chọn nhãn và xuất annotation JSON. Ảnh không được gửi lên máy chủ. Đây là công cụ gán nhãn, chưa kết nối mô hình nên không đưa ra dự đoán AI.

Chỉ thử inference sau khi notebook Colab tạo đủ ba artifact `best.pt`, `deployment_release.json` và `deployment_test_summary.json`; dùng Docker GPU local để thử browser hoặc cài trên VM GPU cloud theo [hướng dẫn inference](service/README.md). Summary ghi test khóa, hash dataset và sáu cổng theo từng bề mặt `poster`/`printed_photo`/`screen` × `depiction_only`/`mixed_scene`; mỗi ảnh phải có inventory instance và mapping vùng nguồn review ID 7 sang model class-1 region đúng ID/type/normalized box, box multiset khớp labels, không có duplicate geometry, `depiction_surface_instance_image_count == image_count`, và số false unverified hardhat candidates bằng 0. Cổng đủ mẫu còn yêu cầu tối thiểu 300 train/100 locked-test box cho mỗi lớp model, ít nhất 1 box mỗi lớp ở validation, và tối thiểu 300 train/100 locked-test group độc lập cho từng nguồn hard-negative trong sidecar. Biên nhận release v9 ràng buộc hash dataset, summary, checkpoint và `hard_negative_source_groups.csv`; API kiểm tra các quota trước khi nạp model. Với từng subtype traffic/cap/beanie, group chỉ đủ điều kiện khi mọi ảnh trong group sạch hardhat/subtype khác/surface và ít nhất một ảnh có subtype đó; chấm mọi ảnh của group. Notebook khóa threshold chỉ từ validation (≥30 group subtype-only mỗi subtype) và ghi evidence/hash trước test. Locked test cần ≥100 group mỗi subtype, 0 hộp/ảnh bị báo nhầm thành `hard_hat_worn`; receipt v9 ràng buộc evidence này. Đây là kiểm tra nhất quán artifact, không phải chữ ký số; biên nhận cũ bị từ chối. Khi API sẵn sàng, mở trang thử ảnh theo [hướng dẫn inference](service/README.md): dùng `127.0.0.1:7861` cho API Docker GPU local hoặc SSH tunnel tới API trên VM cloud. Trang gửi ảnh đến API cùng origin, hiển thị ứng viên hardhat đã loại hoặc cần rà, và luôn giữ số mũ bảo hộ đã xác nhận ở 0. Mở `demo.html` qua máy chủ tĩnh ở cổng 8765 chỉ xem được giao diện; inference cần API GPU đã nạp release hợp lệ (local hoặc cloud).

Browser giữ ontology review tám lớp để ghi rõ loại mũ và nguồn ảnh. Theo hợp đồng runtime, hai lớp mô hình là `hard_hat_worn` và lớp phụ `depiction_region`; lớp phụ này dùng để lọc nguồn ảnh, không phải nhãn PPE. Mũ bảo hiểm giao thông, mũ lưỡi trai, mũ len, đầu trần, mũ trong poster và mũ rời không được xuất thành nhãn model; ảnh đã rà chỉ chứa các loại mũ ngoài mục tiêu có thể được giữ với YOLO label rỗng làm ví dụ nền âm. Gán `depiction_region` cho toàn bộ poster, ảnh in hoặc màn hình có người. Hộp hardhat có tâm trong vùng hiển thị hoặc coverage hợp vùng đạt ít nhất 50% sẽ bị loại; giao dương nhỏ hơn luôn chưa xác định. Mỗi phản hồi `/predict` thành công đặt `wearer_count=0` và `review_required=true`; suy luận chỉ sẵn sàng khi đủ ba artifact phát hành đã được cài và API GPU local hoặc cloud khả dụng. Các mũ giao thông/cap/beanie chỉ được xác nhận là bị từ chối nếu từng cổng locked-test đạt 0 dự đoán hardhat; dữ liệu và checkpoint hiện chưa chứng minh cổng này đạt. Chưa có endpoint xác nhận thủ công để tăng số đếm. Xem [quy chuẩn gán nhãn](configs/helmet_types_labeling.md).

#### Chuyển JSON rà soát sang dữ liệu YOLO

JSON xuất từ trình duyệt không chứa ảnh. Giữ ảnh gốc trong một thư mục riêng; tên file phải khớp `file_name` trong JSON. Bản xuất `helmet-vision-review-v7` nhúng theo từng ảnh các trường `split`, `group_id`, `scene_type`, `depiction_surface_types`, inventory `depiction_surfaces`, `rights` và `image_review_status`, cùng annotation và trạng thái rà soát. V7 chốt semantics hardhat-only và yêu cầu `image_review_status` là `reviewed_empty` (không có annotation) hoặc `reviewed_with_labels` (có annotation đã rà xong); exporter chặn mọi ảnh còn chưa rà: chỉ `hard_hat_worn` được tính vào `real_wearer_count`; mũ khác chỉ là nhãn rà soát và không thành lớp model. Mỗi instance surface có `surface_id` riêng và `surface_type`; từng `depiction_region` tham chiếu đúng một instance bằng `depiction_surface_id`. Converter ghi mapping region `{surface_id, surface_type, box}` vào sidecar; `box` là YOLO xywh chuẩn hóa tám chữ số. Inventory giữ riêng từng poster/ảnh/màn hình kể cả khi nhiều instance cùng loại. Trường quyền sử dụng là **khai báo của người nhập dữ liệu**: converter chỉ kiểm tra tính đầy đủ và nhất quán của metadata, không xác minh giấy phép, sự cho phép hay nguồn ảnh bên ngoài. Chỉ chọn `training_use=approved` khi bạn đã xác nhận quyền dùng ảnh cho mục đích huấn luyện.

Giao diện nhận tối đa 20 ảnh mỗi phiên. Hãy xuất JSON v7 và lưu ảnh gốc sau mỗi batch; để gộp nhiều batch trước khi chuyển đổi, dùng script sau. Script chỉ gộp metadata/annotation, không chứa hay sao chép ảnh; nó kiểm tra format v7, class map, metadata cấp ngoài, UUID và tên ảnh không trùng, đồng thời không ghi đè file đầu ra đã có. Converter tiếp tục kiểm tra sâu split/group, rights, annotation và kích thước ảnh, đồng thời từ chối ảnh nguồn trùng byte SHA-256. Ảnh gần giống cần được rà thủ công và giữ cùng `group_id`/split:

```sh
python scripts/merge_review_json.py --inputs reviews/batch-01.json reviews/batch-02.json --output helmet-vision-review-v7.json
```

Giữ tất cả ảnh gốc tương ứng trong cùng `source_images/`, rồi chuyển đổi JSON đã gộp:

Với JSON `helmet-vision-review-v7`, converter đọc split và provenance ngay trong JSON nên không cần truyền CSV manifest:

```sh
python scripts/convert_review_json_to_yolo.py --review-json helmet-vision-review-v7.json --images-dir source_images --output-dir datasets/hardhat_only_v1
```

Với lệnh trên, converter tạo thư mục `datasets/hardhat_only_v1/`, ZIP, sidecar `test_scene_metadata.csv` và template `datasets/hardhat_only_v1_hard_negative_source_groups.csv`. `data.yaml` chỉ khai báo hai lớp model: `hard_hat_worn` ID 0 và `depiction_region` ID 1. Mọi ảnh được giữ; hộp review ID 0 được remap thành target ID 0, hộp review ID 7 thành support ID 1, các lớp review 1–6 không được ghi vào nhãn YOLO. Ảnh chỉ có mũ ngoài mục tiêu giữ `.txt` rỗng làm ví dụ nền âm. `split_manifest.csv` và sidecar nguồn ảnh giữ split/group, review-class counts, cảnh, surface và quyền. Hoàn tất mọi dòng template với `review_status=confirmed` cùng JSON arrays; không để trống hoặc giữ `pending`. Notebook đối chiếu tags theo group với scene, surface inventory và các review-class counts, đồng thời fail closed nếu thiếu/duplicate group. Inventory surface cùng mapping review class-7 region phải khớp một-một; box multiset phải khớp chính xác các model class-1 labels, duplicate geometry bị từ chối. Borderless hoặc vùng hiển thị chưa xác định phải giữ `review_required` và không vào dataset train/release. Mỗi `group_id` chỉ được nằm trong một split; gộp cùng người, video/phiên, cảnh và poster/màn hình để tránh rò rỉ giữa train, validation và test. Test khóa cần có từng loại `poster`, `printed_photo`, `screen` trong cả cảnh `depiction_only` lẫn `mixed_scene`; mỗi ảnh trong sáu cổng phải có đầy đủ mapping region theo từng physical surface và `depiction_surface_instance_image_count` phải bằng `image_count`. Release gate v9 còn yêu cầu ≥300 train/≥100 test boxes cho mỗi lớp model và ≥300 train/≥100 locked-test group độc lập cho từng nguồn hard-negative `poster`, `printed_photo`, `screen`, `loose_hat`, `mixed_scene`, `empty_background`. Kế hoạch đặt sàn 300 train/30 validation/100 locked-test nhóm cho từng loại traffic/cap/beanie theo [quy chuẩn gán nhãn](configs/helmet_types_labeling.md#sàn-dữ-liệu-cho-mũ-dễ-nhầm). Notebook 03 kiểm tra floor theo từng subtype/split ở preflight và final release gate; API xác thực các count đã khai báo trong `hat_type_negative_group_counts` theo schema và fail-closed nếu thiếu, sai hoặc thấp hơn floor với `release_data_sufficiency_gate_mismatch`. Hiện dữ liệu chưa chứng minh đạt các floor subtype. Chọn threshold cần ≥30 group subtype-only sạch mỗi loại trong validation; threshold được ghi vào `validation_threshold_evidence.json` và khóa theo hash trước locked test. Train cần đạt các quota box nêu trên; validation cần có ít nhất một box cho mỗi lớp model.

Các export v1–v6 không dùng trực tiếp cho release hardhat-only: v6 thiếu trạng thái annotation-complete theo ảnh; các bản cũ hơn có thể thiếu per-surface review hoặc dùng semantics bộ đếm cũ. Mở ảnh trong browser hiện tại, rà lại mũ và nguồn ảnh rồi xuất JSON v7. Mẫu rights CSV chỉ dành cho migration/đối chiếu dữ liệu legacy; converter hardhat-only không nhận manifest CSV.

Tải `datasets/hardhat_only_v1.zip`, `test_scene_metadata.csv` và template đã hoàn tất `hardhat_only_v1_hard_negative_source_groups.csv` lên `MyDrive/helmet_project/datasets/`; đổi tên template thành `hard_negative_source_groups.csv`. `split_manifest.csv` và `dataset_image_sources.json` đã nằm trong ZIP dưới `hardhat_only_v1/`. Sidecar source-group có một dòng cho mỗi `(split, group_id)`, yêu cầu `review_status=confirmed` và JSON list nguồn; `[]` chỉ hợp lệ sau khi người rà xác nhận nhóm không thuộc nguồn nào. Việc gán nhãn, khai báo nguồn/quyền và chuyển đổi dữ liệu có thể làm trên máy cá nhân; đây không phải huấn luyện. **Pipeline hardhat-only chỉ huấn luyện trên managed GPU runtime của Google Colab; không train trên máy local.** Kaggle chỉ xuất hiện trong script tiếp tục một run legacy.

Trước khi chọn dữ liệu ngoài, xem [đánh giá nguồn dữ liệu](docs/dataset_source_assessment.md): các bộ công khai đã rà soát chưa thay thế được hardhat labels và nguồn cảnh đã kiểm chứng.

### Huấn luyện phiên bản hardhat-only trên Colab

Huấn luyện hardhat-only và locked-test release gate chỉ chạy trên managed GPU runtime của Google Colab. Tải dataset ZIP, `test_scene_metadata.csv` và `hard_negative_source_groups.csv` đã rà lên Drive, sau đó mở [notebook Colab](notebooks/03_train_hat_types_colab.ipynb). Notebook có bước kiểm tra dữ liệu, chạy thử, train, tiếp tục từ checkpoint trên Drive, chọn threshold bằng group subtype-only trên validation và lưu `validation_threshold_evidence.json`; cell locked-test đối chiếu hash evidence rồi mới đánh giá. Notebook chỉ cấp receipt v9 cùng summary khi locked-test và sufficiency gates đạt. Trước mọi train, notebook yêu cầu đủ sáu nhóm surface/scene, class boxes tối thiểu 300 train/100 test cho cả hai lớp model, ít nhất 1 box mỗi lớp ở validation và 300 train/100 locked-test independent groups cho từng nguồn hard-negative trong kế hoạch. Đếm group_id độc lập, không nhân số khung. Mục tiêu ≥95% đồng thuận nguồn trên pilot 150–250 ảnh cần được đánh giá thủ công theo metric đã chốt trước. JSON v7 không đóng gói hai lượt rà thành một cặp; `scripts/compare_two_reviews.py` nhận hai export v7 riêng, báo đồng thuận trạng thái ảnh, metadata nguồn và nhãn/box trên roster, nhưng không tự quyết định đạt ngưỡng ≥95%. Mỗi ảnh nền phải có tệp nhãn `.txt` rỗng. Lệnh dưới đây chỉ kiểm tra cấu trúc và nhãn, không huấn luyện mô hình. Chạy kiểm tra trước khi tải bộ dữ liệu lên:

```sh
python scripts/validate_hat_dataset.py /path/to/data.yaml
```

`scripts/evaluate_hat_types.py` là evaluator độc lập để tạo báo cáo chẩn đoán; có thể chọn `--device cpu`. Script này không huấn luyện và không cấp receipt phát hành, kể cả khi báo cáo evaluator ghi các cổng đạt. Chỉ kết quả locked-test trong Notebook 03 chạy trên managed Colab GPU mới có thể cấp receipt.

Máy cá nhân có thể phục vụ trang tĩnh để xem giao diện trong trình duyệt. Không chạy train trên máy cá nhân. Sau khi Colab cấp đủ artifact release, API inference có thể chạy trên Docker GPU Windows để thử browser hoặc trên VM GPU cloud để triển khai; xem [hướng dẫn API](service/README.md). Repo hiện chưa kèm dataset hardhat-only, checkpoint đã train, biên nhận release hoặc báo cáo test phát hành, nên giao diện/API chưa thể đưa ra dự đoán AI thực tế.

### Video

Đây là demo cũ dùng checkpoint YOLOv8m của mô hình trước đó, không phải model hardhat-only hai lớp và không có bộ lọc poster/màn hình. Huấn luyện hardhat-only chỉ chạy trên Colab; sau khi release đạt cổng, inference AI có thể chạy trên Docker GPU Windows để thử browser hoặc trên VM GPU cloud.

Để tái tạo ví dụ trên, cần hai tệp đầu vào: clip gốc `12831498_3840_2160_30fps.mp4` (4K, 30 FPS, 874 khung hình) và checkpoint YOLOv8m đặt tại `weights/v8m/best.pt`. Cài FFmpeg có `libx264` và thêm vào PATH. Dùng một đường dẫn đầu ra mới cho mỗi lần chạy. [Tải clip gốc từ Pexels](https://www.pexels.com/video/construction-workers-building-urban-skyscraper-29888510/) · [Thư mục checkpoint](https://drive.google.com/drive/folders/16BKDss7JgPP565ayg1fow6ZEUUdVbbzh)

```sh
python scripts/demo_video.py --source /path/to/12831498_3840_2160_30fps.mp4 --weights weights/v8m/best.pt --output runs/demo
```

Sau khi chạy trên CPU, mở `runs/demo/demo_v8m_clip2.mp4` để xem video có khung dự đoán. Tệp `runs/demo/demo_log.txt` ghi cấu hình, số khung hình, SHA-256 của checkpoint và thời gian xử lý. [Xem đầu ra mẫu](https://drive.google.com/file/d/1Om8I1JsG1h8oeqn_iCFl5QcGQYJWE1D8/view)

### Webcam

Đây cũng là demo legacy dùng YOLOv8m cũ để chạy suy luận CPU trực tiếp. Nó không train mô hình và không phải cách chạy model hardhat-only trên cloud.

Cài MediaPipe trong cùng môi trường Python: `python -m pip install "mediapipe==1.2.2"`. Tạo thư mục `models/` ở thư mục gốc repo và tải hai model MediaPipe chính thức, lưu đúng tên: [`blaze_face_short_range.tflite`](https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite) và [`hand_landmarker.task`](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task). Webcam demo chạy cục bộ trên máy có webcam, dùng YOLOv8m trên CPU; không mở cửa sổ webcam trong Colab hoặc Kaggle. Nếu camera 0 không mở được, thử `--camera 1`; bấm `Q` hoặc `Esc` để thoát. Tài liệu: [MediaPipe Face Detector](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector) · [MediaPipe Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker).

```sh
python scripts/demo_webcam.py --weights weights/v8m/best.pt --models-dir models --camera 0
```

## Dữ liệu và huấn luyện

Tải tệp `VOC2028.zip` gốc. Script kiểm tra SHA-256 của tệp ZIP và danh sách chia tập trước khi dựng **7.581 ảnh, 120.561 hộp nhãn và 7 danh sách chia tập**. Chọn thư mục đầu ra mới. [Kho dữ liệu SHWD](https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset) · [Tệp ZIP gốc](https://drive.google.com/file/d/1qWm7rrwvjAWs1slymbrLaCf7Q-wnGLEX/view) · [Quy tắc nhãn](configs/label_rules.md)

```sh
python scripts/prepare_shwd.py --archive /path/to/VOC2028.zip --manifests manifests --output data/processed/helmet_yolo
```

| Tập | Ảnh | Vai trò |
| --- | ---: | --- |
| `val_clean` | 425 | Chọn checkpoint và ngưỡng cho phân tích lỗi |
| `test_clean` | 1.087 | Báo cáo kết quả chính sau khi lọc ảnh nghi trùng |
| `test` | 1.517 | Bộ chia gốc của SHWD, dùng tham chiếu |
| `test_clean_site` | 628 | Tập con theo nhóm nguồn `numeric` và `part2` |

Cả bốn mô hình SHWD đã hoàn thành 30 epoch với ảnh 640 px, batch 16 và seed 42; đây là kết quả benchmark legacy. Notebook 01 và các run Colab/Kaggle bên dưới chỉ là hồ sơ của luồng cũ, không phải cách huấn luyện pipeline hardhat-only hiện tại. Pipeline hardhat-only chỉ được train và chạy locked-test release gate bằng [Notebook 03 trên managed GPU runtime của Google Colab](notebooks/03_train_hat_types_colab.ipynb); không train local hoặc trên Kaggle.

<details>
<summary>Hồ sơ legacy: lần huấn luyện YOLOv5su bị gián đoạn</summary>

Khối này chỉ lưu hướng dẫn audit/chuẩn bị và liên kết tới đầu ra của một run cũ. Lệnh `resume` YOLOv5su hiện bị vô hiệu hóa ở mọi môi trường; không dùng để huấn luyện. Đặt `boxes_raw.csv` từ notebook Colab và bảy tệp trong `manifests/` vào `audit/`. Đặt `results.csv`, `weights/last.pt` có trạng thái optimizer, `weights/best.pt` và `args.yaml` nếu có vào `source_run/`. Các thư mục đầu ra phải là đường dẫn mới. [Đầu ra lưu trữ của lần chạy legacy trên Kaggle](https://www.kaggle.com/code/maika123/notebook7514cf8358/output?scriptVersionId=366138307)

```sh
python scripts/continue_v5su.py --audit-dir audit audit
python scripts/continue_v5su.py --audit-dir audit prepare /path/to/VOC2028.zip data/processed/helmet_yolo_resume
```

</details>

## Tái lập đánh giá

Đặt bốn checkpoint tin cậy tại `weights/v8n/best.pt`, `weights/v8s/best.pt`, `weights/v8m/best.pt` và `weights/v5su/best.pt`. Chọn thư mục đầu ra mới cho mỗi lần chạy.

### Kiểm tra bằng CPU

Kiểm tra SHA-256 của checkpoint, suy luận và chấm trên 24 ảnh cố định. Đọc kết quả tại `runs/smoke/smoke_summary.json`.

```sh
python scripts/smoke_repro.py --data-root data/processed/helmet_yolo --manifests manifests --weights weights --output runs/smoke
```

### Đánh giá đầy đủ bằng GPU

Dùng PyTorch có CUDA. Lệnh đánh giá bốn mô hình trên ba tập và lưu bảng kết quả, bảng đo tốc độ, dự đoán và biểu đồ.

```sh
python scripts/evaluate_helmet.py --data-root data/processed/helmet_yolo --manifests manifests --v8n weights/v8n/best.pt --v8s weights/v8s/best.pt --v8m weights/v8m/best.pt --v5su weights/v5su/best.pt --output runs/evaluation
```

Phiên tái lập T78 trên Tesla T4 cho cùng Precision, Recall và hai chỉ số mAP ở cả 12 lượt đánh giá. Notebook cần Internet và quyền gắn các đầu vào Kaggle có `v8n_best.pt`, `v8s_best.pt`, `v8m_best.pt` và `kaggle_resume_metadata.json` nằm cạnh `weights/best.pt` của YOLOv5su. [Notebook T78](notebooks/02_Tai_lap_danh_gia_T78.ipynb) · [Đầu ra tái lập](https://www.kaggle.com/code/maika123/fork-of-notebookc7801aaccc/output?scriptVersionId=368715960)

## Phân tích lỗi

Ở ngưỡng confidence 0,408 và IoU ghép hộp 0,50, Recall của lớp `helmet` là **42,00% (63/150)** với hộp có cạnh dài dưới 16 px sau khi quy cạnh dài ảnh về 640 px. Các hộp còn lại đạt **94,54% (1.507/1.594)**. [Bảng phân tích theo nhóm](results/strata_v8m_test_clean.csv) · [Danh mục 10 ca lỗi](results/error_case_index.csv)

<details>
<summary>Chạy lại phân tích và xuất ảnh minh họa</summary>

Đặt `boxes_raw.csv` và bản sao `manifests/test_clean.txt` vào `audit/`. Thư mục dự đoán `labels/` và tệp `metrics.json` được tạo ở cùng cấp bởi lệnh đánh giá YOLOv8m trên `test_clean`.

```sh
python scripts/analyze_saved_v8m.py --audit audit --labels runs/evaluation/evaluation/v8m/test_clean/labels --images /path/to/VOC2028.zip --out runs/errors
python scripts/plot_v8m_error_cases.py --analysis runs/errors --images /path/to/VOC2028.zip --out runs/error_examples.png
python scripts/analyze_image_conditions.py prepare --data-root data/processed/helmet_yolo --manifests manifests --matches runs/errors/ground_truth_matches.csv --output runs/conditions
python scripts/plot_occlusion_review.py --sample runs/conditions/occlusion_sample.csv --images data/processed/helmet_yolo/images --output runs/occlusion_review
```

Điền các cột `review_id,occlusion,note` trong `occlusion_blind.csv` sau khi rà ảnh gốc. Giá trị `occlusion` là `che`, `khong_che` hoặc `khong_ro`. Có thể dùng lại tệp nhãn đã lưu để đối chiếu kết quả. [Hồ sơ T52–T53](https://drive.google.com/file/d/1dQm7E3KNks1RJNK68uf3R-pL3cl-Mq87/view)

```sh
python scripts/analyze_image_conditions.py aggregate --conditions runs/conditions --review occlusion_blind.csv --matches runs/errors/ground_truth_matches.csv --output runs/conditions_summary
```

</details>

Phân tích che khuất mô tả mẫu 48 hộp, trong đó 15 hộp chưa đủ rõ để gán nhãn. Chỉ số độ sáng và độ nét được tính trên toàn ảnh. Nguồn công trường của từng ảnh trong `test_clean_site` chưa được xác minh. Mỗi mô hình được huấn luyện với một seed, và video demo chưa có nhãn chuẩn theo từng khung hình. [Giới hạn dữ liệu](configs/dataset_limitations.md)

## Cấu trúc repo

| Thư mục | Nội dung |
| --- | --- |
| [`notebooks/`](notebooks/) | Chuẩn bị, huấn luyện trên Colab và tái lập trên Kaggle |
| [`scripts/`](scripts/) | Dựng dữ liệu, đánh giá, phân tích lỗi và demo |
| [`configs/`](configs/) | Cấu hình thí nghiệm và quy tắc nhãn |
| [`manifests/`](manifests/) | Danh sách ảnh cố định của từng tập |
| [`results/`](results/) | Bảng kết quả và chỉ mục ca lỗi |
| [`docs/`](docs/) | [Checklist 13 nhóm kiểm thử](docs/checklist_kiem_thu.md) |

## Nguồn

- Bộ dữ liệu và tài liệu mô hình. [SHWD](https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset) · [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/) · [Ultralytics YOLOv5u](https://docs.ultralytics.com/models/yolov5/)
- Phép ghép hộp trong `analyze_saved_v8m.py` dựa trên mã phân tích của Tuấn. [Mã phân tích gốc](https://github.com/mahTuqn/Noron/blob/main/scripts/analyze_errors.py)
- Tham khảo bố cục README. [Ultralytics YOLOv5](https://github.com/ultralytics/yolov5) · [Roboflow Supervision](https://github.com/roboflow/supervision) · [Detectron2](https://github.com/facebookresearch/detectron2) · [MMDetection](https://github.com/open-mmlab/mmdetection)
