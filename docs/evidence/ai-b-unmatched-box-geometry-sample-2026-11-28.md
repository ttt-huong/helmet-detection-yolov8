# Kiểm tra hình học box A/B: mẫu 13 ảnh

## Phạm vi và tính toàn vẹn

Đã xem ảnh gốc trích từ ZIP pilot khóa và overlay A/B ở kích thước đầy đủ. Mẫu có chủ đích phân tầng: 10 bất đồng (6 ảnh A-empty/B-labeled, 3 ảnh hai bên đều có nhãn nhưng box khác nhau, 1 ảnh A-labeled/B-empty) và 3 control có box ghép từ thấp đến cao IoU. Overlay dùng xanh lá cho A, đỏ cho B. Đây là kiểm tra chẩn đoán, không phải mẫu ngẫu nhiên và không dùng để ước lượng tỷ lệ lỗi toàn bộ 175 ảnh.

Mỗi ảnh trong mẫu đã được đối chiếu byte trích từ ZIP với SHA-256 và kích thước trong `pilot-roster.csv`; cả 13/13 đều khớp. SHA-256 roster là `fbd330cfcfcecdd39a3314898c35ca2eac2b9b75c3f86ba92e3122beb4ba4205`. Comparator được kiểm tra dùng A `fa2db39fab6705d9853b3ad3c35dca92ad2178da31c8e743e88044b1c221d710` và B `e93453fbbbc505c6b9a4a667a2536a2573c53d4acad34413da0ade3791127e69`.

Trong comparator `compare-v7-ai-a-b-normalized`, có 21 cặp box khớp không gian trên 462 đơn vị box (4,5%); 441 box không ghép. Cả 21 cặp đã ghép đồng ý class và `review_state`. B có 150 box `uncertain` (A có 2); tất cả 150 box bất định của B đều không ghép với box A. Trạng thái ảnh gồm 54 A-empty/B-labeled và 1 chiều ngược lại. Vì comparator tính box không ghép là không đồng thuận, tỷ lệ 4,5% phản ánh chủ yếu khác biệt về sự hiện diện/độ phủ và hình học box; nó không tự xác định nguyên nhân cho từng box.

## 10 bất đồng đã xem

