# Rà soát độc lập 8 box `bare_head` của proposal v8

## Phạm vi và tính toàn vẹn

Đã kiểm tra 8 annotation `class_id=4`, `class_name=bare_head` của `candidate-review-v8-adjudicated-proposal.json` trên toàn ảnh gốc và crop phóng đại quanh box. Proposal có SHA-256 `d7a184171e78b365c5633f8532969f3c0136ff116089371175ae559aac32c971`; cả 8 annotation hiện có `review_state=confirmed`, `counts_as_real_wearer=false`.

Proposal không chứa hash riêng cho từng ảnh. Vì vậy đã đối chiếu 6 file ảnh khác nhau với `source_index.csv` và image member trong ZIP nguồn: SHA-256 của file local khớp `source_index` và byte ảnh trong ZIP ở cả 6/6; chiều rộng/cao thực tế khớp đồng thời với JSON và `source_index` ở 6/6. Chỉ đọc image members, hash và kích thước; không đọc hoặc dùng upstream label files làm truth. Roster pilot không áp dụng cho batch này.

| Ảnh (các box) | Kích thước | SHA-256 |
|---|---:|---|
| `train_source-012007571544d108ad62099e53b8a827.jpg` (BH1–BH2) | 1536×1024 | `c01f98b97d0d9ca25253424259db6df3f99e3a81988c79d4135599758ad0f8fc` |
| `train_source-01472cb50a6610833e564bd5add532ee.jpg` (BH3) | 1536×1024 | `7cda1bb378c8e01f6c06364f4b2f9248c2795144601871f6a63f86faa5d911dd` |
| `train_source-04c535fcc25148fcc46c3e4d36902d57.jpg` (BH4) | 2048×1360 | `48e2e971bf0a41e1ae608e10866a0ae52108471cfde33d51259f184de6d8dd01` |
| `train_source-078aa002dcdc9f8ffd092bed4da44e59.jpg` (BH5) | 2048×1360 | `bfc83d07a60f0d8519fb10562d4358b8d7009ce74ea54452389e457a0c3fd753` |
| `train_source-21b5c4f737564d611ad72bf77e9ff8fc.jpg` (BH6) | 1536×1024 | `ee28272fd36ea1047dd879616c8e3fea0bd9c8939cd531506d8a353ff281b1ad` |
| `val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg` (BH7–BH8) | 1264×848 | `caf419a0881a9c970141b2f917a81aef7bd65d6b71c30c8b4c0f9ea229cdcddc` |

## Ontology và đánh giá box

Rubric yêu cầu `bare_head` là đầu người thật trong cảnh, nhìn đủ rõ và không đội loại mũ thuộc phạm vi; box bao vùng đầu theo phạm vi của box headwear, còn trường hợp đầu bị che/không phân biệt rõ phải để `uncertain`. Các box dưới đây được đổi sang tọa độ pixel xyxy để so sánh trực quan; đây là audit proposal, không phải sửa JSON.

| ID | File / box pixel xyxy | Đánh giá độc lập |
|---|---|---|
| BH1 | `train_source-012007571544d108ad62099e53b8a827.jpg` · `[1228,574,1292,624]` | Tóc và mặt người đang làm việc nhìn thấy, không có mũ; class `bare_head` rõ. Box đúng đầu nhưng cạnh dưới cắt phần mặt/cằm nhìn thấy. Nới box xuống nhẹ để bao hết đầu; không cần đổi class. |
| BH2 | Cùng ảnh · `[752,190,790,232]` | Người ở giữa quay lưng, tóc dài lộ rõ và không thấy mũ. Box nằm trên đầu/tóc, hơi ăn xuống vùng cổ/áo nhưng đủ dùng cho đầu nhỏ trong cảnh. Class và vị trí được hỗ trợ. |
| BH3 | `train_source-01472cb50a6610833e564bd5add532ee.jpg` · `[674,178,712,223]` | Người mang tấm ván có tóc/mặt rõ, không đội mũ. Box bao vùng đầu và một phần cổ, vị trí phù hợp; giữ `confirmed`. |
| BH4 | `train_source-04c535fcc25148fcc46c3e4d36902d57.jpg` · `[741,650,775,688]` | Box đặt đúng lên đầu người rất nhỏ ở xa trong kho. Có đầu/người trong cảnh, nhưng vùng chỉ khoảng 34×38 px và khối tối không đủ chi tiết để loại trừ chắc chắn mũ tối màu. Nên đổi sang `uncertain` cho đến khi người rà xác nhận không có mũ; box không cần dịch lớn. |
| BH5 | `train_source-078aa002dcdc9f8ffd092bed4da44e59.jpg` · `[636,654,706,732]` | Người cúi có tóc đuôi ngựa và mặt nghiêng lộ rõ, không thấy mũ. Box bao được đầu/tóc, không tràn sang người khác; class và hình học phù hợp. |
| BH6 | `train_source-21b5c4f737564d611ad72bf77e9ff8fc.jpg` · `[382,534,436,589]` | Tóc bạc và mặt của người cúi nhìn thấy, không đội mũ; mũ trắng cạnh hông không phải mũ đang đội nên không phủ định `bare_head`. Box hiện chỉ phủ phần trước/trái của đầu và cắt phần tóc phía sau. Vẽ lại rộng hơn và dịch sang phải để bao toàn đầu; class `bare_head` vẫn phù hợp. |
| BH7 | `val_source-ea0ae6faa6f33684ea285af1f6eae79c.jpg` · `[810,527,868,588]` | Người đàn ông áo đen có đầu trần nhìn thấy; box hiện nằm chủ yếu trên nền sàn giữa pallet và người, chỉ chạm mép đầu. Đây là lỗi vị trí, không phải bằng chứng class sai. Đặt lại box quanh đầu đang nhìn thấy ở bên phải box hiện tại. |
| BH8 | Cùng ảnh · `[1018,357,1057,395]` | Người mặc áo vàng phía sau pallet có tóc/mặt lộ rõ, không thấy mũ. Dù thân bị pallet/cột che, đầu đủ rõ; box ôm vùng đầu và class `bare_head` được hỗ trợ. |

## Kết luận

Trong 8 box, 7 người có bằng chứng hình ảnh phù hợp với `bare_head`; BH4 là trường hợp duy nhất nên giữ `uncertain` vì độ phân giải không đủ để loại trừ headwear tối màu. Về hình học, BH1 cần nới nhẹ, BH6 cần mở rộng/dịch để lấy trọn đầu, và BH7 cần đặt lại vì box nằm trên nền. Các box BH2, BH3, BH5 và BH8 phù hợp khi giữ ở độ phân giải hiện có.

`counts_as_real_wearer=false` trên cả 8 box là đúng theo rubric: `bare_head` không phải hard-hat target và không được cộng vào số người đội mũ bảo hộ. Không sửa JSON, không gán group/split, không sử dụng nhãn upstream làm truth, không train hoặc deploy.
