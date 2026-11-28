# Quy chuẩn gán nhãn bộ phân biệt loại mũ

## Mục tiêu và nguyên tắc bắt buộc

Ontology tám lớp dưới đây chỉ là schema review trong browser. Model YOLO hardhat-only có đúng hai lớp: ID 0 `hard_hat_worn` và lớp phụ ID 1 `depiction_region`; sáu review class ID 1–6 còn lại không phải đầu ra model. Mô hình chỉ nhận diện mũ bảo hộ lao động; mũ giao thông, mũ lưỡi trai, mũ len và các mũ ngoài mục tiêu không được xuất thành lớp YOLO hoặc tính vào số mũ bảo hộ. Ảnh đã rà chỉ có mũ ngoài mục tiêu có thể được giữ với nhãn YOLO rỗng để làm ví dụ nền âm. **Một người đội mũ xuất hiện trong poster, ảnh in, ảnh chụp, TV, màn hình hoặc thiết bị hiển thị không phải là người thật đang đội mũ trong cảnh và tuyệt đối không được tính vào số mũ bảo hộ.** Quy tắc này áp dụng dù hình hiển thị có giống ảnh chụp thật hay xuất hiện liên tục trong video.

Nhãn chỉ mô tả những gì quan sát được trong cả khung hình và ngữ cảnh xung quanh. Một crop nhỏ quanh đầu hoặc chiếc mũ không chứng minh nguồn là người thật. Nếu không đủ bằng chứng, đánh dấu `uncertain`, chuyển cho người rà soát và loại khỏi nhãn huấn luyện xác định cho đến khi được phân xử.

## Danh mục lớp

| ID review | Tên lớp review | Dùng khi | Được xuất thành hardhat target hoặc tính vào số mũ bảo hộ? |
| ---: | --- | --- | --- |
| 0 | `hard_hat_worn` | Người hiện diện thật trong cảnh đang đội mũ bảo hộ công trường | Có; model ID 0 |
| 1 | `traffic_helmet_worn` | Người hiện diện thật trong cảnh đang đội mũ bảo hiểm giao thông. Phạm vi bản đầu gồm mũ xe máy nửa đầu, 3/4 và full-face | Không; ví dụ nền âm |
| 2 | `cap_worn` | Người hiện diện thật trong cảnh đang đội mũ lưỡi trai hoặc kê-pi | Không; ví dụ nền âm |
| 3 | `beanie_worn` | Người hiện diện thật trong cảnh đang đội mũ len | Không; ví dụ nền âm |
| 4 | `bare_head` | Đầu người hiện diện thật trong cảnh nhìn đủ rõ và không đội bất kỳ loại mũ nào thuộc phạm vi dự án | Không |
| 5 | `depicted_hat` | Mũ hoặc người đội mũ xuất hiện trong poster, ảnh in, ảnh chụp, tranh, TV, màn hình hay nội dung hiển thị khác | Không |
| 6 | `loose_hat` | Mũ thật không được đội, ví dụ đang cầm, treo, đặt trên bàn hoặc để dưới đất | Không |
| 7 | `depiction_region` | Hộp quanh toàn bộ ranh giới nhìn thấy của poster, ảnh, ảnh in hoặc màn hình có hình người | Không, đây là vùng nguồn; model ID 1 |

## Nhãn đưa vào mô hình

Converter tạo YOLO với đúng hai lớp: model ID 0 `hard_hat_worn` (review ID 0) và model ID 1 `depiction_region` (review ID 7, lớp phụ để lọc poster). Review ID 1–6 không được ghi vào YOLO labels. Ảnh chứa mũ giao thông, mũ lưỡi trai, mũ len hoặc mũ rời vẫn được giữ nếu đã rà hết mũ bảo hộ mục tiêu; các hộp ngoài mục tiêu bị bỏ khỏi `.txt`. Nếu ảnh không có hardhat target hoặc `depiction_region`, `.txt` sẽ rỗng và ảnh trở thành ví dụ nền âm cho detector hardhat.

## Metadata loại bề mặt hiển thị

