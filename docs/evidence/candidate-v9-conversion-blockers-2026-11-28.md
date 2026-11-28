# Điều kiện còn chặn chuyển candidate v9 sang YOLO — 2026-11-28

## Phạm vi

Đọc tĩnh [v9 proposal](../../datasets/candidates/construction-ppe-review-batch/candidate-review-v9-adjudicated-proposal.json), [v9 proposal report](../../datasets/candidates/construction-ppe-review-batch/candidate-review-v9-adjudicated-proposal-report.md), converter [convert_review_json_to_yolo.py](../../scripts/convert_review_json_to_yolo.py), validator [validate_hat_dataset.py](../../scripts/validate_hat_dataset.py), [rights intake draft](../../datasets/candidates/construction-ppe-review-batch/rights-intake-draft.csv), [pilot intake](../pilot_intake_template.md) và [ontology](../../configs/helmet_types_labeling.md). Không chạy converter/validator, không tạo dataset và không sửa JSON/CSV.

V9 SHA-256: `22c05cd4c35966db7cf946453855f0315fa0cec0fffa832af279a416283b8520`.

## Blockers trực tiếp của converter

### 1. Chưa có split/group trong embedded review JSON

V9 có `group_id=""` và `split=""` cho **19/19 ảnh**. Converter v7 đọc assignment nhúng trong từng image object; split phải là `train`, `val` hoặc `test`, còn `group_id` phải khác rỗng. Vì split đang rỗng, assignment đầu tiên bị từ chối; group cũng là lỗi độc lập. Các group liên quan không được tách qua split. Điền một CSV rights khác không sửa những trường nhúng này hay được CLI v7 dùng thay thế. [Converter, assignment checks](../../scripts/convert_review_json_to_yolo.py) (lines 201–208, 244–294).

Ngay cả khi được điền, converter chỉ kiểm tra group string không rỗng/ổn định và không nằm ở nhiều split; nó không chứng minh hai group độc lập. Group phải dựa trên person/session/video/scene/source-content và các quan hệ ảnh gốc theo [định nghĩa ontology](../../configs/helmet_types_labeling.md) (lines 87, 102–104); không suy độc lập từ tên file hay hash khác nhau.

### 2. Một annotation còn `uncertain`

BH4 (`train_source-04c535fcc25148fcc46c3e4d36902d57.jpg`, annotations index 2) giữ `class_id=4`, `bare_head`, nhưng `review_state="uncertain"`. Converter từ chối mọi annotation `uncertain`, kể cả class không được xuất thành YOLO; cần người rà phân xử trong browser trước khi tạo final export. Không thể đổi thành `confirmed` chỉ để qua gate. [Converter, annotation validation](../../scripts/convert_review_json_to_yolo.py) (lines 578–660); [v9 adjudication proposal](../../datasets/candidates/construction-ppe-review-batch/candidate-review-v9-adjudicated-proposal-report.md).

### 3. Không đủ bề mặt depiction cho split/model contract

Trong v9, cả 19 ảnh là `scene_type=other`, `frame_source_status=clear`, `image_review_status=reviewed_with_labels`; cờ rà `other` là true và surface inventories/region boxes đều bằng 0. Cấu hình này tự nhất quán cho từng ảnh, nhưng toàn batch không có `depiction_only` hay `mixed_scene`, cũng không có annotation `depiction_region` (model class 1). Khi viết dataset, converter yêu cầu locked test có ít nhất một `depiction_only` và một `mixed_scene`; ngoài ra, cả `hard_hat_worn` lẫn `depiction_region` phải có box trong train và val. Hiện tại thiếu cả test scene coverage lẫn depiction-region support, nên việc chỉ gán group/split không đủ. Cần dữ liệu depiction thật đã rà đủ surface inventory/region và scene type trước khi qua các cổng này. [Converter, v7 surface validation](../../scripts/convert_review_json_to_yolo.py) (lines 158–220, 578–700, 777–831); [ontology surface/test requirements](../../configs/helmet_types_labeling.md) (lines 28–32, 83–86, 115).

## Rights và provenance: phân biệt code gate với phê duyệt quyền

