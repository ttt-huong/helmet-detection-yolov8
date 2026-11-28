# Backlog re-review pilot 175 ảnh — 2026-11-28

## Phạm vi và nguyên tắc

Backlog này biến các dấu hiệu trong [comparator normalized](../../datasets/candidates/construction-ppe-pilot-draft/compare-v7-ai-a-b-normalized/summary.json), [audit số học](comparator-v7-metric-arithmetic-audit-2026-11-28.md), [phân tích calibration](pilot-review-calibration-analysis-2026-11-28.md) và [mẫu geometry 13 ảnh](ai-b-unmatched-box-geometry-sample-2026-11-28.md) thành việc re-review có thể làm. Các dòng/box nêu dưới đây là **đối tượng cần rà**, không phải nhãn đúng.

**Trạng thái:** các mục P0–P5 là công việc tiếp theo, chưa được thực hiện theo backlog này. Mẫu pixel 13 ảnh là rà chẩn đoán trước đó, không phải hoàn tất backlog hoặc adjudication toàn roster.

- Không sửa JSON A/B hiện tại, không suy diễn nhãn từ upstream hoặc từ phía reviewer nào, không điền ID reviewer người thật và không tuyên bố gate đã đạt.
- Giữ nguyên các export và metric ban đầu làm baseline descriptive-only. Mọi pass mới phải là export độc lập sau calibration, cùng roster SHA-256.
- Nếu không đủ pixel để quyết định class/box/source, giữ `uncertain` hoặc `review_required`; không đổi thành `reviewed_empty` chỉ vì không vẽ được box.
- Ghi từng quyết định mới vào export/review log riêng có provenance; backlog này không phải quyết định adjudication.

## Baseline để chia việc

| Hạng mục | Comparator | Ý nghĩa cho backlog |
|---|---:|---|
| Image review status | 120/175 khớp; 55 khác | 54 ảnh A=`reviewed_empty`, B=`reviewed_with_labels`; 1 ảnh ngược chiều. Cả 9 ảnh empty/empty vẫn cần được xem như một kiểm tra coverage, không phải bằng chứng không có đối tượng. |
| Exact source metadata | 175/175 khớp | Không có mismatch cụ thể để adjudicate. Tuy vậy, cả 175 cặp đều ghi `scene_type=other`, `frame_source_status=clear`, không có surface/region; agreement không xác minh nội dung ảnh. |
| Head/source spatial units | 21/462 khớp; 441 unmatched | Có 135 box A-only và 306 box B-only. Trong unmatched, 152 đang `uncertain` (A=2, B=150); 289 còn lại là box `confirmed` nhưng không có box ghép ở lượt kia. |
| Các cặp đã ghép | 21/21 cùng class và review state | IoU pass không bảo đảm box chặt hoặc đầy đủ; controls C01–C03 vẫn có box rộng xuống mặt/vai. |

Các metric là AI–AI, không phải ground truth hoặc accuracy. `box_matches.csv` có hai lát ghép riêng (`review_class` và `object_source_spatial`); backlog về head/source phải lọc đúng `comparison=object_source_spatial`, không cộng hai lát.

## Backlog có thứ tự và điều kiện hoàn tất

### P0 — Khóa cách đọc rubric trước khi mở lại 175 ảnh

**Việc:** dùng anchor deck 18 ảnh theo [calibration analysis](pilot-review-calibration-analysis-2026-11-28.md) và thao tác trong [checklist calibration](../pilot_review_calibration_rubric.md): reference do adjudicator xác lập từ ảnh gốc, không lấy A/B cũ hoặc upstream làm truth; rà toàn ảnh rồi zoom; chốt source/scene trước class; giữ candidate định vị được nhưng chưa phân biệt là `uncertain`; `reviewed_empty` chỉ khi toàn khung không còn candidate; box `*_worn`, `bare_head`, `depicted_hat` phải giữ đủ đầu/mũ, không bao vai/thân, theo normalized top-left `xywh`. Deck reference gồm 2 hardhat thật, 1 mỗi traffic/cap/beanie, 2 bare head, 1 loose hat, 2 background rỗng, đủ 6 stratum depiction và 2 đầu xa/crop/che khuất `uncertain`. Hai lượt đối chiếu anchor độc lập trước khi mở blind pass trên 175 ảnh.