Mỗi ảnh khai báo `depiction_surface_types` là danh sách duy nhất gồm các loại bề mặt có người trong nội dung được hiển thị: `poster`, `printed_photo`, `screen` hoặc `other_depiction`. Một ảnh có thể có nhiều loại. Inventory `depiction_surfaces` lưu từng bề mặt vật lý dưới dạng `{surface_id, surface_type}`; `surface_id` duy nhất trong ảnh, kể cả khi nhiều poster/ảnh/màn hình có cùng loại. Tập loại trong inventory phải bằng chính xác `depiction_surface_types`. Mỗi review ID 7 `depiction_region` phải tham chiếu đúng một inventory instance qua `depiction_surface_id`; converter xuất mapping `{surface_id, surface_type, box}` trong `depiction_region_surfaces`, trong đó `box` là YOLO xywh chuẩn hóa với 8 chữ số thập phân. Mapping ID/type phải một-một và multiset box phải khớp chính xác với review ID 7 labels, rồi được remap thành model ID 1; duplicate ID hoặc duplicate geometry bị từ chối. Không suy đoán loại bề mặt từ crop, nhãn mũ hay tên file.

`scene_type` có ba giá trị: `depiction_only` khi người liên quan chỉ xuất hiện trong vùng hiển thị, `mixed_scene` khi ảnh có cả người thật trong cảnh và người trong vùng hiển thị, `other` khi không có người được mô tả cần rà nguồn. Ảnh `depiction_only` và `mixed_scene` bắt buộc có ít nhất một `depiction_surface_types`; `other` không được khai báo surface có người. Converter, evaluator và notebook từ chối metadata mâu thuẫn này. `poster_only` là giá trị legacy trong export v1/v2; converter hiện chỉ nhận review JSON v7 và không chuyển đổi trực tiếp các export cũ. V7 bắt buộc `image_review_status` terminal: `reviewed_empty` khi không có annotation và `reviewed_with_labels` khi đã rà hết annotation. Nếu dùng ảnh cũ, hãy rà lại và xuất v7 với `scene_type=depiction_only` cùng medium đã xác minh; `poster_only` không cung cấp medium và không đáp ứng cổng coverage theo loại.

Test khóa phải có từng loại `poster`, `printed_photo`, `screen` trong cả `depiction_only` và `mixed_scene`. Mỗi một trong sáu nhóm phải có ảnh; mỗi instance vật lý khai báo phải có đúng một GT review ID 7 `depiction_region` khớp ID/type/box, được remap thành model ID 1, không có duplicate geometry hoặc false unverified hardhat candidates. Notebook từ chối phát hành nếu thiếu vùng/mapping, thiếu nhóm hoặc có false candidate; service yêu cầu release v9 và `depiction_surface_instance_image_count == image_count` trong mỗi cổng. Biên nhận v2–v7 cũ bị từ chối. Khi một ảnh chứa nhiều loại hoặc nhiều instance cùng loại, tính ảnh đó vào từng loại được khai báo nhưng giữ từng `surface_id` riêng. `other_depiction` được ghi nhận nhưng không thay thế ba loại bắt buộc.

`uncertain` là trạng thái rà soát trong metadata, không phải lớp detector. Không chuyển trạng thái này thành `bare_head`, `depicted_hat` hay một lớp mũ dựa trên phỏng đoán.

## Quy tắc quyết định nguồn

