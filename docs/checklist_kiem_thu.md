# Đối chiếu 13 nhóm kiểm thử

Các mức dưới đây mô tả phạm vi bằng chứng của từng nhóm case.

| Nhóm | Trạng thái | Bằng chứng và giới hạn |
|---|---|---|
| C01. Ý nghĩa lớp và khung | Đã đối chiếu | [Quy tắc nhãn](../configs/label_rules.md) ghi hai lớp và phạm vi dự đoán vùng đầu. Hình đối chiếu nhãn và dự đoán nằm ở Chương 4. |
| C02. Nhãn hợp lệ và ảnh nền | Đã đối chiếu tính hợp lệ | Script chuẩn bị đối chiếu 7.581 ảnh và 120.561 hộp. SHWD gốc không có ảnh hoàn toàn âm tính, theo [giới hạn dữ liệu](../configs/dataset_limitations.md). |
| C03. Phân bố và bộ chia | Đã đối chiếu | [Bảy manifest đã đóng băng](../manifests/) và quy tắc lọc theo pHash. Chưa xác minh được các tập độc lập theo cảnh. |
| C04. Khả năng huấn luyện và VRAM | Đã chạy | Notebook có bước chạy thử và kiểm tra VRAM. Bốn lần huấn luyện dùng cấu hình đã ghi trong [experiment_config.json](../configs/experiment_config.json). |
| C05. Lưu và khôi phục | Đã kiểm tra | YOLOv5su tiếp tục từ checkpoint trên Kaggle. Script kiểm tra nhanh xác minh SHA-256 và nạp thành công bốn checkpoint. |
| C06. Ca rõ và nhiều người | Đã kiểm tra định tính | Các lưới nhãn và dự đoán YOLOv8m cùng ảnh minh họa trong Chương 4 cho phép đối chiếu nhiều người trong một khung. |
| C07. Màu mũ và vật gây nhầm | Có ví dụ, thiếu tập riêng | Ca 000441 cho thấy mũ kê-pi bị báo là `helmet`. Chưa có mẫu gắn nhãn theo màu mũ để đo riêng. [Danh mục ca lỗi](../results/error_case_index.csv) |
| C08. Vật nhỏ và che khuất | Có bằng chứng | Có Recall theo kích thước và ví dụ định tính về đầu bị che trong ca 000321. Chưa có nhãn che khuất cho toàn tập. [Bảng phân tầng](../results/strata_v8m_test_clean.csv) |
| C09. Ánh sáng khó và ảnh nền | Có số theo độ sáng, thiếu ảnh nền | Có Recall theo độ sáng trung bình ảnh và ví dụ ca 000577. Chưa có tập ảnh nền hoàn toàn âm tính. [Bảng phân tầng](../results/strata_v8m_test_clean.csv) |
| C10. Chỉ số định lượng | Đã đo | [Kết quả ba tập kiểm thử](../results/helmet_test_summary.csv). AP theo lớp được lưu trong đầu ra Kaggle của phiên đánh giá. |
| C11. Tốc độ | Đã đo | Bốn mô hình đo trên Tesla T4, batch 1, có khởi động và đo lặp. [Bảng tốc độ](../results/helmet_speed_summary.csv). Phạm vi phép đo nằm trong script và protocol Kaggle. |
| C12. Video và lỗi đầu vào | Đã kiểm tra | Video và log nằm ở thư mục demo. Với đường dẫn video sai, CLI báo `File not found` và thoát mã 2. [Video và log](https://drive.google.com/drive/folders/1d4UUCgZ9figKF6BIRLrJe0rGwLsUl7oo) |
| C13. Báo cáo và tái lập | Đã kiểm tra trên mẫu CPU | Dựng dữ liệu từ ZIP gốc và chạy lại suy luận, đánh giá bốn mô hình trên 24 ảnh. Phép đánh giá đầy đủ và benchmark Tesla T4 đã thực hiện trên Kaggle, chưa lặp lại toàn bộ trong lượt kiểm tra này. |
