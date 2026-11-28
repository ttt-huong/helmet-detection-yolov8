# Quy trình rà pilot 175 ảnh theo batch

Tài liệu này hướng dẫn thu hai bản review v7 cho cùng roster 175 ảnh. Roster đã được khóa ngày 27/11/2026 theo SHA-256 trong [`PILOT_ROSTER_LOCK.md`](../datasets/candidates/construction-ppe-pilot-draft/PILOT_ROSTER_LOCK.md); chưa có human A/B exports. Chủ dự án đã ủy quyền phương án thay thế `delegated_ai_review` cho hai agent AI riêng biệt, nhưng hai lượt mới chưa hoàn tất. ZIP ảnh gốc theo 17 browser session ở [`construction-ppe-pilot-review-package-locked.zip`](../datasets/candidates/construction-ppe-pilot-draft/construction-ppe-pilot-review-package-locked.zip). Đây là pilot rà nhãn và metadata; không phải bước gán `group_id`/project split hay đưa ảnh vào train.

## Chế độ thay thế: delegated AI review

Theo [ủy quyền rà AI ngày 28/11/2026](evidence/user-delegated-ai-review-2026-11-28.md), có thể thay hai human reviewer bằng hai lượt riêng của hai Codex agent. Mỗi lượt phải rà ảnh gốc độc lập, không xem các draft AI A/B cũ, triage của agent khác hoặc kết quả review đối phương trước khi hoàn tất. Lưu hai JSON v7 riêng với reviewer label AI rõ ràng; không điền ID reviewer người thật. Comparator giữ ba metric/ngưỡng đã chốt nhưng báo cáo phải ghi `delegated_ai_review`, tức agreement AI-AI chứ không phải human-human. Ca thiếu bằng chứng vẫn `pending`/`uncertain`; agreement cao không biến chúng thành nhãn đã xác nhận. Project approval không được dùng để suy ra provenance, rights-holder, nhóm ảnh hay split.

## 1. Khóa roster và chia batch

Trước khi giao ảnh, lập roster đúng 175 ảnh từ bản gốc bất biến. Chốt một thứ tự ổn định (ví dụ theo tên file), giữ nguyên bytes/kích thước ảnh và tính SHA-256 của từng file. Comparator cần CSV có đúng các cột `sha256,width,height,file_name_a,file_name_b`; `sha256` phải là 64 ký tự hex và duy nhất. Tên file cũng phải duy nhất riêng trong từng cột, không phân biệt hoa/thường. Nếu nguồn có tên trùng, đặt tên review duy nhất trước khi khóa roster và giữ ánh xạ; không đổi tên sau khi review. Nếu có hash trùng, giải quyết ảnh trùng trước khi khóa roster. Với cùng bộ file cho cả hai reviewer, `file_name_a` và `file_name_b` có thể giống nhau.

Chia theo thứ tự roster thành 9 batch logic:

| Batch | Vị trí roster | Số ảnh |
| --- | ---: | ---: |
| 01–08 | 001–160, mỗi batch 20 ảnh | 20 mỗi batch |
| 09 | 161–175 | 15 |

Gói đã khóa giữ 9 batch logic ở trên nhưng chia thành 17 thư mục `session-*` để đáp ứng giới hạn browser: tối đa 20 ảnh, 50 MiB và 48 megapixel mỗi phiên; mỗi ảnh tối đa 10 MiB và 24 megapixel. ZIP README cũng ghi số ảnh mỗi session. Chỉ sau khi cổng quyền ở phần dưới hoàn tất và preflight trả PASS mới nhập từng thư mục session riêng; không nhập cả batch cha. Sau mỗi lần nhập, kiểm tra browser đã nhận đúng số lượng và tên file dự kiến; app có thể bỏ qua tệp trùng hoặc một phần tệp vượt giới hạn. Cả hai reviewer phải dùng cùng các ranh giới session.

| Batch | Session 01 | Session 02 |
| --- | ---: | ---: |
| 01 | 15 | 5 |
| 02 | 17 | 3 |
| 03 | 15 | 5 |
| 04 | 16 | 4 |
| 05 | 15 | 5 |
| 06 | 17 | 3 |
| 07 | 15 | 5 |
| 08 | 17 | 3 |
| 09 | 15 | — |

### Cổng quyền trước khi giao session