1. Xem toàn ảnh, video và các khung liền kề có sẵn trước khi gán lớp đầu hoặc mũ.
2. Gán một trong các giá trị nguồn trong metadata cho mỗi đối tượng đầu/mũ: `real_scene`, `depicted_surface` hoặc `unresolved`.
3. Chỉ gán lớp `*_worn` hoặc `bare_head` khi `source=real_scene` có bằng chứng trong ngữ cảnh toàn cảnh. Dấu hiệu có thể gồm người có cơ thể và tư thế nằm trong cùng không gian cảnh với camera, tương tác hợp lý với người/vật thật, hoặc chuyển động nhìn thấy được liên tục theo thời gian.
4. Chỉ cần đầu hoặc mũ nằm trong ảnh in, poster, tranh, TV, điện thoại, máy tính hay màn hình là phải gán `source=depicted_surface`. Nếu người trong poster đang đội mũ, gán `depicted_hat` bất kể loại mũ được vẽ. Không gán loại mũ `*_worn` cho người đó.
5. Với mũ nằm ngoài đầu, gán `loose_hat`, kể cả khi nó nằm sát người hoặc được cầm trên tay. Không suy ra mũ đang đội từ khoảng cách gần hay từ hướng nhìn.
6. Nếu ảnh chỉ có crop đầu/mũ, poster mất viền, màn hình chiếm toàn khung, ảnh nhòe hoặc dấu hiệu nguồn mâu thuẫn, gán `source=unresolved`, thêm lý do và đưa sang hàng đợi rà soát. Nếu người rà soát vẫn không thể phân biệt, giữ `uncertain` và không dùng làm ví dụ gán nhãn chắc chắn.
7. Không dùng phát hiện khuôn mặt, confidence của detector, hay việc đối tượng xuất hiện qua nhiều khung làm bằng chứng duy nhất cho `real_scene`. Người hoặc video trong màn hình cũng có mặt, có thể cử động và tồn tại qua nhiều khung.
8. Gán `depiction_region` cho toàn bộ vùng poster, ảnh, ảnh in hoặc màn hình có hình người. Ảnh `depiction_only`/`mixed_scene` chỉ được xác nhận `clear` và chuyển đổi khi có ít nhất một hộp region; phải vẽ riêng từng bề mặt hiển thị có người. Với mỗi annotation review ứng viên `*_worn` hoặc `bare_head`, tính tỷ lệ diện tích ứng viên nằm trong hợp các vùng `depiction_region`. Nếu tâm hộp ứng viên nằm trong bất kỳ vùng nào **hoặc** coverage đạt ít nhất 50%, suppression hộp đó khỏi nhãn người thật. Nếu có phần giao dương nhưng coverage dưới 50% và tâm ở ngoài mọi vùng, chuyển ứng viên sang `uncertain`; không xuất thành nhãn người thật. Chỉ hộp không giao vùng nào mới đủ điều kiện xét tiếp, vẫn cần xác nhận nguồn toàn cảnh. Chỉ `hard_hat_worn` mới được xuất và tính vào số mũ bảo hộ; ba lớp mũ đội review còn lại chỉ phục vụ rà soát và được bỏ khỏi nhãn YOLO.
9. Nếu detector bỏ sót một vùng hiển thị đã biết, ảnh/khung đó phải ở trạng thái `review_required`; không tự chấp nhận bất kỳ số đếm người đội mũ nào cho đến khi người rà soát xác nhận nguồn. Nếu nội dung hiển thị tràn khung, mất ranh giới hoặc không thể tạo hộp `depiction_region`, đánh dấu `uncertain`/`review_required`, không đếm. Không dùng ảnh đó làm bằng chứng rằng mô hình tự phân biệt được người thật với hình ảnh.
10. Hộp `depicted_hat` mô tả riêng mũ/đầu trong nội dung hiển thị và không được đổi thành lớp người thật đang đội mũ.

**Bằng chứng nguồn là thuộc tính của cảnh, không thể luôn xác định từ crop đối tượng.** Vì vậy phải giữ ảnh toàn cảnh gốc. Nếu thấy ranh giới poster/màn hình, gán một hộp detector `depiction_region` bao toàn vùng hiển thị. Hộp này cho phép áp dụng luật loại trừ rõ ràng trước khi đếm.

## Quy tắc vẽ hộp