**Mechanical converter gate hiện khớp theo giá trị khai báo:** 19/19 embedded records có `training_use=approved`, `basis=permission`, và `rights.source_reference` không rỗng. Với `basis=permission`, converter không bắt buộc `license_id` hay `attribution`; vì vậy các ô này trống không tự gây lỗi code. Hàm rights chỉ kiểm tra các giá trị/chuỗi trên; nó không xác minh người cấp quyền, rights holder hoặc chuỗi nguồn ảnh. [Converter, rights check](../../scripts/convert_review_json_to_yolo.py) (lines 302–334).

**Cổng quản trị/provenance vẫn cần người có thẩm quyền xác nhận:** v9 trỏ `rights.source_reference` tới bản khai của chủ dự án; rights draft cũng ghi `pilot_review_use`/`training_use` approved theo khai báo ấy, nhưng `image_source_reference`, `rights_holder`, `license_id` và `attribution` còn trống cho 19 ảnh. `source_index.csv` và rights draft có hash, archive reference và member path để truy vết bytes, nhưng các trường đó không chứng minh rights-holder hoặc permission theo ảnh. Pilot intake nói rõ khai báo chưa phải xác minh độc lập provenance/rights-holder/license/attribution và yêu cầu evidence per-image bao phủ đúng hoạt động review và training. Điều này chưa được converter kiểm tra; không nên mô tả là lỗi validator. Trước khi dùng cho training, người phụ trách cần xác nhận nguồn/quyền thật và phạm vi permission theo chính sách dự án. [Pilot intake](../pilot_intake_template.md) (sections 3–4); [rights draft](../../datasets/candidates/construction-ppe-review-batch/rights-intake-draft.csv); [source index](../../datasets/candidates/construction-ppe-review-batch/source_index.csv).

V9 report cũng ghi đây là adjudicated **proposal**, chưa phải final human review/training release. Converter chỉ thấy JSON format/status/fields; không biết tên file có chữ proposal và không đo agreement hay xác nhận người duyệt. Cần đóng adjudication và xuất bản review cuối trước khi coi đây là đầu vào chính thức; riêng BH4 hiện còn uncertain.

## Những gì đã đạt và cổng downstream

- Schema tĩnh của v9: `helmet-vision-review-v7`, tám class IDs/names đúng; 19 ảnh unique; statuses terminal; 77 boxes normalized và trong bounds. 64 `hard_hat_worn` box có count 64, cùng 4 `cap_worn`, 8 `bare_head` (7 confirmed, 1 uncertain) và 1 `loose_hat`. Các box ngoài target không được xuất thành hardhat class; converter chỉ map review ID 0 → YOLO 0 và ID 7 → YOLO 1.
- [validate_hat_dataset.py](../../scripts/validate_hat_dataset.py) chạy sau khi dataset được tạo: yêu cầu `data.yaml` map đúng hai lớp `hard_hat_worn`/`depiction_region`, cả ba split có ảnh/labels, boxes hữu hạn/nằm trong `[0,1]`, không trùng image ID giữa split, và có box của **cả hai lớp trong train và val**. Nó không kiểm tra rights/group provenance; các cổng embedded group/split và rights ở converter vẫn cần trước đó.
- Ngoài khả năng tạo YOLO, batch 19 ảnh này chưa đủ điều kiện release của dự án: riêng batch có 64 `hard_hat_worn` boxes và 0 `depiction_region`, trong khi ontology đặt floors 300 train/100 locked-test cho từng model class. Các group floors và subtype floors cũng không thể đếm khi `group_id` rỗng; chúng là release gates riêng, không phải phần `validate_hat_dataset.py`.

## Kết luận

Các blocker máy đọc được chắc chắn là split/group rỗng, BH4 `uncertain`, thiếu `depiction_only`/`mixed_scene` trong test và không có `depiction_region` boxes cho train/val. Rights fields đạt kiểm tra hẹp của converter theo khai báo hiện tại, nhưng provenance/quyền nguồn chưa được xác minh độc lập theo intake policy. Không chạy converter/validator nên chưa kiểm tra decode JPEG hoặc kích thước bằng Pillow; 19 image hashes/dimensions đã được đối chiếu tĩnh trước đó với source index và rights draft.
