# Checklist calibration cho pilot review

Dùng trước một lượt blind mới. Đây là hướng dẫn thao tác; không phải dữ liệu hoặc nhãn. Tham chiếu [ontology](../configs/helmet_types_labeling.md), [calibration analysis](evidence/pilot-review-calibration-analysis-2026-11-28.md), [workflow v7](pilot_batched_review_workflow.md) và [các gate của roster](../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md). AI-A/B cũ, comparator và nhãn YOLO upstream chỉ là proposal, không phải ground truth.

## 1. Chuẩn bị — dừng nếu thiếu điều kiện

- [ ] Dùng bản ảnh gốc bất biến và roster đã khóa; khớp đủ **175 SHA-256**, tên file và kích thước cho mỗi reviewer. Không thêm/bớt ảnh trong blind pass.
- [ ] Chuẩn bị anchor deck **18 ảnh riêng** với reference do adjudicator được ủy quyền xác lập từ ảnh gốc: 2 hardhat thật; 1 mỗi traffic/cap/beanie; 2 bare head; 1 loose hat; 2 background rỗng; đủ 6 cặp `poster`/`printed_photo`/`screen` × `depiction_only`/`mixed_scene`; 2 đầu xa/crop/che khuất có candidate định vị được nhưng reference `uncertain`. Anchor ngoài roster chỉ để hiệu chỉnh, không tính quota hoặc training. Không dùng A/B hay upstream labels làm reference.
- [ ] Giao cùng thứ tự/batch nhưng giữ hai lượt AI độc lập: không xem draft cũ, annotation của nhau hoặc comparator trước khi export. Ghi `delegated_ai_review`, không ghi ID người review thật.
- [ ] Dùng ontology tám lớp hiện hành cùng review JSON v7; không nhập v1–v6/`poster_only` làm dữ liệu trực tiếp.

**Cổng dừng 1:** thiếu hash/ảnh, sai roster, anchor thiếu bất kỳ nhóm bắt buộc hoặc chưa có reference → không bắt đầu lượt blind.

## 2. Checklist cho từng ảnh

- [ ] Xem toàn khung trước; sau đó zoom từng người/đầu, mũ rời và bề mặt có người. Crop đầu/mũ không đủ chứng minh `real_scene`.
- [ ] Chọn nguồn trước lớp: `real_scene`, `depicted_surface` hoặc chưa rõ. Ghi `scene_type`: `other`, `depiction_only` hoặc `mixed_scene` đúng toàn cảnh.
- [ ] Rà từng đầu/mũ nhìn thấy: `hard_hat_worn` chỉ hardhat công trường trên người thật; traffic/cap/beanie là lớp negative review riêng; `bare_head` chỉ khi đầu thấy đủ rõ và không đội mũ thuộc phạm vi; mũ không đội là `loose_hat`.
- [ ] Với poster, ảnh in hoặc screen có người, inventory từng surface vật lý; `depiction_only`/`mixed_scene` cần surface type, mỗi instance cần đúng một `depiction_region` khớp `surface_id`/type/box, và đầu/mũ bên trong là `depicted_hat`. `other` không khai báo surface có người. Không gán người trong hình hiển thị là người thật đang đội.
- [ ] Nếu không chắc lớp/nguồn, không đoán: đánh dấu candidate `uncertain`, ghi lý do, không tính `real_wearer_count`. Nếu nguồn/bề mặt chưa xác minh được hoặc region bị bỏ sót, giữ `frame_source_status=review_required`.

## 3. Box và trạng thái hoàn tất

- [ ] Với `*_worn`, `bare_head` và `depicted_hat`, vẽ **một box mỗi đầu**, giữ trọn mũ và phần đầu nhìn thấy; `depicted_hat` chỉ đóng quanh đầu trong hình hiển thị. Không bao vai/thân, không kéo sang người khác. Dùng ảnh độ phân giải gốc để chỉnh.
- [ ] Dùng v7 normalized top-left `xywh`: `x,y` là góc trên-trái; `width,height` kéo từ góc đó. Mỗi box có kích thước dương, nằm trong biên ảnh. Xem overlay sau khi export để phát hiện lệch tỷ lệ/đặt sai đầu.
- [ ] `reviewed_empty` chỉ khi đã rà toàn khung và thật sự không còn annotation/candidate nào thuộc ontology. Không dùng “không vẽ được box” làm empty.
- [ ] Nếu có box/candidate, kể cả uncertain, trạng thái là `reviewed_with_labels`. Nếu source rõ nhưng không chốt được annotation, có thể hoàn tất với `uncertain`; converter vẫn loại uncertain. Nếu candidate không định vị được hoặc source chưa rõ, để lượt ở pending/needs-review và không xuất là hoàn tất.

**Cổng dừng 2:** bất kỳ ảnh terminal nhưng source unresolved, candidate chưa xử lý, status không khớp với danh sách annotation, depiction thiếu region, hoặc box sai biên/chuẩn → sửa hoặc giữ review-required; không đưa vào comparator như lượt hoàn chỉnh.

## 4. Calibration pass và blind gates

- [ ] **Anchor pass đề xuất:** hai lượt khớp reference trên **18/18 ảnh** về `image_review_status`, source/scene, class và uncertainty. Mọi box định vị được đạt IoU **≥0,5** với reference; không có người trong depiction bị tính là wearer. Một lỗi thì dừng, làm rõ rubric và chạy lại anchor.
- [ ] Sau anchor pass, chạy hai lượt độc lập trên đủ 175 SHA; xuất đúng 175 record mỗi lượt, terminal statuses, metadata hoàn chỉnh và v7 schema; đối chiếu annotation-status, surface inventory và mapping `depiction_region_surfaces` một-một. Chạy comparator normalized; lưu hash của inputs/outputs và raw metric trước adjudication.
- [ ] Giữ nguyên ba gate đã chốt, tách riêng:
  1. Image-status agreement **≥95% trên 175** (tối thiểu **167/175**).
  2. Exact source-metadata agreement **≥95% trên 175** (tối thiểu **167/175**).
  3. Head/source disposition agreement **≥95%** theo comparator tại IoU **0,5**.
- [ ] Ở gate 3, mẫu số gồm cặp box ghép và **từng box unmatched**; unmatched, unresolved, missing/invalid là non-agreement. Không bỏ `empty/empty` khỏi gate 1. `clear_status_metadata_agreement` là diagnostic, không thay gate 2. Đồng thuận ghi là AI–AI.
- [ ] Chỉ sau khi chốt raw rates mới adjudicate mọi bất đồng, box unmatched, unresolved và ảnh thiếu/không hợp lệ. Dù gate đạt, các uncertain vẫn chưa là nhãn training.

**Cổng dừng 3:** bất kỳ gate nào dưới 95%, metric thiếu mẫu số, comparator không khớp đủ 175 SHA, hoặc có export invalid → ghi kết quả fail, dừng mở rộng/training. Adjudicate để sửa hướng dẫn; lượt sau phải là hai export độc lập mới. Không dùng điểm sau adjudication để đổi ngược kết quả pre-adjudication.

## Phiếu kết quả bắt buộc

Ghi: roster/JSON/comparator SHA-256; số ảnh đủ/thiếu; số `reviewed_empty`/`reviewed_with_labels`; số uncertain; lỗi bounds/normalization; ba metric và mẫu số; anchor pass/fail; lý do dừng và người/agent adjudicator. Giữ `group_id`/project split trống cho tới quy trình adjudication và phân nhóm riêng.
