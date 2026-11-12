# Phát hiện mũ bảo hộ bằng YOLOv8

Dự án Nhóm 17 dùng dữ liệu SHWD với hai lớp `helmet` và `bare_head`. Nhóm so sánh YOLOv8n, YOLOv8s, YOLOv8m và YOLOv5su. Trên `test_clean`, YOLOv8m đạt mAP@0.5:0.95 là 65,48%. [Báo cáo](https://docs.google.com/document/d/10zXsgy_0juhgdIpex2dbZ8Y8d3KVphTD/edit)

## Chuẩn bị dữ liệu

Tải [VOC2028.zip gốc](https://drive.google.com/file/d/1qWm7rrwvjAWs1slymbrLaCf7Q-wnGLEX/view) từ nguồn của bộ dữ liệu SHWD. Dùng Python 3.12 trở lên và chạy từ thư mục repo:

```shell
python scripts/prepare_shwd.py --archive /path/to/VOC2028.zip --manifests manifests --output data/processed/helmet_yolo
```

Script kiểm tra SHA-256 của tệp ZIP và các danh sách chia tập, rồi tạo 7.581 ảnh, 120.561 nhãn và bảy danh sách chia tập. Dùng thư mục đầu ra mới. [Notebook chuẩn bị dữ liệu](notebooks/01_Chuan_bi_va_khao_sat_du_lieu.ipynb) · [Quy tắc nhãn](configs/label_rules.md) · [Giới hạn dữ liệu](configs/dataset_limitations.md)

Tập chính là `test_clean` (1.087 ảnh). Tập `test` gốc (1.517 ảnh) dùng để tham chiếu. `test_clean_site` (628 ảnh) là tập con lọc theo nguồn `numeric` và `part2`. Bối cảnh công trường của từng ảnh trong tập con chưa được xác minh.

## Huấn luyện trên Colab

Notebook gồm 25 ô. 17 ô đầu chuẩn bị dữ liệu và chạy thử. Tám ô cuối ghi lại phần khôi phục dữ liệu, thiết lập thí nghiệm, huấn luyện chính và kiểm tra checkpoint. Chỉ chạy các ô huấn luyện khi cần tạo lại trọng số. Kiểm tra thư mục từng run trên Drive trước khi chạy, vì các ô sử dụng tên run và checkpoint đã định sẵn.

Ô cuối khởi chạy YOLOv5su trên Colab. Run đối chứng bị gián đoạn ở epoch 2 và được tiếp tục đến epoch 30 trên Kaggle. [Đầu ra YOLOv5su trên Kaggle](https://www.kaggle.com/code/maika123/notebook7514cf8358/output?scriptVersionId=366138307)

Để tiếp tục run YOLOv5su, dùng môi trường CUDA với các gói trong `requirements.txt`. Đặt `boxes_raw.csv` từ notebook chuẩn bị dữ liệu và bảy tệp trong `manifests/` vào thư mục `audit/`. Đặt `results.csv`, `weights/last.pt` có trạng thái optimizer, `weights/best.pt` và `args.yaml` nếu có vào `source_run/`. Đầu ra phải là thư mục mới.

```shell
python scripts/continue_v5su.py --audit-dir audit audit
python scripts/continue_v5su.py --audit-dir audit prepare /path/to/VOC2028.zip data/processed/helmet_yolo
python scripts/continue_v5su.py --audit-dir audit resume data/processed/helmet_yolo source_run runs/v5su_resumed
```

## Đánh giá

Dùng Python 3.12 trở lên, PyTorch có CUDA và `pip install -r requirements.txt`. Lấy bốn checkpoint của nhóm từ Drive và đặt mỗi tệp tên `best.pt` trong thư mục tương ứng. [Thư mục các lần huấn luyện](https://drive.google.com/drive/folders/16BKDss7JgPP565ayg1fow6ZEUUdVbbzh)

```shell
python scripts/evaluate_helmet.py --data-root /path/to/helmet_yolo --manifests manifests --v8n weights/v8n/best.pt --v8s weights/v8s/best.pt --v8m weights/v8m/best.pt --v5su weights/v5su/best.pt --output runs/evaluation
```

Thư mục đầu ra cần là một đường dẫn mới. Script tạo kết quả theo tập, thông tin phép đo, CSV tốc độ và biểu đồ. [Kết quả kiểm thử cuối](results/helmet_test_summary.csv) · [Tốc độ trên ảnh](results/helmet_speed_summary.csv) · [Đầu ra Kaggle](https://www.kaggle.com/code/maika123/notebookc7801aaccc/output?scriptVersionId=366157817)

[Notebook T78](notebooks/02_Tai_lap_danh_gia_T78.ipynb) chạy lại quy trình trên Tesla T4 với commit đã kiểm chứng. Gắn các đầu vào Kaggle đã được cấp quyền sao cho có `v8n_best.pt`, `v8s_best.pt`, `v8m_best.pt` và `kaggle_resume_metadata.json` cạnh thư mục `weights/` chứa `best.pt` của YOLOv5su. Bật Internet để tải mã và bộ dữ liệu gốc. [Đầu ra tái lập](https://www.kaggle.com/code/maika123/fork-of-notebookc7801aaccc/output?scriptVersionId=368715960)

| Mô hình | mAP@0.5:0.95 trên `test_clean` | FPS trên ảnh |
| --- | ---: | ---: |
| YOLOv8n | 63,14% | 107,24 |
| YOLOv8s | 65,11% | 54,95 |
| YOLOv8m | 65,48% | 22,24 |
| YOLOv5su | 64,78% | 62,44 |

FPS trên ảnh được đo trên Tesla T4 với batch 1, từ ảnh đã giải mã. `results/summary_smoke_probe.csv` và `results/speed_probe.csv` ghi các lượt chạy thử. Cả bốn mô hình hoàn thành 30 epoch. [Cấu hình huấn luyện](configs/experiment_config.json)

### Kiểm tra nhanh bằng CPU

Cài bản PyTorch phù hợp với máy và chạy `pip install -r requirements.txt`. Đặt bốn checkpoint tin cậy tại `weights/v8n/best.pt`, `weights/v8s/best.pt`, `weights/v8m/best.pt` và `weights/v5su/best.pt`. Script đối chiếu mã SHA-256 với kết quả đã lưu trước khi nạp trọng số.

```shell
python scripts/smoke_repro.py --data-root data/processed/helmet_yolo --manifests manifests --weights weights --output runs/smoke
```

Lệnh kiểm tra suy luận và đánh giá trên 24 ảnh cố định của `test_clean`. Kết quả trong `smoke_summary.json` dùng để kiểm tra quy trình. Để tái tạo bảng thực nghiệm và FPS, dùng lệnh đánh giá đầy đủ với CUDA ở trên.

[Checklist 13 nhóm kiểm thử](docs/checklist_kiem_thu.md) · [Số liệu phân tích lỗi](results/strata_v8m_test_clean.csv) · [Danh mục 10 ca lỗi](results/error_case_index.csv)

## Phân tích lỗi và điều kiện ảnh

Đặt `boxes_raw.csv` và `manifests/test_clean.txt` vào `audit/`. Dùng thư mục `labels/` do lệnh đánh giá YOLOv8m tạo trên `test_clean`, với `metrics.json` nằm cạnh thư mục đó. Phân tích dùng ngưỡng tin cậy 0,408 và IoU ghép hộp 0,50.

```shell
python scripts/analyze_saved_v8m.py --audit audit --labels runs/evaluation/evaluation/v8m/test_clean/labels --images /path/to/VOC2028.zip --out runs/errors
python scripts/plot_v8m_error_cases.py --analysis runs/errors --images /path/to/VOC2028.zip --out runs/error_examples.png
python scripts/analyze_image_conditions.py prepare --data-root data/processed/helmet_yolo --manifests manifests --matches runs/errors/ground_truth_matches.csv --output runs/conditions
python scripts/plot_occlusion_review.py --sample runs/conditions/occlusion_sample.csv --images data/processed/helmet_yolo/images --output runs/occlusion_review
python scripts/analyze_image_conditions.py aggregate --conditions runs/conditions --review occlusion_blind.csv --matches runs/errors/ground_truth_matches.csv --output runs/conditions_summary
```

`prepare` tạo bảng điều kiện ảnh và danh sách hộp để rà che khuất. Sau khi rà ảnh gốc, điền `review_id,occlusion,note` trong `occlusion_blind.csv`, dùng một trong ba nhãn `che`, `khong_che`, `khong_ro`. [Bảng số liệu và nhãn rà của nhóm](https://drive.google.com/file/d/1dQm7E3KNks1RJNK68uf3R-pL3cl-Mq87/view)

## Tái tạo video demo

Cài FFmpeg có `libx264` và đưa vào PATH. Dùng clip gốc 4K, 30 FPS đã dùng trong báo cáo cùng checkpoint YOLOv8m của nhóm. Script tạo MP4 1080p và log riêng của lần chạy CPU. [Nguồn clip](https://www.pexels.com/video/construction-workers-building-urban-skyscraper-29888510/) · [Video và log trên Drive](https://drive.google.com/drive/folders/1d4UUCgZ9figKF6BIRLrJe0rGwLsUl7oo)

```shell
python scripts/demo_video.py --source /path/to/12831498_3840_2160_30fps.mp4 --weights weights/v8m/best.pt --output runs/demo
```

## Demo webcam

Cài thêm `mediapipe==1.2.2`. Đặt hai tệp MediaPipe `blaze_face_short_range.tflite` và `hand_landmarker.task` trong `models/`. Dùng checkpoint YOLOv8m của nhóm và chạy trên máy có camera cùng môi trường đồ họa OpenCV. Bấm `Q` hoặc `Esc` để thoát. [Mô hình phát hiện mặt](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector#models) · [Mô hình nhận diện bàn tay](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models)

```shell
python scripts/demo_webcam.py --weights weights/v8m/best.pt --models-dir models --camera 0
```
