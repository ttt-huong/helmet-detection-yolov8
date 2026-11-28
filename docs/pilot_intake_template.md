# Mẫu intake quyền dữ liệu và pilot

> **Bản nháp để chủ dự án điền.** Mẫu này không tự xác minh hoặc phê duyệt quyền dùng ảnh. `pilot_review_use` và `training_use` đều mặc định `unknown` và được xét riêng theo từng ảnh. Chỉ người được ủy quyền mới được đặt trạng thái `approved`, sau khi kiểm tra chứng cứ cho đúng hoạt động. Không dùng `source_index.csv`, nhãn nguồn hoặc manifest quyền legacy làm bằng chứng thay thế. Huấn luyện chỉ chạy trên managed Google Colab GPU, không train local.

Hướng dẫn hiện hành: [Checklist kiểm thử](checklist_kiem_thu.md) · [Đánh giá nguồn dữ liệu](dataset_source_assessment.md).

## 1. Tiêu chí pilot đã được duyệt

Đo agreement trên hai bản export độc lập ban đầu, **trước adjudication**. Cả ba metric dưới đây phải đạt riêng lẻ `≥95%`; không lấy trung bình gộp. Comparator chỉ báo số liệu mô tả, không tự cấp pass. Sau khi ghi nhận điểm pre-adjudication, adjudicate mọi bất đồng, box unmatched/unresolved và bản rà thiếu/không hợp lệ; các trường hợp đó vẫn là non-agreement trong điểm pre-adjudication.

| Metric đã duyệt | Numerator / denominator |
|---|---|
| `image_review_status.agreement_fraction_over_full_roster` | Số ảnh có terminal `image_review_status` hợp lệ và giống nhau giữa hai reviewer / `N` ảnh trong roster. Ảnh thiếu, invalid hoặc thiếu status là non-agreement. |
| `source_metadata_exact_agreement.fraction_over_roster` | Số ảnh có toàn bộ metadata nguồn khớp chính xác / `N` ảnh trong roster. Bao gồm `scene_type`, `frame_source_status`, cờ rà cảnh `other` khi áp dụng, danh sách loại surface, số instance vật lý và số vùng `depiction_region` theo surface type. Ảnh thiếu, pending, invalid hoặc không so sánh được là non-agreement. |
| `head_source_disposition.agreement_fraction` tại IoU `0.5` | Numerator là cặp box ghép mà **cả hai box đều thuộc** review class 0–4, cả hai disposition được xác định và giống nhau. Denominator là mọi cặp box ghép không phân biệt lớp nếu ít nhất một phía thuộc class 0–4, cộng mọi box class 0–4 không ghép ở cả hai phía. Cặp unresolved, mismatch/class-boundary và box head unmatched là non-agreement; box không ghép không thuộc class 0–4 ở phía còn lại không được tính. Nếu denominator bằng 0, metric là N/A và không đạt ngưỡng. |

`clear_status_metadata_agreement` là diagnostic riêng về metadata khớp và frame-source status `clear`; metric này **không nằm trong ba cổng ≥95% đã duyệt** và không thay thế `image_review_status` agreement. Ảnh empty/empty không tạo đơn vị box cho `head_source_disposition`, nhưng vẫn nằm trong denominator toàn roster của hai metric image-level.

| Thông tin triển khai pilot | Giá trị cần ghi |
|---|---|
| Kích thước và khóa roster | `150–250` ảnh; khóa SHA-256 roster trước khi reviewer bắt đầu. |
| Reviewer A / Reviewer B | Reviewer độc lập; ID phải khác nhau và được truyền cho comparator. |
| Adjudication | Ghi người adjudicate và cách xử lý mọi bất đồng, unmatched/unresolved, thiếu hoặc invalid sau khi lưu điểm agreement ban đầu. |
| Roster CSV và thư mục ảnh A/B | Schema comparator chính xác: `sha256,width,height,file_name_a,file_name_b`. |
| Đường dẫn roster, SHA-256 roster, thời điểm khóa | Ghi timestamp và timezone. |

Không xem comparator là bộ tự động cấp pass: nó chỉ tính agreement mô tả trên hai export độc lập và không adjudicate, gộp nhãn hay đổi điểm sau adjudication. Chủ dự án quyết định kết quả theo ba tiêu chí đã duyệt và lưu kết quả adjudication riêng.

Roster comparator là CSV riêng, chỉ gồm đúng năm cột trên. Không thêm cột rights, provenance, split, group hoặc reviewer vào roster này; lưu các trường đó trong manifest intake theo SHA-256 bên dưới. Khóa file và hash roster trước khi reviewer bắt đầu.

## 2. Sàn nhóm cho các mũ ngoài mục tiêu