**Thứ tự phụ thuộc:** trước P1–P4. Chỉ bắt đầu vòng mới khi hai lượt review thống nhất cách ghi candidate chưa phân loại, người trong ảnh hiển thị, mũ ngoài mục tiêu và box bao quanh đầu/mũ. Nếu còn bất đồng rubric, giải thích lại rồi lặp anchor.

**Đầu ra kiểm tra được:** calibration log riêng; mọi quyết định có căn cứ pixel/khung; nếu dùng hai agent theo `delegated_ai_review`, ghi đúng loại lượt AI và giữ ID người thật là unknown. Anchor deck là kiểm tra rubric, không thay cho metric trên roster 175 và không cấp pass.

### P1 — Thử thách lại source/scene metadata, không coi 100% là truth

**Việc:** rà source và toàn cảnh cho đủ 175 ảnh, ưu tiên xác minh liệu ảnh có người/bề mặt poster, ảnh in hoặc màn hình, cảnh mixed/depiction-only, và trạng thái `frame_source_status`. Source phải được xác định trước khi chốt wearer/depicted hat. Nếu ảnh không đủ ngữ cảnh, để `review_required`.

**Phạm vi và tham chiếu:** `per_image_agreement.csv`, dòng vật lý 2–176 (175 ảnh). Không có ID mismatch riêng: cả 175 hàng hiện khớp tuple `other/clear/no surfaces`. Đây là rà lại có chủ đích để phát hiện lỗi đồng thuận có hệ thống, không phải sửa 175 nhãn đã chứng minh sai.

**Đầu ra kiểm tra được:** mỗi ảnh có source/scene review mới kèm bằng chứng quan sát; mọi surface phát hiện được có inventory/region nhất quán theo rubric. Không suy ra ảnh không có depiction chỉ vì cả A và B đều không vẽ region.

### P2 — Re-review 55 bất đồng trạng thái ảnh và kiểm tra empty/empty

**Việc:** với 55 ảnh dưới đây, mở ảnh gốc đầy đủ, rà toàn khung, rồi xác định trạng thái ảnh phù hợp theo rubric sau khi xử lý candidate/box. Riêng 54 trường hợp A-empty/B-labeled, kiểm tra từng box B có bám đúng đầu/mũ hay không và tìm coverage bị bỏ sót; trường hợp ngược chiều phải tìm lý do box A xuất hiện nhưng B không có. Sau đó kiểm tra 9 cặp empty/empty như một mẫu completeness; không tự động chấp nhận empty.

**Tham chiếu:** `per_image_agreement.csv`; số dòng là dòng vật lý có tính header.

