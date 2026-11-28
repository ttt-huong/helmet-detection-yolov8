# Kế hoạch chuẩn bị chụp và intake có kiểm soát — 2026-11-28

## Trạng thái và phạm vi

Đây là kế hoạch chuẩn bị cho người tại hiện trường, **không phải bằng chứng dữ liệu đã được thu**. Chưa chụp ảnh, chưa xin hay duyệt quyền, chưa tạo `group_id`/split và chưa có mẫu nào được tính vào quota. Chỉ tính sau khi ảnh thật đã được thu hợp lệ, metadata/provenance theo ảnh được ghi, quyền cho hoạt động tương ứng được người có trách nhiệm xác nhận, ảnh được rà hoàn chỉnh và nhóm độc lập được kiểm tra.

Các cổng bên dưới bám theo [ontology](../../configs/helmet_types_labeling.md), [mẫu pilot intake](../pilot_intake_template.md), [capture-session intake template](../../configs/capture_session_intake_template.csv), [split manifest template](../../configs/hat_types_split_manifest_template.csv) và [rights manifest template](../../configs/hat_types_rights_manifest_template.csv). Capture-session CSV là sổ hỗ trợ; không thay thế hay tự ingest vào hai manifest split/rights hiện có.

## Những điều kiện đã được quyết định

- Nhãn cần bù là `traffic_helmet_worn` (người thật trong cảnh đội mũ xe máy nửa đầu, 3/4 hoặc full-face), `cap_worn` (mũ lưỡi trai/kê-pi), và `beanie_worn` (mũ len). Chỉ người thật đang đội mới đủ điều kiện; mũ cầm/đặt, mũ trong hình hiển thị và trường hợp chưa rõ không được tính.
- Mỗi subtype cần ít nhất **300 nhóm train, 30 validation, 100 locked-test**. Đơn vị là `(split, group_id)` có ít nhất một box đã rà xác nhận loại đó, không phải số ảnh/box/khung/người ghi danh.
- Với nguồn depiction `poster`, `printed_photo`, `screen`, ontology yêu cầu tối thiểu **300 nhóm train và 100 locked-test mỗi nguồn**. Tập locked test phải có cả `depiction_only` và `mixed_scene` cho từng loại bề mặt; đây là sáu ô cần có. Không tự đặt mức sàn mỗi ô cao hơn quy định; ghi số nhóm/ảnh riêng để chủ dự án quyết định nếu muốn tăng coverage.
- Một người được nhận diện trong hồ sơ, cùng video/phiên/cảnh, cùng poster/nội dung màn hình, cùng ảnh gốc, crop hoặc biến thể phải ở chung một nhóm. Khi thiếu bằng chứng để tách nhóm, giữ chờ và chưa tính. SHA khác nhau, tên file hoặc ngày chụp khác nhau không tự chứng minh độc lập.

**Quy mô thực tế:** mỗi subtype cần tối thiểu 430 group units độc lập (300/30/100), còn mỗi nguồn depiction cần 400 group units (300 train + 100 locked test). Đây không phải số ảnh. Nếu cùng người tình nguyện được chụp đội cả ba loại mũ trong cùng group, group đó có thể đóng góp một lần cho từng subtype khi mỗi loại có bằng chứng riêng; không được tạo ba group IDs từ cùng người/cảnh. Mỗi nguồn depiction cũng có thể được ghi cho cùng group khi các medium cùng hiện diện, nhưng group/nội dung liên quan không được nằm ở nhiều split. Nên lập trước bảng tiến độ theo subtype × split và depiction-source × split, rồi bổ sung nhiều buổi/địa điểm/thành phần cảnh cho đủ variation.

## Protocol đề xuất

### 1. Phê duyệt trước khi cầm máy

1. Chọn buổi chụp có kiểm soát với người tình nguyện trưởng thành, địa điểm được chủ sở hữu cho phép và người vận hành được chỉ định. Với cảnh xe máy, dùng xe đứng yên hoặc khu vực riêng an toàn; không yêu cầu người lái thao tác, tạo tình huống nguy hiểm hay chụp khi đang điều khiển xe.
2. Trước buổi chụp, ghi mục đích và phạm vi cho từng hoạt động: chụp/lưu trữ, rà/gán nhãn, huấn luyện, đánh giá, tạo crop/biến thể, chia sẻ hoặc công bố. Lấy xác nhận có thể truy lại của người chụp/đơn vị giữ quyền và người được nhận diện; với poster, ảnh in hoặc nội dung màn hình, kiểm tra riêng quyền của nội dung đó. Xác nhận không được suy từ việc người đó đồng ý chụp hay từ quyền của photographer.
3. Dùng ID giả danh cho người tham gia; giữ danh sách nối ID với danh tính tách biệt, hạn chế quyền truy cập và không đưa tên liên hệ, giấy tờ, biển số hoặc PII không cần thiết vào ảnh/manifest. Nếu bắt buộc chụp người qua đường hoặc nội dung có quyền chưa rõ, loại ảnh đó khỏi intake sử dụng cho đến khi có xác nhận đủ phạm vi.

