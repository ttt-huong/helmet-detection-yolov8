# Kiểm tra capture intake template — 2026-11-28

## Phạm vi và kết quả parser

Đối chiếu [capture plan](controlled-data-capture-plan-2026-11-28.md), [capture intake CSV](../../configs/capture_session_intake_template.csv), [pilot intake](../pilot_intake_template.md), [rights manifest template](../../configs/hat_types_rights_manifest_template.csv), [split manifest template](../../configs/hat_types_split_manifest_template.csv) và [ontology](../../configs/helmet_types_labeling.md). Chỉ capture intake CSV mới và capture plan được cập nhật; hai manifest rights/split hiện hữu không bị sửa. Không chạy test suite.

Đọc CSV bằng Python standard-library `csv` và parse các ô JSON bằng `json`: header có **50 cột, 50 tên duy nhất**; có **2 dòng dữ liệu**, mỗi dòng đúng 50 trường; cả hai dòng có `record_status=EXAMPLE_ONLY_DO_NOT_INGEST`; các ô JSON đều parse được. Giá trị ảnh/SHA/time/source/consent đều là placeholder, rights ở `unknown` hoặc trống, `group_id` cuối trống và `split=UNASSIGNED`; không có dữ liệu cá nhân hay ảnh thật.

## Crosswalk nhất quán

- Capture plan yêu cầu nối từng ảnh với `sha256`, file gốc, capture/session, camera/operator/time/location, person ID giả danh, scene/content IDs, parent image và nguồn. CSV có các trường tương ứng; `image_source_reference` tách khỏi `source_reference` cho rights như pilot intake yêu cầu.
- Split manifest chỉ có `image_id,split,group_id,scene_type`. Capture CSV giữ đủ bốn trường và bổ sung `candidate_group_id`, cơ sở/trạng thái review group, liên kết ảnh liên quan, các split liên quan và trạng thái/người/ngày/bằng chứng audit leakage. Ví dụ để `group_id` và split thực chưa được gán.
- Rights manifest chỉ có `image_id,training_use,basis,source_reference,license_id,attribution`. Capture CSV giữ đủ các trường đó, đồng thời có SHA và quyền `pilot_review_use` tách khỏi training, permission evidence, rights holder và approver/date. `basis` để trống khi chưa biết, phù hợp pilot intake.
- Giá trị ví dụ `traffic_helmet_worn`, `cap_worn`, `depicted_hat`, `other`, `mixed_scene` và `screen` phù hợp danh mục ontology. JSON cho surface lưu riêng `surface_id`, `surface_type`, `content_id`; không trộn người thật với người trong hình.

## Gaps so với capture plan — phát hiện ở lượt đầu

Các điểm sau được phát hiện trong lượt audit đầu và mô tả trạng thái lúc đó; đề xuất sửa tối thiểu được thực hiện trong phần revalidation bên dưới, ngoại trừ reviewer IDs vẫn được giữ trong pilot intake riêng.

1. **Kích thước ảnh:** capture plan yêu cầu ghi kích thước gốc, nhưng CSV không có width/height. Sửa tối thiểu: thêm `image_width,image_height` hoặc ghi rõ chúng được lấy tự động ở ingest và gắn với cùng SHA-256.
2. **Consent theo từng người:** `person_ids_pseudonymous_json` có thể có nhiều ID, trong khi `person_consent_status/reference/scope` chỉ có một bộ giá trị cho cả ảnh. Nếu consent khác nhau giữa người, không biết trường nào áp dụng cho ai. Sửa tối thiểu: thay/đi kèm một `person_permissions_json` keyed theo `person_id` với status, evidence reference, scope và ngày; giữ consent evidence bên ngoài CSV.
3. **Quyền bề mặt depiction:** `depiction_surfaces_json` có thể có nhiều `surface_id`, nhưng `depiction_content_rights_status` và evidence reference hiện chỉ ở cấp ảnh; `license_id`/`attribution` cũng chỉ có một cặp chung. Một ảnh chứa nhiều poster/screen có thể có nhiều rights holder/terms. Sửa tối thiểu: thêm một `depiction_surface_rights_json` keyed theo `surface_id`/`content_id` chứa source URL, holder, permission status/evidence, license ID và attribution riêng cho từng bề mặt.
4. **Biến thể mũ quan sát được:** capture plan muốn theo dõi độ phủ nửa đầu/3⁄4/full-face và baseball cap/kê-pi, nhưng `candidate_review_classes_json` chỉ ghi class ontology. Sửa tối thiểu: thêm `observed_hat_variants_json` keyed theo người/box để thống kê coverage; giữ các biến thể này ở mức ghi chú, không tạo class mới.
5. **Thông tin reviewer:** pilot intake yêu cầu `reviewer_a_id` và `reviewer_b_id`, còn capture CSV không có hai trường. Đây là phân tách chấp nhận được nếu capture CSV chỉ là sổ provenance và reviewer IDs tiếp tục nằm trong manifest pilot đã khóa. Nếu muốn dùng CSV này làm intake review hợp nhất, thêm hai cột và adjudicator reference; không thay roster comparator năm cột.

Không thấy xung đột giữa group/split rule với ví dụ: cùng pseudonymous person ở hai session liên kết về một `candidate_group_id`, chưa có final `group_id` hoặc split. Cần giữ việc xác nhận độc lập của group và quyền ở các cổng hiện có trước khi điền manifest chính thức; CSV này là sổ hỗ trợ, không phải cơ chế tự duyệt hoặc tự ingest.

## Revalidation sau các sửa đổi — 2026-11-28

Các gap ban đầu đã được xử lý trong capture intake CSV mới và mô tả [capture plan](controlled-data-capture-plan-2026-11-28.md): có `image_width`/`image_height`; `person_permissions_json` ghi status, evidence, scope và ngày theo `person_id`; `depiction_surface_rights_json` ghi source URL, rights evidence, holder, license và attribution theo từng `surface_id`/`content_id`; `observed_hat_variants_json` ghi kiểu mũ quan sát theo chủ thể/nguồn. Capture plan nêu cách dùng các trường JSON này. Reviewer IDs vẫn thuộc pilot intake riêng, nên không thêm chúng vào sổ capture provenance.

Chạy lại Python standard-library `csv`/`json` parser trên bản cuối: **50 header, tất cả duy nhất; 2 dòng, mỗi dòng 50 trường; cả hai dòng mang marker `EXAMPLE_ONLY_DO_NOT_INGEST`; mọi trường JSON parse được.** Kiểm tra chéo thêm thấy mỗi `person_id` trong ảnh có đúng entry permission và mỗi `surface_id/content_id` có entry rights tương ứng. Hai dòng vẫn chỉ có hash/kích thước/time/source/permission placeholder, không có group/split thật hay dữ liệu cá nhân. Không chạy test suite và không sửa rights/split manifest hiện hữu.