- Với bốn lớp review `*_worn`, vẽ một hộp quanh vùng đầu và mũ đang đội của người thật. Giữ trọn mũ và phần đầu nhìn thấy, không vẽ toàn thân. Không kéo hộp sang người khác hoặc phần poster cạnh đó.
- Với `bare_head`, vẽ hộp quanh vùng đầu người thật theo phạm vi tương đương. Chỉ gán khi đủ bằng chứng đầu không đội mũ; đầu bị che một phần đến mức không phân biệt được thì là `uncertain`.
- Với `depicted_hat`, vẽ hộp quanh mũ và vùng đầu được mô tả đang đội mũ trong nội dung hiển thị. Một hình có nhiều người đội mũ cần một hộp riêng cho mỗi đầu/mũ, tất cả mang nhãn `depicted_hat`.
- Với `depiction_region`, vẽ một hộp quanh toàn bộ phần poster, ảnh, ảnh in hoặc màn hình có hình người. Giữ đủ ranh giới nhìn thấy được, kể cả khi vùng chứa nhiều người. Nếu có nhiều bề mặt hiển thị, tạo một hộp cho từng bề mặt. Đây là review ID 7 trong ontology tám lớp và được converter ánh xạ thành model ID 1; không phải model ID 7.
- Với `loose_hat`, vẽ hộp chặt quanh từng chiếc mũ rời. Mũ được cầm nhưng không đội vẫn là `loose_hat`.
- Không tạo hộp cho đối tượng ngoài khung hình hoặc vùng mà người gán nhãn không thể xác định. Ghi chú crop, mờ, che khuất hay vùng thiếu ngữ cảnh trong metadata thay vì bịa box.
- Ghi `image_id`, `object_id`, `class_name`, `source`, `person_id` nếu áp dụng, `video_id`/`session_id`, `poster_id` hoặc `screen_id`, `surface_box` trùng tọa độ `depiction_region` nếu cần liên kết metadata, `frame_source_status` (`clear` hoặc `review_required`) và `frame_source_reviewed_at` tùy chọn (thời điểm rà nguồn toàn ảnh), `occlusion`, `visibility`, `reviewer_id`, `review_status` và `uncertain_reason` nếu có. Dùng tọa độ chuẩn hóa theo ảnh gốc cho YOLO và lưu metadata bổ sung theo cùng `image_id`.

## Cảnh nhiều đối tượng và trường hợp khó

- Trong cảnh có người thật đứng cạnh poster, gán riêng từng đối tượng và một hộp `depiction_region` bao poster. Người thật đội mũ nhận lớp đội mũ tương ứng; người trong poster nhận `depicted_hat`. Không gộp hộp của họ, và poster không được cộng vào tổng số người đội. Runtime suppression áp dụng đúng ngưỡng: tâm ứng viên nằm trong vùng hoặc coverage theo hợp các vùng đạt ít nhất 50% thì loại; phần giao dương có coverage dưới 50% và tâm ở ngoài mọi vùng thì gắn `uncertain` và không đếm. Nếu vùng poster bị bỏ sót hoặc ranh giới không thấy, đặt `review_required` và giữ tổng số người đội mũ bằng 0 cho khung đó đến khi được rà soát.
- Trong cảnh có người thật đầu trần cạnh poster người đội mũ, người thật nhận `bare_head`, hình trong poster nhận `depicted_hat`.
- Nếu người thật đang cầm poster có hình người đội mũ, gán hộp người cầm theo trạng thái đầu thật của họ, gán các đầu/mũ trong poster là `depicted_hat` và thêm `depiction_region` cho tờ poster. Áp dụng chính sách tâm/50%/`uncertain` như trên; nếu người thật đứng đè lên poster khiến hộp ứng viên giao vùng, không tự xác nhận họ cho đến khi rà soát.
- Ảnh có cả người thật và màn hình phát video phải được rà theo từng nguồn, với hộp `depiction_region` quanh màn hình. Không dùng tính liên tục giữa các khung làm điều kiện đủ để nhận là người thật.
- Nón bảo hộ, mũ công trường và mũ giao thông phải dựa trên đặc điểm nhìn thấy của loại mũ. Nếu không phân biệt được, dùng `uncertain`, không chọn lớp có vẻ gần nhất.
- Khăn trùm đầu, mũ thời trang khác phạm vi, tóc che kín đầu, đạo cụ hoặc đồ chơi hình mũ không được ép vào một trong bốn lớp review đội mũ. Ghi `out_of_scope` trong metadata rà soát và giữ lại làm mẫu âm tính nếu phù hợp.
- Ảnh hoàn toàn không có đối tượng thuộc ontology review tám lớp được giữ như ảnh nền với danh sách box rỗng. Chúng cần có ảnh đường phố, phòng làm việc, cửa hàng, bảng hiệu và cảnh có poster để đo phát hiện giả.

## Lưu ý đối với bước loại trừ poster và màn hình

