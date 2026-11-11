# Phát hiện mũ bảo hộ bằng YOLOv8

Dự án Nhóm 17 dùng dữ liệu SHWD với hai lớp `helmet` và `bare_head`. Nhóm so sánh YOLOv8n, YOLOv8s, YOLOv8m và YOLOv5su. Trên `test_clean`, YOLOv8m đạt mAP@0.5:0.95 là 65,48%. [Báo cáo](https://docs.google.com/document/d/10zXsgy_0juhgdIpex2dbZ8Y8d3KVphTD/edit)

## Chuẩn bị dữ liệu

Mở [notebook chuẩn bị dữ liệu](notebooks/01_Chuan_bi_va_khao_sat_du_lieu.ipynb) trên Colab. Các tệp trong `manifests/` chứa ID ảnh dùng trong thực nghiệm. Thư mục YOLO đã chuẩn bị cần có `images/`, `labels/` và các tệp `train.txt`, `val_clean.txt`, `test.txt`, `test_clean.txt`, `test_clean_site.txt` ghi đường dẫn tuyệt đối tới ảnh theo đúng thứ tự ID tương ứng. [Quy tắc nhãn](configs/label_rules.md) · [Giới hạn dữ liệu](configs/dataset_limitations.md)

Tập chính là `test_clean` (1.087 ảnh). Tập `test` gốc (1.517 ảnh) dùng để tham chiếu. `test_clean_site` (628 ảnh) là tập con lọc theo nguồn `numeric` và `part2`. Bối cảnh công trường của từng ảnh trong tập con chưa được xác minh.

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

## Tái tạo video demo

Cài FFmpeg có `libx264` và đưa vào PATH. Dùng clip gốc 4K, 30 FPS đã dùng trong báo cáo cùng checkpoint YOLOv8m của nhóm. Script tạo MP4 1080p và log riêng của lần chạy CPU. [Nguồn clip](https://www.pexels.com/video/construction-workers-building-urban-skyscraper-29888510/) · [Video và log trên Drive](https://drive.google.com/drive/folders/1d4UUCgZ9figKF6BIRLrJe0rGwLsUl7oo)

```shell
python scripts/demo_video.py --source /path/to/12831498_3840_2160_30fps.mp4 --weights weights/v8m/best.pt --output runs/demo
```