| Dòng | File ảnh | Pair A/B |
|---:|---|---|
| 2 | `source-c285b53fb701de95fbfe70714765e8c7.jpg` | `reviewed_empty/reviewed_with_labels` |
| 3 | `source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` | `reviewed_empty/reviewed_with_labels` |
| 4 | `source-36e876b96b016d65e880cb345751bd72.jpg` | `reviewed_empty/reviewed_with_labels` |
| 5 | `source-903bd92aa69a20ccde63606d9b8e74af.jpg` | `reviewed_empty/reviewed_with_labels` |
| 6 | `source-4c8b02d254dd8190897f4ce0e54ef9f7.jpg` | `reviewed_empty/reviewed_with_labels` |
| 8 | `source-58c7f3d161f4a1348b91f9808ba107a3.jpg` | `reviewed_empty/reviewed_with_labels` |
| 9 | `source-61bbd52cd3ed3880b13a7a4f88e8b9f6.jpg` | `reviewed_empty/reviewed_with_labels` |
| 10 | `source-fbb201fd66f289e3ad4e6f1a71c2a282.jpg` | `reviewed_empty/reviewed_with_labels` |
| 14 | `source-596bdd3a39761003f3913916c3a97c55.jpg` | `reviewed_empty/reviewed_with_labels` |
| 15 | `source-4d6af6d0fce09bd9d6228c8525c2f2c5.jpg` | `reviewed_empty/reviewed_with_labels` |
| 16 | `source-5aef8f03a221e1d0f7dc1df4501dda5e.jpg` | `reviewed_empty/reviewed_with_labels` |
| 17 | `source-d9f9c995d964d8a06df134b5637ad554.jpg` | `reviewed_empty/reviewed_with_labels` |
| 19 | `source-32bc8ce2aa0fba5b92cebfee6d8a4459.jpg` | `reviewed_empty/reviewed_with_labels` |
| 21 | `source-d5d4d730d8fbb824c881beaa18b34d80.jpg` | `reviewed_empty/reviewed_with_labels` |
| 23 | `source-5dc89b08baaaa3f5098e90ea8e5d5f7e.jpg` | `reviewed_empty/reviewed_with_labels` |
| 25 | `ultralytics-ppe-nov2026-034.jpg` | `reviewed_empty/reviewed_with_labels` |
| 32 | `source-223442b1ecf2d156710f2b828bb05db2.jpg` | `reviewed_empty/reviewed_with_labels` |
| 33 | `source-5a67f7bc0dd29deee4039b7c839d6663.jpg` | `reviewed_empty/reviewed_with_labels` |
| 36 | `source-56088ecf75821c1b93f4015a2bc0a071.jpg` | `reviewed_empty/reviewed_with_labels` |
| 37 | `source-2dcc1cb94093fa4285e9392019a06378.jpg` | `reviewed_empty/reviewed_with_labels` |
| 39 | `ultralytics-ppe-nov2026-336.jpg` | `reviewed_empty/reviewed_with_labels` |
| 50 | `source-55914bf88946606112f27e935d1f3200.jpg` | `reviewed_empty/reviewed_with_labels` |
| 59 | `source-9a1a7af602890ceff8a7513dddfe1e10.jpg` | `reviewed_empty/reviewed_with_labels` |
| 67 | `source-7b3c67476e2c7d60e7de960c902aaf5b.jpg` | `reviewed_empty/reviewed_with_labels` |
| 73 | `ultralytics-ppe-nov2026-563.jpg` | `reviewed_empty/reviewed_with_labels` |
| 77 | `source-aaaa2bca13c5a4328f9f1b8058936c98.jpg` | `reviewed_empty/reviewed_with_labels` |
| 87 | `source-3fcdab28d51a8a73673fd1bd1bf917c0.jpg` | `reviewed_empty/reviewed_with_labels` |
| 90 | `source-1a83ec5c795cea29a4c342541c1056b2.jpg` | `reviewed_empty/reviewed_with_labels` |
| 92 | `source-2cf558de976172bb38d06497fed78904.jpg` | `reviewed_empty/reviewed_with_labels` |
| 93 | `source-1cf7cb3866d943a954bc8e591591e519.jpg` | `reviewed_empty/reviewed_with_labels` |
| 105 | `ultralytics-ppe-nov2026-600.jpg` | `reviewed_empty/reviewed_with_labels` |
| 111 | `source-5ff9631584ae41efd2b7f508e6b24947.jpg` | `reviewed_empty/reviewed_with_labels` |
| 113 | `source-a8c726058fc542d983d5eb9427f86f09.jpg` | `reviewed_empty/reviewed_with_labels` |
| 117 | `source-9ee9d4ea8bef38f97faecd6be074f904.jpg` | `reviewed_empty/reviewed_with_labels` |
| 128 | `source-c715790ce68e51f46da3fef5c618486a.jpg` | `reviewed_empty/reviewed_with_labels` |
| 129 | `source-0f1bcf865e6c2db6ebdc47be3bb206b7.jpg` | `reviewed_empty/reviewed_with_labels` |
| 131 | `source-1c60612624732b80742dd50ae6225c57.jpg` | `reviewed_empty/reviewed_with_labels` |
| 135 | `source-bfbb13f4dbe39c58cf7d0106cd8000f7.jpg` | `reviewed_empty/reviewed_with_labels` |
| 136 | `source-6b6114dea7ecbe5997f1f0393824508b.jpg` | `reviewed_empty/reviewed_with_labels` |
| 140 | `source-a36439d05ebf0f383997aed40d295074.jpg` | `reviewed_empty/reviewed_with_labels` |
| 141 | `source-c2222ec081577f813f03068f8641fc48.jpg` | `reviewed_empty/reviewed_with_labels` |
| 142 | `ultralytics-ppe-nov2026-502.jpg` | `reviewed_with_labels/reviewed_empty` |
| 146 | `source-2edf4fdf4d031044f1130ef13ef129cc.jpg` | `reviewed_empty/reviewed_with_labels` |
| 148 | `source-5fae4385b524dc38fa23bc4423a17c29.jpg` | `reviewed_empty/reviewed_with_labels` |
| 150 | `source-62f03e64233ccb5a3966914b379a424c.jpg` | `reviewed_empty/reviewed_with_labels` |
| 155 | `ultralytics-ppe-nov2026-054.jpg` | `reviewed_empty/reviewed_with_labels` |
| 156 | `source-a9654697f4739d0834ce644ae8a0ca79.jpg` | `reviewed_empty/reviewed_with_labels` |
| 165 | `source-b58c93c47793ff3f0010e6cf29c7ca98.jpg` | `reviewed_empty/reviewed_with_labels` |
| 167 | `source-3dec6deaf0d256258b125015a036bb67.jpg` | `reviewed_empty/reviewed_with_labels` |
| 171 | `ultralytics-ppe-nov2026-490.jpg` | `reviewed_empty/reviewed_with_labels` |
| 172 | `source-2e27333e41769f0937c3111892af7957.jpg` | `reviewed_empty/reviewed_with_labels` |
| 173 | `ultralytics-ppe-nov2026-090.jpg` | `reviewed_empty/reviewed_with_labels` |
| 174 | `source-305deca284bbf639bcdcc00671e240aa.jpg` | `reviewed_empty/reviewed_with_labels` |
| 175 | `ultralytics-ppe-nov2026-690.jpg` | `reviewed_empty/reviewed_with_labels` |
| 176 | `ultralytics-ppe-nov2026-390.jpg` | `reviewed_empty/reviewed_with_labels` |