| Mẫu | File | A / B | Quan sát trên ảnh gốc và overlay |
|---|---|---|---|
| D01 | `source-c285b53fb701de95fbfe70714765e8c7.jpg` | empty / 4 | Ba box `hard_hat_worn` bất định và một `bare_head` của B nằm trên sàn, thân người hoặc kết cấu thấp; không ôm đầu/mũ. Bất đồng coverage đi kèm lỗi định vị rõ. |
| D02 | `source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` | empty / 4 | B đặt cả bốn box quanh vùng thân/ngực của công nhân; đầu và mũ trắng nằm phía trên box. Sai lệch dọc xuống dưới rất rõ. |
| D03 | `ultralytics-ppe-nov2026-034.jpg` | empty / 4 | B có box hard hat lớn phủ cả mũ và phần thân; hai box `bare_head` rộng xuống vai; box `hard_hat_worn` bất định ở người nền không chặt vào đầu. Đây là coverage bổ sung có một số vị trí hữu ích nhưng độ chính xác hình học không đồng đều. |
| D04 | `ultralytics-ppe-nov2026-563.jpg` | empty / 2 | Một box B phủ đúng công nhân đội mũ xanh nhưng khá rộng; box còn lại đặt lên trụ nâng xe nâng, không phải đầu người. Cùng ảnh có phát hiện đúng và false positive hình học. |
| D05 | `source-c715790ce68e51f46da3fef5c618486a.jpg` | empty / 2 | Hai box `bare_head` bất định của B nằm trên phần cốt thép/ván khuôn ở tiền cảnh, không phải đầu. Cần duyệt lại toàn ảnh để quyết định hai người nhỏ ở xa có cần nhãn nào. |
| D06 | `ultralytics-ppe-nov2026-490.jpg` | empty / 1 | Box `bare_head` bất định của B ở mép trên ôm phần đầu/mặt bị cắt khung. Vị trí này hợp lý với bất định; không phải mọi box `uncertain` của B đều lệch khỏi đầu. |
| D07 | `ultralytics-ppe-nov2026-002.jpg` | 3 / 3 | Ba box A bắt đầu khoảng y=0,09–0,105; box B khoảng y=0,21–0,22. Box B bị đẩy xuống mặt/vai, bỏ phần trên mũ. B còn gán người giữa đang đội mũ trắng thành `bare_head`. Đây là ví dụ mạnh về lệch hình học kéo theo sai class. |
| D08 | `ultralytics-ppe-nov2026-033.jpg` | 3 / 4 | Ba box A nằm trên ba mũ vàng/trắng/xanh. Ba box B bị dồn vào vùng giữa, không theo đúng vị trí các đầu trái/phải; box `uncertain` thứ tư nằm ở tay/vùng bụng. Có cả lỗi bố trí box và box thừa, không chỉ bất đồng class. |
| D09 | `ultralytics-ppe-nov2026-097.jpg` | 3 / 3 | Hai box xanh của A ở trái/phải nằm trên khung gỗ trống. Các box đỏ của B phủ đầu ba người thật, dù còn rộng xuống mặt/vai. Đây là phản ví dụ rõ rằng A cũng có lỗi hình học nghiêm trọng và B đúng hơn trong ảnh này. |
| D10 | `ultralytics-ppe-nov2026-502.jpg` | 1 / empty | A gán `beanie_worn` cho khăn trùm hijab của người phụ nữ; quan sát ảnh cho thấy nhiều khả năng nhầm ontology. B không tạo box hard hat; empty của B hợp lý đối với hard hat, nhưng không chứng minh ảnh đã được gán đủ mọi lớp headwear khác. |

## 3 control có box ghép

| Control | File | IoU của cặp ghép | Quan sát |
|---|---|---:|---|
| C01 thấp | `ultralytics-ppe-nov2026-339.jpg` | 0,524 | Cặp ghép có IoU thấp; box A `bare_head` bên trái ở nền trống, trong khi một số box B đặt đúng hơn lên người/mũ. Một box B khác vẫn rộng. Khớp của comparator không đồng nghĩa cả hai box đúng. |
| C02 giữa | `ultralytics-ppe-nov2026-378.jpg` | 0,611 | A có box trên chồng gạch; cặp còn lại và box B bao phủ người đội mũ nhưng còn rộng. Đây cũng là control cho thấy A có box sai và B có thể bắt thêm người. |
| C03 cao | `ultralytics-ppe-nov2026-072.jpg` | 0,750 | Box A/B chồng nhau quanh công nhân đội mũ xanh; cả hai vẫn trùm xuống mặt/vai. IoU cao xác nhận độ chồng lấp tốt hơn, không xác nhận box chặt hoặc nhãn đầy đủ. |

## Hash và kích thước 13 ảnh

