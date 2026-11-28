# Ủy quyền quyết định trong dự án

- Ngày ghi nhận: 28/11/2026 (Asia/Saigon).
- Người khai báo: chủ dự án trong cuộc trò chuyện Codex; danh tính cá nhân không được ghi nhận trong artifact.
- Tuyên bố: “bạn hãy tự động duyệt thay tôi bất kì cái gì nhé”.
- Phạm vi áp dụng: Codex được chủ dự án giao tự quyết và duyệt các lựa chọn triển khai, chỉnh sửa code/tài liệu và thao tác dự án thuộc phạm vi công việc đã giao, không cần hỏi lại cho từng lựa chọn.

## Phê duyệt dự án

### Phê duyệt project cho pilot 175 ảnh

Ngày 28/11/2026, chủ dự án chỉ thị rõ Codex duyệt thay cho dự án đối với việc pilot review và mục đích training của 175 archive member. Codex `/root` là delegated project approver cho hai hoạt động đó. Căn cứ dự án là thông báo CC BY 4.0 tại [trang Construction-PPE chính thức của publisher](https://docs.ultralytics.com/datasets/detect/construction-ppe) cùng việc xác minh SHA-256 archive và byte/hash mapping của 175/175 member trong [báo cáo provenance](construction-ppe-175-source-provenance-check-2026-11-27.md). Manifest intake ghi `pilot_review_use=approved` và `training_use=approved` cho 175/175 ảnh, với `pilot_review_approved_by`/`training_approved_by` là `Codex /root (delegated by project owner in Codex conversation, 2026-11-28)` và ngày xác nhận 2026-11-28.

Đây là phê duyệt ở cấp dự án; nó không phải xác minh độc lập về provenance của từng ảnh, thẩm quyền của rights holder, hoặc quyền publicity/privacy của người được mô tả. `rights_holder`, `group_id`, project `split`, và reviewer A/B vẫn blank/unknown. Chưa có review nào của người thật hoàn tất; cần hai reviewer người thật độc lập trước khi bắt đầu các session. Phê duyệt training thể hiện ý định dự án, nhưng chỉ chạy training trên managed Colab GPU sau khi các data-sufficiency, group/floor và release gate còn lại đạt. Không chạy training local. Không coi phê duyệt dự án là bằng chứng rights-holder, review hoàn tất, hay release kỹ thuật.