### P3 — Rà 441 box unmatched: geometry trước class

**Việc:** dùng ảnh gốc + overlay, kiểm tra từng dòng spatial chưa ghép xem box có thực sự nằm trên đầu/mũ và bao đủ mũ/phần đầu nhìn thấy không. Kiểm tra coverage cả ảnh, không chỉ vị trí box đã có. Chỉ sau khi xác định vị trí mới áp dụng class/state theo rubric; xóa/vẽ lại chỉ trong một export review mới sau khi có căn cứ, không sửa A/B gốc.

**Phạm vi và bộ lọc:** `box_matches.csv`, `comparison=object_source_spatial`, `status=unmatched_a` hoặc `unmatched_b`. Bảng breakdown:

| Lượt | Box không ghép | Phân loại/state comparator | Việc cần làm |
|---|---:|---|---|
| A-only | 135 | 93 `hard_hat_worn/confirmed`; 39 `bare_head/confirmed`; 1 `beanie_worn/confirmed`; 2 `hard_hat_worn/uncertain` | Kiểm tra box đã bỏ sót ở B, box A trên nền/thân, coverage và mọi trạng thái không chắc. Không xem `confirmed` là bằng chứng đúng. |
| B-only | 306 | 113 `hard_hat_worn/confirmed`; 43 `bare_head/confirmed`; 90 `hard_hat_worn/uncertain`; 60 `bare_head/uncertain` | Kiểm tra các box candidate B có bám đầu/mũ; tách lệch geometry khỏi sai/missing class; mọi `uncertain` vào P4. |

