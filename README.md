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

## Đánh giá

Dùng Python 3.12 trở lên, PyTorch có CUDA và `pip install -r requirements.txt`. Lấy bốn checkpoint của nhóm từ Drive và đặt mỗi tệp tên `best.pt` trong thư mục tương ứng. [Thư mục các lần huấn luyện](https://drive.google.com/drive/folders/16BKDss7JgPP565ayg1fow6ZEUUdVbbzh)

```shell
python scripts/evaluate_helmet.py --data-root /path/to/helmet_yolo --manifests manifests --v8n weights/v8n/best.pt --v8s weights/v8s/best.pt --v8m weights/v8m/best.pt --v5su weights/v5su/best.pt --output runs/evaluation
```

Thư mục đầu ra cần là một đường dẫn mới. Script tạo kết quả theo tập, thông tin phép đo, CSV tốc độ và biểu đồ. [Kết quả kiểm thử cuối](results/helmet_test_summary.csv) · [Tốc độ trên ảnh](results/helmet_speed_summary.csv) · [Đầu ra Kaggle](https://www.kaggle.com/code/maika123/notebookc7801aaccc/output?scriptVersionId=366157817)

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

## Tái tạo video demo

Cài FFmpeg có `libx264` và đưa vào PATH. Dùng clip gốc 4K, 30 FPS đã dùng trong báo cáo cùng checkpoint YOLOv8m của nhóm. Script tạo MP4 1080p và log riêng của lần chạy CPU. [Nguồn clip](https://www.pexels.com/video/construction-workers-building-urban-skyscraper-29888510/) · [Video và log trên Drive](https://drive.google.com/drive/folders/1d4UUCgZ9figKF6BIRLrJe0rGwLsUl7oo)

```shell
python scripts/demo_video.py --source /path/to/12831498_3840_2160_30fps.mp4 --weights weights/v8m/best.pt --output runs/demo
```