Nhãn YOLO riêng lẻ không đủ để chứng minh nguồn của một cái đầu. Huấn luyện model hai lớp với `depiction_region` từ các hộp ranh giới poster/màn hình. API chỉ phát hiện `hard_hat_worn` và `depiction_region`; với mỗi ứng viên model `hard_hat_worn`, API, giao diện inference và evaluator dùng cùng thứ tự quyết định: (1) nếu tâm ứng viên nằm trong vùng hoặc coverage tính trên hợp các vùng đạt từ 50% trở lên, suppression và không đếm; (2) nếu coverage lớn hơn 0 nhưng dưới 50% và tâm ở ngoài mọi vùng, trả `uncertain` và không đếm; (3) nếu vùng hiển thị bị bỏ sót, ảnh/khung cần rà soát và số người đội mũ bằng 0 đến khi người rà soát xác nhận nguồn. Các review class `traffic_helmet_worn`, `cap_worn`, `beanie_worn` và `bare_head` không phải đầu ra của model. Trong bước gán nhãn và chuyển đổi dữ liệu, áp dụng kiểm tra nguồn tương ứng cho các annotation review đầu/mũ; `bare_head` mô tả đầu trần của người thật nhưng không làm tăng số người đội mũ.

`frame_source_status` phải mặc định là `review_required`; chỉ chuyển thành `clear` sau khi bước rà nguồn xác nhận không còn vùng hiển thị bị bỏ sót hoặc chưa rõ. Giao diện chặn xác nhận `clear` khi scene/surface metadata cho biết có nội dung hiển thị nhưng chưa có hộp `depiction_region`; thay đổi scene hoặc loại bề mặt sẽ đặt lại trạng thái cần rà và làm các nhãn đầu người trở về chưa xác định. Khi suppression theo luật tâm/50%, văn bản cho người dùng là: **“Đã loại dự đoán nằm trong vùng ảnh hiển thị; không tính là người đang đội mũ.”** Khi overlap dương dưới 50% và tâm ở ngoài, hiển thị: **“Chưa xác định nguồn người này. Không tính vào số người đang đội mũ.”** Khi nguồn của ảnh/khung chưa xác minh được, hiển thị: **“Chưa xác minh được nguồn ảnh hiển thị. Chưa ghi nhận người đội mũ (0). Cần rà soát.”** Không hiển thị dự đoán bị suppression như người đang đội mũ.

Tập dữ liệu cần có ví dụ khó mà poster chiếm phần lớn khung, mất viền hoặc bị detector bỏ sót, phản chiếu/lóa, poster có ảnh chụp thật, màn hình đang phát video, poster được cầm, và người thật đứng trước hoặc sát poster. Không dùng một ngưỡng confidence đơn lẻ để biến phát hiện mũ trong nội dung hiển thị thành người thật. Với poster bị bỏ sót hoặc tràn khung, kiểm tra rằng API giữ `wearer_count=0` và `review_required=true`; giao diện/review phải giữ ứng viên ở trạng thái chưa xác minh hoặc cần rà cho đến khi người rà soát xử lý nguồn.

## Chọn mẫu, chia tập và kiểm soát rò rỉ

- Bắt đầu với pilot **150–250 ảnh**. Hai người rà độc lập tất cả ảnh pilot, đặc biệt các cặp `real_scene`/`depicted_surface`, bốn lớp review đội mũ, poster mất viền và người thật cạnh poster. Bao gồm mẫu đủ lớn để có `depiction_region` và mẫu không nhìn thấy ranh giới hiển thị.
- Thảo luận mọi bất đồng trước khi mở rộng gán nhãn. Ghi tỷ lệ đồng thuận riêng cho nguồn và lớp. **Ít nhất 95% đồng thuận nguồn** trên pilot là prerequisite thủ công trước khi phát hành. Review JSON hiện không lưu lượt rà độc lập hoặc phép tính đồng thuận; không được tự giả định đạt hay ghi đồng thuận suy ra từ nhãn cuối cùng. Nếu thấp hơn, sửa quy tắc, huấn luyện lại người gán nhãn và gán lại pilot.
- Release sufficiency floor bắt buộc của model YOLO hai lớp: ít nhất **300 `hard_hat_worn` box train và 100 locked-test box**, cùng ít nhất **300 `depiction_region` box train và 100 locked-test box**. Không đặt quota box train theo lớp cho review ID 1–6 vì converter không đưa chúng vào model. Vẫn thu và rà ảnh có mũ giao thông, mũ lưỡi trai, mũ len, đầu trần, mũ trong hình, mũ rời và cảnh nền làm ví dụ âm tính cho target `hard_hat_worn`; giữ nhãn `depiction_region` trên bề mặt hiển thị khi có. Áp dụng sàn nhóm theo từng loại mũ dễ nhầm ở mục dưới.
- Mỗi nguồn hard-negative `poster`, `printed_photo`, `screen`, `loose_hat`, `mixed_scene` và `empty_background` cần ít nhất **300 group độc lập trong train và 100 group độc lập trong locked test**. Đếm `group_id` duy nhất trong đúng split, không đếm frame/ảnh lặp trong cùng group nhiều lần. Đây là release floor; sáu cổng surface × scene vẫn phải đạt riêng.