### 2. Thu ảnh thật theo nhóm độc lập

1. Mỗi buổi chụp nhận `session_id` duy nhất; ghi `operator_id`, `camera_id`, ngày giờ kèm timezone, địa điểm ở mức đủ truy vết nhưng không phơi bày vị trí riêng tư, thiết lập chụp và `person_id` giả danh cho người xuất hiện. Ghi người chụp/đơn vị là nguồn ảnh; không tự gọi đây là nguồn mở.
2. Với mỗi loại mũ, chụp toàn khung có đầu, thân thể/ngữ cảnh và các dấu hiệu không gian đủ để người rà phân biệt `real_scene` với bề mặt hiển thị. Giữ ảnh gốc nguyên bytes. Nếu chụp chuỗi ảnh hoặc video, mọi khung liên quan cùng người, session và cảnh dùng chung nhóm; crop/resize/ảnh tăng cường luôn tham chiếu ảnh cha và ở cùng nhóm.
3. Thu riêng nhiều người và nhiều cảnh độc lập; không lặp cùng người đã nhận diện ở nhóm khác nhằm tăng số nhóm. Có thể một nhóm đóng góp cho nhiều loại mũ nếu trong nhóm có bằng chứng box riêng cho từng loại, nhưng chỉ được đếm một lần cho mỗi subtype. Ghi rõ kiểu mũ nhìn thấy để cân bằng mũ xe máy nửa đầu/3⁄4/full-face và baseball cap/kê-pi; kiểu ghi chú không mở rộng ontology.
4. Với các bề mặt, tạo sáu strata: `poster × depiction_only`, `poster × mixed_scene`, `printed_photo × depiction_only`, `printed_photo × mixed_scene`, `screen × depiction_only`, `screen × mixed_scene`. Ghi `surface_id` riêng cho từng vật thể vật lý và `poster_id`/`screen_content_id` cho nội dung nguồn; cùng một poster, ảnh nguồn hoặc nội dung video/màn hình được gom chung dù chụp ở góc, thời điểm hay thiết bị khác. Cảnh hỗn hợp cần có người thật trong cảnh và người trong bề mặt; ảnh depiction-only chỉ có người trong bề mặt. Giữ toàn bộ viền nhìn thấy để người rà có thể vẽ `depiction_region`; chụp cả ca khó như poster cầm tay, màn hình phát video, lóa, mất viền và người đứng sát bề mặt.

### 3. Sổ intake nối từng ảnh với chứng cứ

Giữ một sổ thu nhận bổ sung keyed bằng `image_id` và SHA-256; sổ này phục vụ provenance, không được browser/converter tự ingest. Mỗi ảnh gốc có tối thiểu:

`image_id`, tên file gốc, SHA-256, `image_width`, `image_height`, `capture_id`, `session_id`, `person_id` pseudonymous, `camera_id`, thời điểm + timezone, địa điểm/scene ID, `surface_id`, `poster_id`/`screen_content_id` nếu có, ảnh cha nếu derivative, người chụp, nguồn/nội dung gốc, ghi chú lớp/biến thể mũ quan sát được, và đường dẫn đến chứng cứ quyền.

Trong capture-session CSV, `person_permissions_json` là danh sách object keyed theo `person_id`, mỗi object ghi trạng thái, scope, evidence reference và ngày xác nhận consent của đúng người đó. `depiction_surfaces_json` ghi từng bề mặt vật lý, còn `depiction_surface_rights_json` ghi source URL, rights status/evidence, rights holder, license và attribution keyed theo `surface_id`/`content_id`; không gộp nhiều nội dung khác quyền thành một quyết định ảnh. `observed_hat_variants_json` nối ghi chú kiểu mũ quan sát được tới người/nguồn tương ứng để đo độ phủ; các giá trị này là mô tả phụ, không phải lớp review mới. Kích thước được lấy từ ảnh gốc sau ingest. Các ví dụ trong CSV không phải quyền hay dữ liệu thật.

Với quyền, ghi riêng cho từng SHA hoặc danh sách SHA được chứng cứ bao phủ: ai là rights holder, ai cấp phép, ngày/phiên bản chứng cứ, hoạt động được phép (ít nhất tách `pilot_review_use` khỏi `training_use`; nếu cần, ghi thêm đánh giá, derivative, chia sẻ/công bố), giới hạn mục đích, license/attribution yêu cầu và người được ủy quyền đã kiểm tra/ngày kiểm tra. Gắn xác nhận của người tham gia với đúng `person_id` và phạm vi buổi/ảnh; gắn quyền poster/screen content riêng với `surface_id`/content ID. Khi thiếu hoặc còn mơ hồ, giữ `unknown`, không đưa vào pilot/training tương ứng.

Ánh xạ vào template có sẵn, không đổi header:

| Template | Ghi sau khi chứng cứ được kiểm tra |
|---|---|
| [Capture-session intake](../../configs/capture_session_intake_template.csv) | Sổ mỗi ảnh gốc: capture/session/person/source, kích thước, observed variants, consent theo person, rights theo surface/content, candidate group và link audit; giá trị quyền `unknown` đến khi chứng cứ được xác nhận. |
| [Pilot intake](../pilot_intake_template.md) | Một dòng mỗi ảnh theo SHA-256; `image_source_reference` trỏ đến capture/session và nguồn nội dung; `group_id`, `split`, `scene_type` khớp quyết định đã rà; giữ `pilot_review_use` và `training_use` tách biệt cùng evidence/approver/date riêng. |
| [Split manifest](../../configs/hat_types_split_manifest_template.csv) | Chỉ map đúng `image_id`, split (`train`, `val`, `test`), `group_id`, `scene_type` (`depiction_only`, `mixed_scene`, `other`). Ghi sau khi nhóm đã được rà; test là locked. |
| [Rights manifest](../../configs/hat_types_rights_manifest_template.csv) | Một dòng mỗi ảnh: `image_id`, `training_use`, `basis`, `source_reference`, `license_id`, `attribution`. Không đặt `training_use=approved` khi permission/license không bao phủ training cho ảnh và nội dung liên quan. |

Với quyền sở hữu, ghi chứng cứ cụ thể cho ai tạo ảnh và ai giữ quyền; `basis=owned` không tự duyệt. Với `basis=permission`, lưu giấy phép/consent có scope và mapping SHA/session. Với `basis=license`, lưu ID điều khoản, attribution chính xác và URL/bản lưu điều khoản. `source_reference`, `license_id` hay attribution tự thân không phải chứng cứ được cho phép. Không thay thế bằng archive/source index hoặc lời khai không gắn từng file.

### 4. Khóa nhóm, gán split và rà

1. Sau ingest, tính SHA-256 cho bytes gốc, giữ bản gốc bất biến và lập dẫn xuất riêng. Dò exact/near duplicates và nối qua person/session/video/location/source content; người kiểm tra provenance phân xử liên kết trước khi chia tập. Mọi quan hệ chưa rõ được giữ `pending`/ngoài quota.
2. Lập `group_id` cho mỗi đơn vị nguồn/cảnh đã có bằng chứng độc lập; sau đó gán toàn bộ nhóm vào đúng một split. Bảo đảm không có person, session/video, scene hoặc poster/screen content liên quan bắc qua split. Khóa test trước khi dùng để chọn mô hình/threshold; thay đổi split cần phiên bản manifest mới và nhật ký lý do.
3. Hai reviewer rà độc lập toàn ảnh, không chỉ crop. Xác nhận `image_review_status` terminal, source của từng head/hat, lớp và box, toàn bộ `depiction_surface_types`, từng `surface_id`/`depiction_region`, scene type và trạng thái `frame_source_status=clear` chỉ khi đã rà hết nguồn hiển thị. Chỗ không đủ bằng chứng là `unresolved`/`uncertain` và không đếm. Lưu kết quả agreement trước adjudication theo cổng trong intake template; adjudicate mọi bất đồng sau đó.
4. Trước khi mở rộng collection/review, chạy pilot 150–250 ảnh với hai reviewer độc lập và yêu cầu cả ba agreement gates trong intake template đạt riêng lẻ `≥95%`. Nếu bất kỳ cổng nào thấp hơn, sửa hướng dẫn, hiệu chuẩn lại và review lại pilot trước khi tăng quy mô.

## Cổng để bắt đầu đếm

- [ ] Ảnh gốc thật đã được chụp, SHA-256 và provenance theo ảnh được lưu; derivatives nối về ảnh cha.
- [ ] `pilot_review_use` được phê duyệt riêng trước khi đưa ảnh vào roster; `training_use` chỉ approved khi chứng cứ per-image và nội dung phụ bao phủ rõ hoạt động training.
- [ ] `group_id` được kiểm tra theo người/phiên/cảnh/nội dung/ảnh gốc; mọi group chỉ thuộc một split, còn trường hợp không đủ provenance chưa được tính.
- [ ] Hai lượt rà độc lập và adjudication xác nhận người thật đang đội đúng subtype; hình người trong poster/ảnh/screen chỉ được ghi là depiction, không cộng vào worn count.
- [ ] Đạt đủ group floors theo từng subtype và đúng split (300/30/100); các nguồn depiction đạt source floors và có cả hai scene type cho từng medium trong locked test.

Cho đến khi các cổng này hoàn tất, mọi con số trong kế hoạch chỉ là **mục tiêu thu thập**, không phải ảnh, nhóm hay quota đã đạt. Người tại hiện trường cần thực hiện chụp và lưu chứng cứ; kế hoạch này không thay cho việc cấp quyền hoặc rà dữ liệu.