Theo chỉ thị rõ ràng của chủ dự án ngày 28/11/2026, Codex `/root` được ủy quyền làm project approver và đã phê duyệt ở cấp dự án việc pilot review cùng mục đích training cho cả 175 archive member. Manifest intake ghi `pilot_review_use=approved` và `training_use=approved` trên 175/175 dòng, với approver `Codex /root (delegated by project owner in Codex conversation, 2026-11-28)` và ngày xác nhận 2026-11-28. Căn cứ là thông báo CC BY 4.0 trên [trang publisher chính thức](https://docs.ultralytics.com/datasets/detect/construction-ppe), cùng kiểm tra byte/hash: archive publisher-linked có SHA-256 khớp và bytes của 175/175 member khớp SHA-256 theo manifest; xem [bằng chứng kiểm tra archive](evidence/construction-ppe-175-source-provenance-check-2026-11-27.md). Đây là phê duyệt sử dụng ở cấp dự án, không phải xác minh độc lập provenance từng ảnh, thẩm quyền của rights holder hay quyền publicity/privacy. `rights_holder`, `group_id` và `split` vẫn để trống; human A/B chưa được gán và hai lượt AI delegated chưa hoàn tất. Có thể bắt đầu quy trình human hoặc AI đã ủy quyền sau khi preflight package đạt. Phê duyệt training ghi nhận ý định dự án; chỉ được chạy trên managed Colab GPU sau khi đạt các cổng dữ liệu, group/floor và release còn lại. Không train local. Package preflight chỉ xác minh cấu trúc/hash/ảnh, không thay thế các gate dự án hoặc release.

Sau khi cổng quyền hoàn tất và trước khi giao session, chạy preflight từ thư mục gốc repo:

```sh
python scripts/validate_pilot_review_package.py
```

Script đối chiếu hash ZIP/roster với lock record, tên file/hash/kích thước với roster, giải mã JPEG trong bộ nhớ và in bảng 17 session cùng các giới hạn browser. Script không giải nén hoặc ghi ảnh; cần Pillow sẵn trong môi trường Python và không tự cài dependency. Preflight chỉ xác minh package kỹ thuật, không phê duyệt quyền hoặc training; mọi lỗi trả mã thoát khác 0 và phải được xử lý trước khi giao session.

## 2. Hai lượt review tách biệt

Mỗi reviewer rà đủ 17 session theo cùng roster, nhưng làm độc lập và không trao đổi nhãn trước khi xuất. Dùng browser profile riêng cho reviewer A và B; có thể kết hợp origin riêng (scheme + host + port). `localStorage` của ứng dụng dùng khóa `helmet-vision.review-draft.v1` và được cô lập theo browser profile/origin. Hai tab cùng profile và cùng origin dùng chung bản nháp.

Ảnh gốc không nằm trong localStorage hoặc JSON v7; bản nháp giữ metadata/nhãn và cần chọn lại đúng file gốc để khôi phục. Sau khi hoàn tất từng session, xuất JSON v7, xác nhận số ảnh trong mảng `images` bằng số JPEG của session trong README gói, rồi đổi tên/move file download mặc định `helmet-vision-review-v7.json` thành tên riêng, ví dụ `reviews/reviewer-a/batch-01-session-01-v7.json`. Chỉ đổi tên file export, không sửa nội dung JSON hay đổi tên ảnh nguồn sau khi review. Trước session kế tiếp, dùng **Xóa phiên** rồi **Xóa bản nháp đã lưu**; JSON đã xuất là bản lưu của session. Dùng bản sao của [tracker 34 lượt review](../datasets/candidates/construction-ppe-pilot-draft/pilot-175-review-session-tracker-template.csv) để ghi số lượng/tên file đã nhập, trạng thái hoàn tất và đường dẫn/hash/count từng export; reviewer IDs để trống đến khi được gán. Các ô `pending` là trạng thái chưa thực hiện, không phải bằng chứng hay phê duyệt quyền; template không thay đổi quyền dùng review/train, roster, group hoặc split.

Chỉ xuất khi từng ảnh đã được đánh dấu rà xong và đạt các kiểm tra scene/surface/region của exporter. Nếu đã rà toàn cảnh và nguồn `clear` nhưng không thể chốt một annotation đầu/mũ, có thể xác nhận hoàn tất lượt rà và giữ annotation đó với `review_state=uncertain`; JSON lưu `reviewed_with_labels` để đối chiếu, còn comparator tính ca unresolved là không đồng thuận. Converter từ chối mọi annotation uncertain nên chúng không vào dữ liệu huấn luyện. Nếu chính nguồn ảnh/bề mặt chưa rõ, giữ `frame_source_status=review_required` và không đánh dấu hoàn tất. Trong pilot, để trống `group_id` và `split`: đây chưa phải giai đoạn phân nhóm cảnh hay gán project split. Không điền giá trị phỏng đoán để làm mất cảnh báo metadata; các trường này được hoàn tất sau adjudication khi xây dataset. Bộ so sánh pilot chấp nhận `split` trống; bước chuyển đổi sang YOLO vẫn yêu cầu gán group và split hợp lệ.

Đặt mọi export của mỗi reviewer dưới một thư mục riêng. Merger chỉ nhận export `helmet-vision-review-v7`, yêu cầu metadata cấp cao nhất giống nhau và từ chối `image_id` hoặc `file_name` trùng; dùng cùng phiên bản browser/rule cho mọi batch.

## 3. Gộp riêng từng reviewer

Từ thư mục gốc repo, merge đủ 17 session export của A theo thứ tự batch/session cố định trong ZIP thành một file mới; lặp lại cho B, không trộn export giữa hai reviewer. Comparator ghép ảnh theo SHA-256 nên việc merge giữ thứ tự package giúp tái lập đầu ra:

```powershell
python scripts/merge_review_json.py --inputs `
  reviews/reviewer-a/batch-01-session-01-v7.json reviews/reviewer-a/batch-01-session-02-v7.json `
  reviews/reviewer-a/batch-02-session-01-v7.json reviews/reviewer-a/batch-02-session-02-v7.json `
  reviews/reviewer-a/batch-03-session-01-v7.json reviews/reviewer-a/batch-03-session-02-v7.json `
  reviews/reviewer-a/batch-04-session-01-v7.json reviews/reviewer-a/batch-04-session-02-v7.json `
  reviews/reviewer-a/batch-05-session-01-v7.json reviews/reviewer-a/batch-05-session-02-v7.json `
  reviews/reviewer-a/batch-06-session-01-v7.json reviews/reviewer-a/batch-06-session-02-v7.json `
  reviews/reviewer-a/batch-07-session-01-v7.json reviews/reviewer-a/batch-07-session-02-v7.json `
  reviews/reviewer-a/batch-08-session-01-v7.json reviews/reviewer-a/batch-08-session-02-v7.json `
  reviews/reviewer-a/batch-09-session-01-v7.json `
  --output reviews/reviewer-a/merged-v7.json
```

Chạy lại lệnh với `reviewer-a` đổi thành `reviewer-b`. Chọn `--output` chưa tồn tại vì script không ghi đè. Merger kiểm tra duplicate ID/tên và cấu trúc chung, nhưng không chứng minh đủ roster 175 ảnh; bước comparator bên dưới mới đối chiếu đủ hash.

## 4. Đối chiếu bằng roster/hash

Comparator cần thư mục ảnh phẳng (không thư mục con, không symlink), còn ZIP giữ cấu trúc batch/session lồng nhau. Sau khi review, tạo một bản ảnh phẳng riêng cho mỗi reviewer bằng cách copy đúng 175 JPEG gốc từ các session; giữ nguyên tên và bytes, không dùng ảnh overlay hoặc tên đã đổi. Tên cần khớp `file_name_a`/`file_name_b` trong roster. Comparator đọc lại ảnh, xác minh SHA-256 và kích thước với roster rồi ghép review bằng hash. Export v7 không chứa pixel ảnh; comparator tự tính SHA-256 từ file nguồn, nên giữ nguyên bytes gốc và roster đã khóa.

```powershell
python scripts/compare_two_reviews.py `
  --roster datasets/candidates/construction-ppe-pilot-draft/pilot-roster.csv `
  --review-a reviews/reviewer-a/merged-v7.json --images-a images/reviewer-a --reviewer-a reviewer-a `
  --review-b reviews/reviewer-b/merged-v7.json --images-b images/reviewer-b --reviewer-b reviewer-b `
  --output-dir reports/pilot-175 --iou-threshold 0.5
```

`pilot-roster.csv` cần đúng `sha256,width,height,file_name_a,file_name_b`; output directory phải mới. Trước khi đọc tỷ lệ, xác nhận `summary.json` ghi đúng roster 175 ảnh, cả `reviewer_a_roster_hash_set_equal` và `reviewer_b_roster_hash_set_equal` đều `true`, không có roster issue/thiếu hash. Xem thêm `per_image_agreement.csv`, `disagreements.csv`, `box_matches.csv` và `roster_issues.csv`. Comparator báo tỷ lệ mô tả trên hai bản review độc lập ban đầu; nó không adjudicate hoặc tự tuyên bố đạt ngưỡng. Ba metric đã chốt phải được tính riêng trước adjudication, mỗi metric đạt ít nhất 95%, không lấy trung bình:

- Trạng thái rà ảnh: `summary.json.image_review_status.agreement_fraction_over_full_roster`; mẫu số là toàn bộ roster 175 ảnh. Thiếu/không hợp lệ/chưa có trạng thái cuối là không đồng thuận.
- Metadata nguồn: `summary.json.source_metadata_exact_agreement.fraction_over_roster`; mẫu số là toàn bộ roster. Bao gồm khớp chính xác `scene_type`, `frame_source_status`, inventory/số vùng theo loại surface và cờ rà cảnh `other` khi áp dụng.
- Nhãn/source disposition của box đầu-mũ: `summary.json.head_source_disposition.agreement_fraction`; IoU ghép mặc định 0.5. Mẫu số gồm các cặp box không gian có ít nhất một bên thuộc review class 0–4, cộng từng box đầu-mũ unmatched; unresolved, mismatch và unmatched là không đồng thuận. Nếu mẫu số bằng 0 thì metric là N/A, không được tính là đạt.

`clear_status_metadata_agreement` là số liệu chẩn đoán bổ sung, không thay thế metric trạng thái ảnh đã chốt và không phải cổng 95%. Sau khi lưu các tỷ lệ ban đầu, adjudicate mọi bất đồng, ảnh thiếu/không hợp lệ và box unmatched/unresolved; không xóa chúng khỏi roster hay mẫu số ban đầu. Xem thêm [checklist pilot](checklist_kiem_thu.md).

Tách profile/origin chỉ cô lập bản nháp browser, không chứng minh tính độc lập của phán đoán. Nếu có lượt do LLM tạo, ghi đúng nguồn; **hai lượt LLM không phải hai reviewer con người độc lập**.