Converter tạo template sibling `hardhat_only_v1_hard_negative_source_groups.csv`, một dòng cho mỗi `(split, group_id)` và `review_status=pending`. Người rà phải xác nhận từng group rồi điền `hard_negative_sources` bằng JSON array thuộc đúng sáu nguồn trên và `hat_type_negative_sources` bằng JSON array traffic/cap/beanie; group không thuộc nguồn nào cần `[]` sau khi đã rà. Notebook đối chiếu split/group với `split_manifest.csv`, bề mặt với `dataset_image_sources.json`, `mixed_scene` với scene metadata, `loose_hat`/hat-type counts với review annotation counts, và `empty_background` với định nghĩa group rỗng đã rà. Thiếu dòng, duplicate group, `pending`, nguồn sai hoặc mapping không khớp sẽ chặn train/release. Upload sidecar đã xác nhận lên Drive với tên `hard_negative_source_groups.csv`; notebook ghi SHA-256 của sidecar vào summary và receipt v9.
- Chia train/validation/test theo `person_id`, `video_id`, `session_id`, địa điểm/quang cảnh và `poster_id`/`screen_id`. Mọi khung từ cùng video hoặc ảnh của cùng poster phải ở cùng một split. Không để các crop của một ảnh gốc sang tập khác.
- Dùng khoảng 70% train, 15% validation, 15% test làm mốc ban đầu. Điều chỉnh theo số cảnh độc lập, giữ test đủ đại diện cho từng lớp và nhóm nguồn. Khóa test trước khi chọn checkpoint hoặc confidence.
- Dò bản trùng theo hash chính xác và ảnh gần giống, rồi rà bằng nhóm nguồn. Giữ bản ghi các ID được loại và lý do. Không dùng tên nguồn hoặc tiền tố ID làm bằng chứng các split độc lập theo cảnh.
- Đưa lỗi validation vào vòng bổ sung dữ liệu. Không sửa nhãn test để làm đẹp kết quả. Nếu phát hiện lỗi test, tạo phiên bản dữ liệu mới và báo cáo kết quả trước/sau cùng ảnh hưởng.

### Sàn dữ liệu cho mũ dễ nhầm

| Loại mũ đã rà | Train | Validation | Locked test |
| --- | ---: | ---: | ---: |
| Mũ bảo hiểm giao thông (`traffic_helmet_worn`) | 300 | 30 | 100 |
| Mũ lưỡi trai/kê-pi (`cap_worn`) | 300 | 30 | 100 |
| Mũ len (`beanie_worn`) | 300 | 30 | 100 |

Theo quyết định chủ dự án ngày 28/11/2026, floor cho mỗi subtype là 300 nhóm train, 30 nhóm validation và 100 nhóm locked test. Sàn tính theo **nhóm độc lập** cho từng loại mũ trong từng tập. `service/app.py` kiểm tra floor subtype trong release summary; Notebook 03 kiểm tra từng subtype/split ở preflight và final release gate. Riêng chọn threshold validation cần ít nhất 30 group subtype-only độc lập cho mỗi subtype; locked test cần ít nhất 100 group subtype-only. Dữ liệu hiện tại chưa được xác nhận đạt các floor. Báo riêng số nhóm/ảnh đủ điều kiện, số hộp dự đoán và số nhóm/ảnh có dự đoán hardhat cho từng loại trên validation và locked test.