Áp dụng sàn **300 nhóm train, 30 nhóm validation và 100 nhóm locked test** cho từng loại: mũ bảo hiểm giao thông, mũ lưỡi trai/kê-pi và mũ len. Dùng định nghĩa [nhóm độc lập và điều kiện tính nhóm](../configs/helmet_types_labeling.md#sàn-dữ-liệu-cho-mũ-dễ-nhầm) khi lập dataset sau pilot. Đợt pilot 175 ảnh dùng để đo đồng thuận rà nhãn. Sàn trên áp dụng cho các tập của dataset chính.

## 3. Manifest intake theo từng ảnh

Tạo một manifest riêng, một dòng cho mỗi ảnh, khóa bằng SHA-256. `file_name` và SHA-256 phải trỏ đúng bytes ảnh sẽ được rà. Quyền cho rà pilot và quyền dùng để train là hai quyết định riêng: `pilot_review_use` (hoạt động rà/gán nhãn) và `training_use` đều dùng enum `unknown` / `approved` / `not_allowed`. Chỉ đặt `pilot_review_use=approved` khi chứng cứ bao phủ rõ việc rà/gán nhãn; chỉ đặt `training_use=approved` khi chứng cứ bao phủ việc dùng ảnh để huấn luyện. Không suy quyền cho hoạt động này từ quyền của hoạt động kia. Tách nguồn ảnh khỏi chứng cứ: `image_source_reference` mô tả xuất xứ ảnh; `pilot_review_evidence_reference` trỏ tới căn cứ cho phép review; `training_rights_evidence_reference` trỏ tới căn cứ dùng ảnh huấn luyện. Giá trị `basis` theo UI là `owned`, `permission`, `license` hoặc `public_domain`; để trống khi chưa xác định, và không suy quyền từ `basis` hay `license_id`.

Header CSV đề xuất cho manifest riêng:

```csv
sha256,file_name,image_source_reference,group_id,split,scene_type,reviewer_a_id,reviewer_b_id,pilot_review_use,pilot_review_evidence_reference,pilot_review_approved_by,pilot_review_confirmed_date,training_use,basis,training_rights_evidence_reference,training_approved_by,training_confirmed_date,license_id,attribution,rights_holder
```

Candidate batch hiện có manifest 19 dòng tại [`datasets/candidates/construction-ppe-review-batch/rights-intake-draft.csv`](../datasets/candidates/construction-ppe-review-batch/rights-intake-draft.csv). File nối SHA-256 và tên file với image ID của review v7, tên/hash archive và archive member. `pilot_review_use` và `training_use` được ghi `approved` theo khai báo của chủ dự án ngày 27/11/2026, gắn với từng SHA trong [hồ sơ khai báo](evidence/user-rights-declaration-19-images-2026-11-27.md). Đây là quyền do người dùng tự khai báo cho dự án, chưa phải xác minh độc lập về quyền của người khai báo, provenance, rights holder, license hay attribution; các trường nguồn ảnh/chủ quyền/license còn trống. `scene_type=other` khớp review v7; group, project split và reviewer chưa hoàn thiện. Các trường archive chỉ truy vết bytes/vị trí trong gói. Manifest intake không được browser, converter hoặc notebook tự ingest.

Để trống `group_id`, `split`, reviewer, approver hoặc ngày xác nhận khi chưa quyết định; không tự gán split trước khi các ảnh cùng nguồn/ngữ cảnh được gom group. Split của dataset dùng `train`, `val` hoặc `test` (`test` là locked test). Định danh hai reviewer trong manifest phải khớp quyết định pilot và lệnh comparator. `rights_holder` là chủ thể/nguồn nắm quyền; các trường `*_approved_by` ghi người được ủy quyền trong dự án đã đối chiếu chứng cứ cho hoạt động tương ứng.

License cấp ở mức dataset chỉ là căn cứ để đối chiếu phạm vi áp dụng cho từng file; nó không tự chứng minh quyền hoặc provenance của mọi ảnh trong dataset. Không đưa ảnh vào pilot roster nếu `pilot_review_use` chưa là `approved` hoặc thiếu chứng cứ cho hoạt động review. Không chuyển đổi/huấn luyện ảnh nếu `training_use` chưa là `approved` hoặc thiếu chứng cứ per-file bao phủ training. Với `basis=license`, ghi rõ `license_id` và `attribution`, nhưng các trường này không tự chứng minh quyền. Khai báo của người dùng được lưu riêng làm căn cứ cho 19 ảnh; không được hiểu là đã xác minh nguồn, người nắm quyền hoặc điều khoản của bên thứ ba. Manifest intake này là tài liệu thu thập đầu vào, browser và converter không tự ingest nó. Review v7 không có trường riêng cho `image_source_reference` hoặc `pilot_review_evidence_reference`; giữ hai trường đó trong manifest intake, không chuyển chúng vào `rights.source_reference`. Giữ người duyệt và ngày xác nhận riêng cho từng hoạt động trong manifest làm audit trail. Không dùng `source_index.csv`, nhãn nguồn hay manifest quyền legacy để tự điền quyền, group, split hoặc scene.

## 4. Cổng trước khi chuyển dữ liệu

- [ ] Quyết định pilot và metric ≥95% đã được điền trước khi rà.
- [ ] Roster comparator CSV có đúng năm cột và 150–250 ảnh đã khóa bằng SHA-256, có hai tên file tương ứng cho reviewer A/B.
- [ ] Manifest intake riêng được khóa theo SHA-256; reviewer/group/split khớp quyết định và các trạng thái chưa biết vẫn để trống hoặc `unknown`.
- [ ] Mọi ảnh trong pilot roster có `pilot_review_use=approved` cùng evidence bao phủ hoạt động rà; điều này không tự duyệt `training_use`.
- [ ] Quyền cho hoạt động review và provenance của từng ảnh trong pilot đã được người có trách nhiệm xác minh; `training_use` có thể còn `unknown`, nhưng ảnh đó không được chuyển đổi/huấn luyện.
- [x] Floor traffic/cap/beanie và định nghĩa group đã được quyết định (chủ dự án, 28/11/2026).
- [ ] Candidate archive/index và manifest legacy không được coi là chứng cứ quyền hoặc nhãn review.

Hoàn tất mẫu này không tự tạo quyền dùng ảnh, không duyệt annotation, không chạy converter và không cho phép train local. Huấn luyện chỉ chạy trên managed Google Colab GPU.

Khi dữ liệu và mọi cổng đủ điều kiện, huấn luyện/release gate chỉ chạy trên [managed Google Colab GPU — Notebook 03](../notebooks/03_train_hat_types_colab.ipynb); không chạy train hoặc resume local.
