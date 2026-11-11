# Quy tắc nhãn và phạm vi kết luận — Nhóm17

Cập nhật hồ sơ ngày05/11/2026. Không thay đổi nhãn hoặc manifests đã dùng để huấn luyện.

## Quy tắc đã áp dụng
- `helmet` (id0): box mũ bảo hộ/đầu đội mũ theo nhãn SHWD `hat`; ba box `dog` trong ảnh000377 đã được xem và chuyển sang helmet ở bước trước.
- `bare_head` (id1): box đầu không đội mũ từ lớp `person`, không phải box toàn thân người.
- Đầu ra là lớp, bounding box và confidence cho đối tượng được phát hiện. Không suy ra một người không đội mũ chỉ vì mô hình không phát hiện helmet. Không ghép box đầu với người để kết luận tuân thủ nếu chưa có bước liên kết được kiểm chứng.
- VOC `difficult=1` (610box) đã giữ như nhãn bình thường trong YOLO; không tự ý đổi cách tính sau huấn luyện.
- Giữ bộ chia gốc và manifests đã chốt; pHash Hamming<=6 dùng lọc ảnh có ứng viên gần giống khỏi validation/test. pHash=0 không chứng minh trùng pixel. Không tuyên bố hết rò rỉ hoặc độc lập theo cảnh.

## Ca nhập nhằng — quy tắc cho lần kiểm tra/gán nhãn tiếp theo
Các quy tắc dưới đây mới được ghi thành văn bản, chưa phải bằng chứng mọi ảnh hiện tại đã được rà soát theo chúng.
- Mũ cầm tay, treo hoặc đặt trên bàn: không kết luận là người đang đội mũ. Ghi riêng trong hàng đợi kiểm tra nếu nhãn SHWD chỉ bao quanh mũ; không tự sửa nhãn đóng băng.
- Đầu bị che: chỉ kết luận có/không mũ khi có đủ bằng chứng nhìn thấy. Không nhìn thấy trạng thái thì ghi uncertain để kiểm tra; không tự gán bare_head.
- Nhãn không chắc hoặc box mơ hồ: ghi image_id, box, lý do và quyết định người rà soát. Nếu phát hiện lỗi ảnh hưởng thực nghiệm, lập phiên bản dữ liệu mới và đánh giá tác động; không âm thầm sửa tập test.
- Đầu quá nhỏ/mờ/thiếu sáng: phân biệt bỏ sót của mô hình với trạng thái nhãn không thể xác định; giữ minh chứng crop khi phân tích lỗi.

## Định nghĩa nhỏ dùng trong biểu đồ
`long_px_640 = max(xmax-xmin,ymax-ymin)*640/max(W,H)`; nhỏ nếu `long_px_640 <16`.
Đây là quy ước riêng theo cạnh dài sau resize giữ tỉ lệ, không phải diện tích nhỏ COCO; không tính phần padding hay làm tròn letterbox. Biểu đồ kích thước dùng train; biểu đồ lớp/nguồn dùng train,val_clean,test_clean riêng biệt. Tên nguồn numeric/part2 là tiền tố ID, không chứng minh bối cảnh công trường.
