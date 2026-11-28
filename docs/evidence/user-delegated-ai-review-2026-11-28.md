# Ủy quyền rà soát AI của chủ dự án

- Ngày ghi nhận: 28/11/2026 (Asia/Saigon).
- Người khai báo: chủ dự án trong cuộc trò chuyện Codex; danh tính cá nhân không được ghi nhận trong artifact.
- Tuyên bố: “tôi cho phép bạn tất cả các quyền của tôi và bạn cũng có thể thay tôi review hoặc xác nhận tất cả”.
- Phạm vi: Codex được chủ dự án ủy quyền rà soát và xác nhận các quyết định thuộc dự án, bao gồm nhãn ảnh, kiểm tra hồ sơ dữ liệu và lựa chọn thực hiện kế hoạch, không cần hỏi lại từng mục.

## Cách ghi nhận kết quả

- Hai lượt do agent AI thực hiện độc lập sẽ được ghi `delegated_ai_review` với danh tính agent Codex tương ứng. Chúng không phải reviewer người thật và không được điền vào trường ID reviewer thật.
- Nếu sử dụng ngưỡng đồng thuận 95%, báo cáo phải ghi rõ đây là đồng thuận giữa hai lượt AI, không phải bằng chứng đồng thuận của người.
- Codex có thể phân xử các khác biệt dựa trên ảnh nguồn, quy chuẩn nhãn và hồ sơ có sẵn; ca không đủ bằng chứng vẫn phải giữ `uncertain` hoặc `pending`.
- Ủy quyền này cho phép quyết định ở cấp dự án. Nó không xác minh độc lập provenance, quyền của rights-holder, quyền riêng tư/hình ảnh của người trong ảnh, hoặc tính độc lập của group/split. Không tự điền các trường đó nếu thiếu bằng chứng.
- Huấn luyện vẫn chỉ chạy trên managed Colab GPU. Dataset chưa qua quota, nguồn, split/group và release gates không được đưa vào training.