Các ID sample cụ thể từ [báo cáo geometry](ai-b-unmatched-box-geometry-sample-2026-11-28.md): D01 `source-c285…` (B box ở sàn/thân), D02 `source-cdc3…` (B box ở thân), D04 `ultralytics-ppe-nov2026-563.jpg` (một box lên trụ nâng), D05 `source-c715…` (2 box trên kết cấu), D07 `ultralytics-ppe-nov2026-002.jpg` (box dồn xuống mặt/vai, có nghi vấn class), D08 `ultralytics-ppe-nov2026-033.jpg` (box gom sai đầu và box thừa), D09 `ultralytics-ppe-nov2026-097.jpg` (A box trên khung gỗ trống). D06 `ultralytics-ppe-nov2026-490.jpg` là cảnh đầu bị crop, minh họa rằng `uncertain` có thể là trạng thái phù hợp; không ép thành class chắc chắn.

Rà cả 21 matched boxes như một lượt quality check. Các số là dòng vật lý trong `box_matches.csv` (có header); mọi hàng đều lọc `comparison=object_source_spatial`, `status=matched`:

| Dòng | File ảnh | IoU | Class |
|---:|---|---:|---|
| 42 | `ultralytics-ppe-nov2026-520.jpg` | 0,569 | `hard_hat_worn` |
| 43 | `ultralytics-ppe-nov2026-520.jpg` | 0,648 | `bare_head` |
| 165 | `ultralytics-ppe-nov2026-339.jpg` | 0,524 | `hard_hat_worn` |
| 315 | `ultralytics-ppe-nov2026-484.jpg` | 0,661 | `hard_hat_worn` |
| 341 | `ultralytics-ppe-nov2026-378.jpg` | 0,611 | `hard_hat_worn` |
| 433 | `ultralytics-ppe-nov2026-255.jpg` | 0,571 | `hard_hat_worn` |
| 437 | `ultralytics-ppe-nov2026-259.jpg` | 0,621 | `hard_hat_worn` |
| 441 | `ultralytics-ppe-nov2026-451.jpg` | 0,669 | `hard_hat_worn` |
| 473 | `ultralytics-ppe-nov2026-330.jpg` | 0,657 | `hard_hat_worn` |
| 499 | `ultralytics-ppe-nov2026-055.jpg` | 0,543 | `hard_hat_worn` |
| 539 | `ultralytics-ppe-nov2026-459.jpg` | 0,610 | `hard_hat_worn` |
| 627 | `ultralytics-ppe-nov2026-233.jpg` | 0,571 | `hard_hat_worn` |
| 633 | `ultralytics-ppe-nov2026-587.jpg` | 0,636 | `hard_hat_worn` |
| 639 | `ultralytics-ppe-nov2026-072.jpg` | 0,750 | `hard_hat_worn` |
| 697 | `ultralytics-ppe-nov2026-372.jpg` | 0,723 | `hard_hat_worn` |
| 719 | `ultralytics-ppe-nov2026-282.jpg` | 0,747 | `bare_head` |
| 751 | `ultralytics-ppe-nov2026-704.jpg` | 0,555 | `bare_head` |
| 801 | `ultralytics-ppe-nov2026-632.jpg` | 0,623 | `bare_head` |
| 835 | `ultralytics-ppe-nov2026-203.jpg` | 0,579 | `bare_head` |
| 857 | `source-58be932a7b22ab7a7ee6cf126214beb0.jpg` | 0,538 | `bare_head` |
| 907 | `ultralytics-ppe-nov2026-446.jpg` | 0,554 | `bare_head` |