| Mẫu | Kích thước | SHA-256 từ roster; ZIP trích xuất khớp |
|---|---:|---|
| D01 `source-c285b53fb701de95fbfe70714765e8c7.jpg` | 1536×1024 | `5e80704990f94f5053372eaf2f46ae9fa45d9d9276bcd90fbe7808b7cce9194c` |
| D02 `source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` | 2048×1360 | `b94965fad5549c0a1610cb10514a98924e6f426b3874485614540feeae615e6b` |
| D03 `ultralytics-ppe-nov2026-034.jpg` | 2048×2048 | `6f3b810087fadb286759e512d7d63d4806cfdaaf88eb47cef3015e8b7f209692` |
| D04 `ultralytics-ppe-nov2026-563.jpg` | 2048×2048 | `baa663b3c64ac2ab71daa36c40341e59b399716b6407fc7913d8d7eabcf44ef9` |
| D05 `source-c715790ce68e51f46da3fef5c618486a.jpg` | 2048×1360 | `14b60296f00a3a13c557d0d003f59efc0819cc7d14b6d16899e2ad417dff1dd3` |
| D06 `ultralytics-ppe-nov2026-490.jpg` | 2048×1152 | `5e9614384efc6869f614a7250be995e84d34649e6cef712093a1eb24e0d92402` |
| D07 `ultralytics-ppe-nov2026-002.jpg` | 2048×1152 | `e18092e2a401f842394c17e5ffa098e8b8038aff5e5d19cee689c6efae9152a4` |
| D08 `ultralytics-ppe-nov2026-033.jpg` | 1152×2048 | `cae9cd2c1a0c538bd1ebbf53b2f73121992e7bf255cb341fd99919f68f2a7b50` |
| D09 `ultralytics-ppe-nov2026-097.jpg` | 2048×1360 | `8f8e36e9cd592b419f56efa83800cbe630371b850df8ed5ba9c8592d084c4b3f` |
| D10 `ultralytics-ppe-nov2026-502.jpg` | 2048×1152 | `b6b1fb583169c3ecda31ff13967c8c80d7e97c4feaf0b2fe673599e361499963` |
| C01 `ultralytics-ppe-nov2026-339.jpg` | 2048×1360 | `ca336d5d01e931817a27e6e9e1f7fcaa8b35f9b1d526b5213c86ad512e830414` |
| C02 `ultralytics-ppe-nov2026-378.jpg` | 1360×2048 | `c04d78075e82a80e7c0c935b3898d622307c462113ecb9348cae5bac8a9b3916` |
| C03 `ultralytics-ppe-nov2026-072.jpg` | 2048×1360 | `dac25a02d150964010272f57f2e98225630caf94b1621324479a1659f03a0ca1` |

## Đối chiếu upstream chỉ như proposal

Ba ảnh `source-c285…`, `source-cdc3…`, `source-c715…` có byte ảnh trùng chính xác với member tương ứng trong `ultralytics-construction-ppe.zip`. Trong nguồn này class 0 tên chung là `helmet`, class 6 là `no_helmet`; chúng không phải ground truth đã được adjudicate theo ontology pilot. Với hai ảnh đầu, các box `hard_hat_worn` của B đều có IoU 0 với các box class-0 upstream. Ở ảnh `source-c715…`, hai box `bare_head` bất định của B đều có IoU 0 với hai box class-6 upstream. Điều này củng cố dấu hiệu lệch vị trí trong các ví dụ cụ thể, nhưng không dùng upstream để tự động sửa hoặc chấp nhận nhãn.

## Kết luận và bước re-review

Trong 13 ảnh đã xem, có nhiều ví dụ box B nằm trên thân người, sàn/kết cấu hoặc trụ xe nâng; vì vậy mức ghép thấp không thể giải thích chỉ bằng B thận trọng hơn về `review_state`. Đồng thời, B có box đúng ở một số ảnh (như 097, 563) và có `uncertain` hợp lý ở đầu bị cắt (490); A cũng có box sai trên nền và một nhầm lớp headwear (097, 339, 378, 502). Không suy rộng các tỷ lệ này ra 175 ảnh.

Quy trình đề xuất: mở ảnh gốc độ phân giải đầy đủ; đối chiếu overlay A/B và box chưa ghép; xác định từng box có thực sự bám vào đầu hay không trước khi quyết định class/state; xóa hoặc vẽ lại box đặt trên nền/thân người; rà coverage toàn ảnh cho 54 trường hợp A-empty/B-labeled và trường hợp ngược chiều; giữ `uncertain` cho đầu thật sự không thể phân loại. Dùng upstream chỉ làm dấu gợi ý. Sau một lượt hiệu chỉnh, chạy lại comparator và kiểm tra tiếp các mẫu chưa ghép. Mẫu hiện tại chỉ chứng minh có lỗi hình học ở những ảnh nêu trên; chưa phân loại được nguyên nhân của mọi box trong tập.
