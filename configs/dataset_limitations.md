# Hạn chế dữ liệu và đánh giá

- SHWD trộn nhiều miền ảnh. Nhiều bare_head đến từ PartA lớp học và PartB ảnh Internet/đám đông; không diễn giải điểm tổng hợp là hiệu quả riêng công trường.
- Không có ảnh hoàn toàn không có box trong dữ liệu gốc. Vẫn đếm được false positives ở nền của ảnh có đối tượng, nhưng chưa đo riêng hiệu quả trên ảnh hoàn toàn âm tính.
- Không có metadata scene/video đã được xác minh để chia nhóm; các tập không được chứng minh độc lập theo cảnh. Ảnh khác số người vẫn có thể cùng cảnh.
- pHash<=6 loại ứng viên gần giống; có thể loại ảnh khác nội dung và bỏ sót ảnh liên quan. So sánh pixel bổ sung chỉ tìm trùng chính xác, không giải quyết toàn bộ rò rỉ theo cảnh.
- test_clean_site628 ảnh có1744helmet và334bare_head; subset này chỉ lọc nguồn numeric/part2, không được xác minh từng ảnh là công trường. Chỉ92ảnh có bare_head, nên kết luận về lớp này có giới hạn.
- Lớp helmet bao quanh mũ/đầu đội mũ; bare_head bao quanh đầu. Chưa kiểm tra toàn bộ ca mũ rời, mũ cầm tay, đầu che và nhãn nhập nhằng theo quy tắc mới.
- 610box difficult được tính như nhãn thường; cần ghi rõ khác biệt nếu so với bài dùng VOC ignore-difficult.
- Ultralytics đã cảnh báo tự sửa khoảng53JPEG; chưa lưu danh sách và hash trước/sau đầy đủ trong hồ sơ này.
- Các run hiện dùng một seed42,30epochs. Không suy ra khác biệt có ý nghĩa thống kê hay tối ưu tuyệt đối.
- Các số hiện có là validation; chưa có test cuối hoặc benchmark tốc độ chính thức.
- license_checked=True chỉ ghi nhận đã đọc nguồn. Repo SHWD có MIT, SCUT-HEAD ghi phạm vi nghiên cứu học thuật; quyền ảnh bên thứ ba và quyền phát hành lại toàn bộ dataset chưa được xác minh.
