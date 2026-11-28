# Kế hoạch rà độc lập 175 ảnh

Đợt rà thử dùng danh sách 175 ảnh đã khóa theo SHA-256, chia thành 17 phiên cho mỗi người. Gói ảnh đã qua kiểm tra toàn vẹn. Hiện còn chờ chỉ định nhân sự và thu hai bản JSON v7 chính thức. [Hồ sơ khóa danh sách](../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md)

## 1. Chốt người và giao gói ảnh

- **Chủ dự án** chỉ định hai người rà độc lập A/B và một người thứ ba xử lý bất đồng. Chọn A/B có thể rà đủ 175 ảnh và áp dụng cùng quy tắc gán nhãn. Chọn người xử lý bất đồng có thể giải thích quyết định theo quy tắc. Điền ID của A/B vào cột `reviewer_id` trong bản sao tracker. Ghi tên hoặc ID của ba người và ngày hẹn nộp trong biên bản phân công. Chủ dự án có thể kiêm điều phối.
- **Điều phối** chạy `python scripts/validate_pilot_review_package.py` trước khi giao. Sau khi có người nhận vai và kiểm tra gói trả `PASS`, giao cho A/B cùng gói ảnh, hướng dẫn gán nhãn và tracker. Hai người dùng cùng phiên bản giao diện và quy tắc, với hồ sơ trình duyệt riêng. [Tracker 34 lượt rà](../datasets/candidates/construction-ppe-pilot-draft/pilot-175-review-session-tracker-template.csv) · [Quy trình giao ảnh](pilot_batched_review_workflow.md#1-khóa-roster-và-chia-batch)

## 2. Rà song song và thu hai bản JSON v7

- **A và B** mỗi người tự rà đủ 17 phiên. Trong thời gian rà, giữ riêng nhãn, bản nháp và bản xuất của mỗi người. Để bản rà sơ bộ bằng AI dành cho tra cứu ca khó sau khi đã lưu số đo đồng thuận ban đầu.
- **Sau từng phiên**, mỗi người xuất JSON v7, đối chiếu số lượng và tên ảnh với phiên tương ứng, ghi đường dẫn, số ảnh và SHA-256 của bản xuất vào tracker. Lưu đủ 34 tệp phiên để truy vết.
- **Điều phối** gộp riêng 17 tệp mỗi bên bằng `scripts/merge_review_json.py` để có hai tệp `reviews/reviewer-a/merged-v7.json` và `reviews/reviewer-b/merged-v7.json`. Đầu ra cần đủ 175 ảnh mỗi bên, không trùng ảnh và khớp đúng danh sách SHA-256 đã khóa ở bước đối chiếu. [Quy trình rà và gộp](pilot_batched_review_workflow.md#2-hai-lượt-review-tách-biệt)

## 3. Lưu kết quả đồng thuận trước khi xử lý bất đồng

**Điều phối** chạy `scripts/compare_two_reviews.py` với `--iou-threshold 0.5` vào một thư mục báo cáo mới, dùng hai bản gộp và ảnh gốc. Kiểm tra cả hai tập hash khớp danh sách 175 ảnh và xem các mục thiếu hoặc không hợp lệ trong báo cáo. Lưu hai bản gộp, `summary.json`, `disagreements.csv`, `box_matches.csv`, `per_image_agreement.csv` và `roster_issues.csv` làm hồ sơ ban đầu.

| Chỉ số trong `summary.json` | Điều kiện đạt |
| --- | --- |
| `image_review_status.agreement_fraction_over_full_roster` | Trạng thái rà khớp trên ít nhất 167/175 ảnh |
| `source_metadata_exact_agreement.fraction_over_roster` | Metadata nguồn khớp chính xác trên ít nhất 167/175 ảnh |
| `head_source_disposition.agreement_fraction` | Nhãn và phân loại nguồn của khung đầu-mũ đạt ít nhất 95% tại IoU 0,5 |

Đánh giá riêng từng tỷ lệ gốc. Khung không ghép được và ca chưa rõ được tính vào mẫu số chỉ số khung đầu-mũ theo quy tắc đối chiếu. Kết quả N/A hoặc dưới 95% ở bất kỳ chỉ số nào đều chưa đạt. Giữ nguyên danh sách và mẫu số của lần đo, kể cả khi có ảnh thiếu hoặc lần rà không hợp lệ. [Cách tính và lệnh đối chiếu](pilot_batched_review_workflow.md#4-đối-chiếu-bằng-rosterhash)

## 4. Xử lý bất đồng và bàn giao

- **Nếu cả ba chỉ số đạt**, người xử lý bất đồng xem từng mục lệch, kể cả ảnh thiếu hoặc rà không hợp lệ, khung không ghép được và ca chưa rõ. Nhật ký ghi SHA-256 ảnh, nội dung bất đồng, quyết định cuối và căn cứ. Xuất bản nhãn v7 đã chốt thành tệp riêng và giữ nguyên hai bản gốc.
- **Nếu có chỉ số chưa đạt**, giữ báo cáo gốc, dùng các ca bất đồng để làm rõ hướng dẫn, rồi tổ chức vòng rà độc lập mới trên cùng danh sách. Lưu bản xuất và báo cáo mới riêng theo vòng. Chỉ chốt nhãn sau khi vòng rà có cả ba chỉ số đạt trước xử lý bất đồng.
- **Chủ dự án** xác nhận bàn giao khi có hai JSON v7 độc lập, báo cáo trước xử lý cho thấy ba chỉ số đều đạt, nhật ký xử lý đầy đủ và một JSON v7 đã chốt. [Điều kiện trong kế hoạch dữ liệu](ke_hoach_hoan_tat_du_lieu.md#các-việc-cần-hoàn-thành)