Floor nhóm âm tính hiện không phải cổng từ chối hiệu năng. Với yêu cầu “chỉ báo hardhat nhưng không báo nhầm traffic/cap/beanie”, group chỉ là **subtype-only** nếu mọi ảnh trong group đều được rà, không có hardhat, subtype đội mũ khác hoặc bất kỳ depiction surface/region nào, và ít nhất một ảnh xác nhận subtype đang xét. Chấm mọi ảnh trong group đủ điều kiện. Notebook chọn một threshold chung chỉ từ validation: ngưỡng thấp nhất lớn hơn confidence hardhat cao nhất ở ít nhất 30 group subtype-only mỗi subtype (margin 1e-6), rồi ghi bằng chứng/hash trước locked test. Trên ít nhất 100 group subtype-only locked-test độc lập của mỗi loại, gate yêu cầu **0 hộp `hard_hat_worn`, 0 ảnh và 0 group có dự đoán hardhat**; một lỗi bất kỳ chặn release. `uncertain`/chưa rõ không được tính. Đây là kết quả trên locked test, không phải bảo đảm tổng quát. Notebook 03, evaluator chẩn đoán, test summary, receipt v9 và API áp dụng cùng rule; API xác minh threshold/evidence hashes và thời gian evidence trước test. Chỉ cấp release khi dữ liệu đạt floor và locked test thực tế qua cả ba subtype.

**Một nhóm độc lập** là một đơn vị nguồn/cảnh có căn cứ truy vết và một `group_id` duy nhất. Gộp vào cùng nhóm mọi ảnh có quan hệ qua cùng người nhận diện được trong hồ sơ, cùng video/phiên chụp hoặc cảnh quay, cùng poster/nội dung màn hình, hoặc cùng ảnh gốc (gồm crop, khung liền kề, ảnh chỉnh sửa, ảnh tăng cường và ảnh gần trùng). Gộp cả các liên kết gián tiếp. Mỗi nhóm chỉ ở một split. Khi thiếu căn cứ xác định hai nhóm độc lập, giữ chờ rà và chưa tính vào sàn; tên tệp, tên nguồn hay SHA khác nhau chưa đủ để tách nhóm.

Chỉ đếm một lần mỗi `(split, group_id)` cho một loại mũ khi nhóm đã rà xong và có ít nhất một hộp xác nhận người thật trong cảnh đang đội loại đó. Mũ rời, mũ trong nội dung hiển thị và hộp chưa xác định không đủ điều kiện. Một nhóm có thể tính vào nhiều loại nếu mỗi loại có hộp xác nhận riêng. Ví dụ, 20 frame có cùng người đội mũ xe máy trong một clip tính là một nhóm mũ giao thông.

## Kiểm tra chất lượng và điều kiện nghiệm thu

Trước khi đóng phiên bản dữ liệu, xác nhận:

- `data.yaml` có đúng hai tên lớp model theo thứ tự ID: `hard_hat_worn` và `depiction_region`. Ontology review tám lớp chỉ tồn tại trong browser JSON. Mỗi box YOLO có đúng năm trường, lớp hợp lệ và tọa độ chuẩn hóa trong `[0, 1]`. Metadata có `frame_source_status`, mặc định `review_required`; chỉ cho đếm khi đã được xác nhận `clear`.
- Ảnh minh họa được vẽ lại từ nhãn và rà toàn bộ pilot. Không có ví dụ `depicted_surface` mang nhãn `*_worn` hoặc `bare_head`.
- Mọi đối tượng được ghi là `real_scene` có thể được xác nhận từ toàn cảnh hoặc chuỗi video gốc, không chỉ từ crop.
- Kiểm kê ảnh nền và hard negative theo nhóm `poster`, `printed_photo`, `screen`, `loose_hat`, `mixed_scene` và `empty_background`.
- Đếm train/test theo **cảnh/video/poster độc lập** cũng như theo box; không báo số khung là số mẫu độc lập. Đạt release floor ở từng lớp model và từng hard-negative source group theo mục chọn mẫu.
- Trên tập test poster/ảnh/màn hình bắt buộc, số trường hợp được tính là người thật đang đội mũ phải bằng **0**. Metadata đã rà phải khớp mọi ảnh test; từng medium `poster`, `printed_photo`, `screen` phải có ảnh trong cả `depiction_only` và `mixed_scene`. Mỗi stratum cần ảnh dương và không có false unverified worn candidates; đồng thời đủ các floor box/group độc lập ở trên. Đánh giá cả khi region được phát hiện, bị bỏ sót và không có ranh giới. Mẫu bị bỏ sót hoặc tràn khung phải trả `review_required`/`uncertain` với số đếm bằng 0, không được auto-accept. Báo riêng số group và số lượt dương tính giả theo medium và scene type. Bất kỳ lượt đếm giả nào đều chặn nghiệm thu.
- Đánh giá cảnh hỗn hợp theo từng người thật trong cảnh. Người thật được đếm đúng; mọi người đội mũ trong hình hiển thị bị loại. Không gán `bare_head` cho đầu người trong poster/ảnh/màn hình; lớp này chỉ mô tả đầu trần của người thật và không làm tăng số người đội mũ. Ca thiếu bằng chứng được trả `uncertain`/không đếm và thống kê riêng.
- Kiểm tra cùng một luật trong API, giao diện và evaluator bằng hộp chuẩn tại coverage 0%, dưới 50%, đúng 50% và trên 50%, với tâm cả bên trong lẫn bên ngoài vùng. Tâm bên trong hoặc coverage ≥50% phải bị suppression; coverage dương dưới 50% khi tâm ở ngoài phải thành `uncertain` và không đếm; region bị bỏ sót/tràn khung phải `review_required` và đếm 0 đến khi review. Đo tác dụng phụ trên cảnh người thật đứng sát hoặc che một phần poster.

### Chỉ báo mũ bảo hộ lao động

- **Dữ liệu.** Chỉ gán `hard_hat_worn` khi người thật trong cảnh đang đội mũ bảo hộ lao động. Giữ mẫu dễ nhầm theo đúng nhãn riêng hoặc làm mẫu âm tính sau khi rà soát. Giữ cả cảnh có mũ bảo hộ và mũ dễ nhầm để kiểm tra từng đối tượng trong cùng khung hình. Chuyển ca chưa xác định được loại mũ sang rà soát trước khi đưa vào huấn luyện.
- **API và giao diện.** Chỉ dùng dự đoán model `hard_hat_worn` cho chỉ báo mũ bảo hộ lao động; `depiction_region` là lớp phụ để lọc nguồn, không phải loại mũ. Áp dụng quy tắc lọc poster, ảnh in và màn hình trước khi hiển thị. Gắn trạng thái cần rà soát khi nguồn chưa được xác minh, kể cả khi mô hình dự đoán đúng loại mũ. API hiện tại luôn trả `wearer_count=0` và chưa có endpoint xác nhận thủ công; không hiển thị ứng viên như số đã xác nhận.
- **Nghiệm thu trên tập test độc lập đã khóa.** Kiểm thử cả cảnh chỉ có mũ ngoài mục tiêu và cảnh có mũ bảo hộ thật đứng cạnh mũ dễ nhầm. Dùng nhãn rà soát để đo số lần mô hình dự đoán nhầm `hard_hat_worn` theo từng nhóm mũ giao thông, mũ lưỡi trai hoặc kê-pi, mũ len và các nhóm dễ nhầm khác có trong tập test. Đo riêng số mũ bảo hộ thật bị bỏ sót. Kiểm tra đầu ra API và giao diện trên các cảnh này, gồm cả mũ rời và mũ trong hình hiển thị. Các nhóm mũ ngoài mục tiêu chỉ dùng để đối chiếu khi nghiệm thu, còn đầu ra mô hình chỉ dự đoán `hard_hat_worn` và vùng phụ `depiction_region`.

Kết quả các mục tiêu kiểm thử là điều kiện đo được, không phải bảo đảm chỉ từ quy tắc gán nhãn. Chỉ phát hành mô hình sau khi chạy kiểm thử toàn luồng từ ảnh/video đến kết quả đếm trên các split đã khóa.