Controls C01 `ultralytics-ppe-nov2026-339.jpg`, C02 `ultralytics-ppe-nov2026-378.jpg` and C03 `ultralytics-ppe-nov2026-072.jpg` are listed above. Their observed boxes show that IoU match does not guarantee a tight or correct box.

### P4 — Giải quyết hoặc giữ nguyên các trạng thái uncertain

**Việc:** review riêng toàn bộ 152 box uncertain trước khi bất kỳ box nào được tính là resolved. Dùng ảnh gốc, phóng to và xem toàn cảnh/context. Chỉ nâng trạng thái nếu bằng chứng phân biệt được lớp/nguồn theo rubric; nếu không, giữ uncertain và không tính là wearer hoặc box đã chốt.

**Phạm vi/ID:** `box_matches.csv`, lọc `comparison=object_source_spatial`, `status=unmatched_*`, `review_state_*=uncertain`:

- A: 2 `hard_hat_worn` uncertain, dòng vật lý **382** (`ultralytics-ppe-nov2026-129.jpg`) và **420** (`ultralytics-ppe-nov2026-019.jpg`).
- B: 90 `hard_hat_worn` uncertain, dòng vật lý **6, 8–9, 22–24, 29–31, 36–39, 49–53, 66–69, 99–101, 107, 110–111, 140–142, 156–159, 174–177, 191, 233, 258–261, 266–269, 289–290, 295–297, 355–357, 385, 409–411, 461–463, 507, 532–533, 568–571, 583–585, 597–599, 605–609, 692–695, 701–703, 717**.
- B: 60 `bare_head` uncertain, dòng vật lý **25, 98, 115–117, 121–123, 151, 211, 291, 726–727, 731–733, 742–745, 758–759, 763–765, 771, 783–785, 788–789, 806–809, 817–819, 827–829, 845, 852–855, 889–891, 899–901, 909, 913–915, 917, 920–921, 925**.

Không kết luận chỉ từ `review_state` của A/B. Các dòng trên là review states chưa thống nhất/resolved trong comparator, không phải lệnh đổi nhãn.

### P5 — Kiểm tra riêng ontology/class, rồi blind pass mới

**Việc:** sau P0–P4, kiểm tra class theo rubric trên export/review log mới. Một ứng viên `beanie_worn` A-only ở `ultralytics-ppe-nov2026-502.jpg` xuất hiện trong dòng **791** của `box_matches.csv`; sample D10 cho thấy khả năng nhầm hijab với beanie. Đây là câu hỏi ontology cần rà bằng pixel/rubric, không phải căn cứ tự sửa thành class khác. Trong 21 cặp ghép spatial, class/state đã trùng; không dùng điều đó làm bằng chứng các class ngoài các box ghép đã được phân biệt tốt.

Sau khi các lượt đọc rubric ổn định, chạy hai lượt mới độc lập, blind trên đủ 175 SHA trong [roster đã khóa](../../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md), không xem draft cũ/kết quả lượt kia trước khi nộp. Ghi loại review là AI delegated nếu là agent; reviewer người thật không có ID thì để unknown. So sánh lại status, exact source metadata và head/source tại IoU 0,5; lưu raw comparator mới tách khỏi baseline này. Nếu bất kỳ metric nào dưới 95%, giữ gate fail, adjudicate các bất đồng rồi mới mở lượt mới.

## Đầu ra và điều kiện dừng

1. Calibration log/anchor outcome, không ghi nhãn dự án thay cho evidence.
2. Review log mới có roster SHA, file/box reference, decision + pixel rationale hoặc trạng thái còn uncertain/review_required; provenance reviewer đúng sự thật.
3. Comparator mới và audit số học mới; không ghi “pass” nếu cổng chưa đạt ≥95% riêng từng metric trước adjudication theo quy trình.

Nếu chưa xác định được source, class hoặc box bằng ảnh gốc, dừng ở `uncertain`/`review_required`; không đưa ảnh đó vào train/release. Không có thao tác nào trong backlog này tự cấp split/group, quyền sử dụng, human A/B identity, training eligibility hay release approval.
