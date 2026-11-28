# Audit số học metric comparator v7

## Kết luận

Đối chiếu read-only giữa `summary.json`, `per_image_agreement.csv`, `box_matches.csv`, roster và `scripts/compare_two_reviews.py` không tìm thấy lỗi tính metric hoặc ảnh thiếu. Ba số trong cổng pilot được tính đúng: image review status **120/175 = 68,57%**; source metadata **175/175 = 100%**; head-source disposition **21/462 = 4,55%**. Với ngưỡng ≥95% ghi trong checklist, chỉ metric source metadata đạt; comparator vẫn đánh dấu `automated_95_percent_pass=false` và yêu cầu adjudication.

## Kiểm tra roster, missing và status ảnh

- `pilot-roster.csv`: 175 dòng, 175 SHA-256 duy nhất, file SHA-256 `fbd330cfcfcecdd39a3314898c35ca2eac2b9b75c3f86ba92e3122beb4ba4205`.
- `per_image_agreement.csv`: 175 dòng và 175 SHA-256 duy nhất. Summary cũng ghi 175 image rows cho mỗi review, hai hash set bằng roster, không có hash thừa/thiếu, không có diagnostics, 175/175 source file pairs đã xác minh; không có incomplete image status. `source_metadata_comparable` và `box_comparable` đều true trên 175 dòng.
- Các status pair: 111 `reviewed_with_labels/reviewed_with_labels`, 9 `reviewed_empty/reviewed_empty`, 54 `reviewed_empty/reviewed_with_labels`, 1 `reviewed_with_labels/reviewed_empty`. Do đó 120 agreement và 55 disagreement trên toàn roster: `(111 + 9)/175 = 68,5714%`.
- Cả 9 ảnh empty/empty đều có `annotations=[]` ở hai phía. Chúng được tính là 9 status agreements và vẫn nằm trong mẫu số metadata 175. Chúng không tạo box agreement units. Số ảnh zero annotation/zero object boxes là A=63, B=10; hai số này không thay mẫu số 175 của status hoặc metadata.

## Source metadata: 175/175

`source_metadata_exact_agreement` là phép so tuple chính xác, không phải đánh giá nội dung bằng người. `source_tuple()` trong code gồm `scene_type`, `frame_source_status`, cờ rà người trong cảnh `other` (khi áp dụng), loại surface, số inventory theo surface và số depiction-region theo surface. Hai export có 175 tuple khớp, 175 dòng comparable và không có mismatch field; `clear/clear` cũng là 175/175. Công thức gate là `175/175 = 100%`.

Đây là độ trùng khớp giữa hai bản review theo các field được nêu. Nó không xác minh độc lập rằng scene/surface được diễn giải đúng, và không bao gồm `rights`, `group_id` hoặc `split` trong tuple.

## Head-source disposition: 21/462

`summary.json` và tổng các đối tượng `object_source_agreement` trong 175 dòng CSV đều cho cùng kết quả:

- 21 cặp spatially matched.
- 135 box unmatched phía A và 306 box unmatched phía B.
- Mẫu số: `21 + 135 + 306 = 462` (tương đương 156 box A + 327 box B − 21 cặp ghép).
- Cả 21 cặp đã ghép đều có disposition được giải quyết và bằng nhau; unresolved matched pairs = 0, resolved mismatch pairs = 0.
- Toàn bộ 441 box unmatched vẫn là non-agreement. Trong đó 152 unresolved boxes (A=2, B=150); 289 box unmatched còn lại có disposition `real_scene` nhưng không có box đối ứng.

Vì vậy gate là `21/462 = 4,54545%`, làm tròn 4,55%. Mức này thấp do đa số units là box unmatched; nó không có nghĩa 21 cặp đã ghép là toàn bộ lỗi class/state. Ở 21 cặp ghép, class và `review_state` đều đồng ý.

`box_matches.csv` có 924 dòng: hai lát phân tích độc lập, mỗi lát 462 dòng. Lọc `comparison=object_source_spatial` cho 21 matched, 135 `unmatched_a`, 306 `unmatched_b` dùng bởi head-source gate. Lát `review_class` cũng có 462 dòng nhưng là phép ghép riêng theo từng class; không cộng hai lát với nhau vì sẽ đếm đôi. Tổng 175 `object_source_agreement` record trong `per_image_agreement.csv` khớp các số của lát spatial này và summary.

## Đối chiếu code và định nghĩa gate

- `docs/checklist_kiem_thu.md` ghi ba gate ≥95%, mẫu số toàn roster cho image status và metadata, còn object-level denominator là matched pairs cộng mọi box unmatched; empty/empty không tạo object units nhưng vẫn nằm trong roster denominator.
- `scripts/compare_two_reviews.py`: `source_tuple()` định nghĩa metadata tuple; `compare_image()` cộng matched và unmatched vào denominator, đồng thời cộng unmatched head boxes vào head-source denominator; vòng lặp trên roster đưa incomplete/missing status thành non-agreement; summary chia image status và metadata numerator cho `len(roster)`, còn head-source numerator chia cho denominator object-level.

Số liệu kiểm tra được tái lập bằng phép cộng trực tiếp trên các CSV và không chạy lại comparator, tests hoặc training. Đây là xác nhận số học/denominator; các metric vẫn là mô tả trước adjudication, không chứng minh annotation completeness, quyền sử dụng, provenance hoặc readiness phát hành.

## Vị trí định nghĩa trong code

- `docs/checklist_kiem_thu.md:42-44`: ba metric gate, mẫu số object-level, cách xử lý empty/empty và unresolved.
- `scripts/compare_two_reviews.py:682-696`: source metadata tuple; `:774-981`: so sánh tuple, tạo matched/unmatched units và source disposition.
- `scripts/compare_two_reviews.py:1258-1275`: status pair, incomplete, agreement và empty/empty counts; `:1617-1678`: mẫu số toàn roster cho metadata/status.
- `scripts/compare_two_reviews.py:838-968` và `:1731-1746`: công thức object/head-source denominator và summary fraction.
