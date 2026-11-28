# Phân tích hiệu chỉnh pilot 175 ảnh — 2026-11-28

## Kết luận

Comparator normalized **không đạt** các cổng đồng thuận đã chốt: status 120/175 (68,6%); head/source disposition 21/462 (4,5%). Source metadata trùng 175/175, nhưng hai lượt đều ghi mọi ảnh là `other`, `clear` và không có `depiction_region`; đây là agreement mô tả, không xác nhận sự thật ảnh. Các số là AI–AI, không phải độ chính xác hay nhãn chuẩn.

## Dữ kiện

Nguồn: [`summary.json`](../../datasets/candidates/construction-ppe-pilot-draft/compare-v7-ai-a-b-normalized/summary.json), [`notes A`](../../datasets/candidates/construction-ppe-pilot-draft/ai-review-codex-a-final-notes.md), [`notes B`](../../datasets/candidates/construction-ppe-pilot-draft/ai-review-codex-b-final-notes.md), [ontology](../../configs/helmet_types_labeling.md) và [quyết định roster](../../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md). Comparator normalized dùng JSON A SHA `fa2db39fab6705d9853b3ad3c35dca92ad2178da31c8e743e88044b1c221d710`, B SHA `e93453fbbbc505c6b9a4a667a2536a2573c53d4acad34413da0ade3791127e69`; khớp đủ 175 SHA, không thiếu dòng hoặc box sai biên. Summary SHA `fabe175c72b0fc236b35e913dfb3ad46ee5923548791172731068fd3d0af765c`; `automated_95_percent_pass=false`.

| Chủ đề | Comparator và notes ghi nhận |
|---|---|
| Empty/status | A: 63 `reviewed_empty`, 112 `reviewed_with_labels`; B: 10/165. Có 55 khác status: 54 `A empty/B labels`, 1 ngược lại; 9 ảnh empty ở cả hai. Tất cả status đều terminal. |
| Box/class | A 156 box, B 327. `hard_hat_worn`: 109/217 (A/B), 14 ghép ở IoU ≥0,5, 95/203 unmatched. `bare_head`: 46/110, 7 ghép, 39/103 unmatched. A có một `beanie_worn`, B không; traffic/cap và depiction classes đều 0/0. |
| Uncertainty/source | A notes có 2 annotation `uncertain`; B có 150 candidate uncertain trong 327 annotation. Head/source: 154 `real_scene` + 2 unresolved ở A; 177 + 150 ở B. A ghi nhiều đầu xa/nhỏ không box; B ghi candidate uncertain khi còn định vị được. |
| Gate và source metadata | Head/source: 21/462 đồng thuận resolved; 441 box unmatched (152 unmatched unresolved) tính là non-agreement. Trong 21 box ghép, class ID và trạng thái trùng. Source metadata: 175/175; `clear/clear` 175. Cả hai notes nói không thấy người trong poster/ảnh/màn hình; cả hai có 0 region, nên geometry depiction zero/zero là unscored. |

[QA thị giác độc lập trên 13 ảnh](ai-b-unmatched-box-geometry-sample-2026-11-28.md) gồm 10 bất đồng và 3 controls: phát hiện lỗi coverage/geometry ở cả A lẫn B, có các trường hợp đúng ở mỗi bên và matched control IoU cao nhưng box vẫn chưa chặt. Đây là mẫu chẩn đoán có chủ đích, không ước lượng accuracy toàn tập.

## Nguyên nhân khả dĩ, không phải kết luận ground truth

- **Có bằng chứng về quy tắc empty/uncertain khác nhau:** 54/55 bất đồng status là A empty nhưng B có labels; notes mô tả A bỏ đầu quá nhỏ, B giữ candidate uncertain. **Suy luận:** khác ngưỡng giữa “không có đối tượng” và “có candidate chưa rõ” có thể là nguồn lớn của chênh lệch.
- **Có bằng chứng về coverage/localization yếu:** chỉ 21/462 head/source units ghép; sample hình học B cho thấy một số box nằm lệch. **Suy luận:** số box khác nhau và vị trí box cùng góp phần làm fail; comparator không cho biết reviewer nào đúng.
- **Class conflict chưa được cô lập:** trong 21 cặp ghép, class giống nhau; chỉ một candidate beanie lệch giữa hai lượt. Do phần lớn box không ghép, chưa thể xác nhận ranh giới lớp ổn. Các lớp zero/zero không chứng minh recall.
- **Source consensus cần thử thách:** 100% metadata agreement cùng 0 depiction box không chứng minh poster/screen không bị bỏ sót; chưa có reference truth trong comparator. Đây là rủi ro cần kiểm tra, chưa phải lỗi đã chứng minh.

## Rubric và điều kiện calibration đề xuất

1. **Anchor deck 18 ảnh, tách khỏi gate:** người adjudicator xác lập reference từ ảnh gốc, không dùng AI A/B hoặc YOLO upstream làm truth. Có: 2 hardhat thật; 1 mỗi traffic/cap/beanie; 2 bare head; 1 loose hat; 2 background rỗng; đủ 6 tổ hợp poster/printed-photo/screen × `depiction_only`/`mixed_scene`; 2 đầu xa/crop/che khuất với kết quả `uncertain`.
2. **Quy tắc quyết định:** rà toàn khung rồi phóng đại từng đầu; xác định nguồn/bề mặt trước loại mũ. `hard_hat_worn` chỉ hardhat công trường trên người thật; mũ khác là negative review class; `bare_head` cần thấy đủ rõ; mỗi bề mặt có người cần `depiction_region` riêng và đầu trong đó là `depicted_hat`. Crop không chứng minh `real_scene`.
3. **Empty, uncertainty, geometry:** `reviewed_empty` chỉ sau khi rà hết khung và không còn annotation/candidate ontology; không dùng nó thay cho “không vẽ được box”. Candidate định vị được nhưng không phân loại được thì ghi `uncertain`, không đếm wearer; source rõ có thể hoàn tất `reviewed_with_labels`. Source/region chưa rõ thì giữ `frame_source_status=review_required`. Box `*_worn` giữ trọn mũ và phần đầu thấy được, không lấy vai/thân; overlay phải kiểm tra tại ảnh gốc, top-left normalized `xywh`.
4. **Điều kiện calibration:** hai lượt độc lập khớp 18/18 anchor về status, source/scene, lớp và `uncertain`; mọi box định vị được đạt IoU ≥0,5 với reference; không người trong depiction nào bị tính là wearer. Nếu lỗi, giải thích lại rubric và lặp anchor trước khi blind pass.
5. **Blind pass và cổng:** chạy lại 2 lượt `delegated_ai_review` không xem draft cũ/kết quả đối phương trên đủ 175 SHA. Trước adjudication, đạt riêng image-status ≥95%/175, exact source metadata ≥95%/175 và head/source ≥95% tại IoU 0,5 như [PILOT_ROSTER_LOCK.md](../../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md). Unmatched, unresolved, missing/invalid đều non-agreement; giữ empty/empty trong mẫu. Ghi rõ đây là AI–AI. Nếu fail, giữ raw score là fail baseline, adjudicate mọi mismatch rồi tạo lượt độc lập mới; không dùng điểm sau adjudication làm pass trước đó.

Các ngưỡng trên là đề xuất để hiệu chỉnh, không đổi dữ liệu hiện có. Report này không sửa JSON/nhãn, không gán `group_id`/split và không đưa dữ liệu vào training. Quy trình AI độc lập hiện hành nằm trong [pilot workflow](../pilot_batched_review_workflow.md) và [ủy quyền review](user-delegated-ai-review-2026-11-28.md).
