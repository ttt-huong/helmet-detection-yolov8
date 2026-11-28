# Audit tiến độ kế hoạch dữ liệu và phát hành — 2026-11-28

## Phạm vi và cách tính

Đây là đối chiếu tĩnh giữa các bước 1–9 trong [checklist kiểm thử](../checklist_kiem_thu.md), [kế hoạch hoàn tất dữ liệu](../ke_hoach_hoan_tat_du_lieu.md) và bằng chứng trong workspace. Không truy cập Drive/VM từ xa; các phát biểu “không thấy” dưới đây chỉ nói về workspace, trạng thái artifact bên ngoài workspace là unknown. Không sửa checklist/kế hoạch, dữ liệu, notebook, converter, evaluator hay API; không chạy huấn luyện, chuyển đổi hoặc inference.

Không tính một tỷ lệ hoàn thành chung cho toàn kế hoạch. Các mục trộn lẫn công việc kỹ thuật, cổng chất lượng, quota theo box/group và các hoạt động vận hành; trọng số chung không được định nghĩa. Đếm các mục “đã làm” như số phần trăm cũng sẽ gộp nhầm việc code tồn tại với dữ liệu/release đã đạt. Báo cáo chỉ tính phần trăm khi có mẫu số và ngưỡng được chốt trong tài liệu nguồn; các việc còn lại ghi trạng thái `đã có bằng chứng`, `một phần`, `chưa đạt` hoặc `chưa bắt đầu`.

## Các tỷ lệ có mẫu số rõ

| Cổng đo được | Kết quả hiện có | Ý nghĩa |
|---|---:|---|
| Pilot: trạng thái ảnh ≥95% | 120/175 = **68,57%** | Chưa đạt; có **55** cặp trạng thái ảnh khác nhau. |
| Pilot: metadata nguồn khớp chính xác ≥95% | 175/175 = **100%** | Đạt metric này; không đồng nghĩa nhãn box đã đồng thuận. |
| Pilot: head/source disposition ≥95%, IoU 0,5 | 21/462 = **4,55%** | Chưa đạt. 441 box unmatched; 152 box unmatched có disposition unresolved. |
| Số metric pilot đạt ngưỡng | **1/3 = 33%** | Tỷ lệ đếm cổng metric, không phải phần trăm hoàn thành dự án; comparison là descriptive-only và không tự cấp pass. |
| Inventory quota đủ điều kiện | **0/33 cổng quota đạt** | CSV có 33 yêu cầu quota và 1 discovery lead bị loại khỏi quota; 33/33 quota có `eligible_current=0`, `status=not met`, `remaining=minimum`. Candidate boxes không có group/split không được tính quota. |
| Artifact phát hành tìm thấy trong workspace | **0/3** | Workspace search không thấy `best.pt`, `deployment_release.json` hoặc `deployment_test_summary.json`; Drive/VM từ xa chưa được kiểm tra nên trạng thái artifact ở đó unknown. |

Mẫu pixel adjudication gồm 13 ảnh được chọn để chẩn đoán; báo cáo ghi 32 đầu/mũ có thể phân loại và 5 còn unresolved. Không tính 13/175 thành “7,4% tiến độ”: đây không phải lượt adjudication toàn roster hay mẫu đại diện. Năm trường hợp này cũng không phải các head còn unresolved trong batch 19 ảnh; proposal v10 đã phân xử một head ở #19 thành `hard_hat_worn`, còn bốn head ở #1, #5 (hai vị trí) và #16 vẫn chưa có nhãn xác định. Đây cũng không phải cùng mẫu số với 152 box unresolved của comparator.

## Trạng thái theo các mục checklist

| Mục | Tiến độ có bằng chứng | Trạng thái điều kiện đầu ra |
|---|---|---|
| 1. Code v7 và browser gates | Pipeline/schema v7 và nhiều UI/geometry smoke tổng hợp đã được kiểm tra. Browser evidence có lần nạp fixture tại 8793; lần kéo box tạm ở 8794 timeout, sau đó smoke riêng tại 18765 đã vẽ một box synthetic `loose_hat`, hoàn tất terminal review và export v7. | **Một phần.** Chưa có converter end-to-end; thay đổi cho phép export khi còn annotation `uncertain` chưa được browser-smoke xác minh đầy đủ. Smoke 18765 chỉ dùng fixture tổng hợp, không phải dữ liệu dự án. |
| 2. Pilot A/B và agreement | Hai lượt delegated AI bao phủ 175/175 ảnh mỗi lượt; schema/roster checks và comparator đã hoàn tất. | **Baseline đo xong, pilot gate trượt.** Chỉ 1/3 metric đạt ≥95%; đây không phải human A/B agreement. |
| 3. Adjudicate pilot | Có pixel adjudication chẩn đoán 13 ảnh: 32 đầu/mũ có lớp hỗ trợ, 5 còn unresolved. | **Một phần.** Chưa adjudicate đủ 175 ảnh hoặc xử lý mọi unmatched/unresolved; mẫu 13 ảnh không tạo pass cho pilot. |
| 4. Bổ sung nguồn, group/split và khóa test | Có source discovery và capture protocol; CAP và SALSA là hai lead mới được ghi trong bản rà nguồn công khai, ở mức discovery và chưa được stage/cộng quota trong inventory workspace. Workspace chưa có evidence về group/split dự án hợp lệ hoặc locked-test marker runtime. Notebook source có cơ chế marker; repo không có notebook execution output. Drive/VM từ xa chưa xác minh. | **Chưa đạt theo inventory workspace.** Dữ liệu đủ điều kiện vẫn 0/33 cổng quota; thiếu provenance, grouping evidence và đủ nhóm độc lập. |
| 5. Convert và validate dataset | Converter/validator có trong source. Proposal v10 đã qua kiểm tra schema/diff/geometry tĩnh; có 19 ảnh/78 annotations (65 hardhat, 4 cap, 8 bare-head, 1 loose-hat), 1 box `uncertain` và 4 head ứng viên chưa được gán hộp xác định. `group_id`/project `split` rỗng 19/19; provenance/rights-holder/privacy chưa được xác minh độc lập; không có `depiction_region` hoặc scene depiction cho split contract. | **Chưa có kết quả conversion end-to-end trong workspace; conversion chưa đủ điều kiện từ batch này.** Workspace không có YOLO dataset/ZIP đã tạo và kiểm tra; trạng thái Drive từ xa chưa xác minh. |
| 6. Train và locked-test release gate | Notebook và evaluator source hiện gom eligibility theo toàn bộ `group_id`, loại group nếu có subtype khác hoặc depiction. Notebook chọn threshold chỉ từ group subtype-only trong validation, tạo `validation_threshold_evidence.json` có SHA-256 và ràng buộc checkpoint/dataset/metadata/manifest/validation labels. Trước khi mở ảnh cho lượt đánh giá locked test, cell tạo `locked_test_start.json` bằng exclusive-create; marker đã có thì chặn rerun hoặc đổi threshold. API v9 kiểm tra hash evidence/marker, liên hệ thời gian bắt đầu với evidence, threshold selection rule và gate fields trong summary. Đây là cơ chế trong source tĩnh; repo không có execution output hoặc evidence/marker runtime xác nhận run trên dữ liệu thực. | **Code có trong source; runtime/data gate chưa pass trong bằng chứng đã kiểm tra.** Workspace không có notebook-run artifacts, checkpoint, locked-test result hoặc receipt; trạng thái Colab/Drive từ xa chưa xác minh. Cần hoàn tất review/verification rồi mới đánh giá gate theo kết quả thật. |
| 7. Deploy artifact và mở tunnel | Hướng dẫn VM/Docker/SSH có sẵn. | **Chưa có bằng chứng triển khai trong workspace.** VM/host/tunnel hoặc API cloud từ xa chưa được kiểm tra. |
| 8. Readiness check | Snapshot 28/11 lúc 15:52–15:53 +07, GET độc lập lặp lại lúc 15:57: Docker preview API ở 7860 trả `/livez` 200 nhưng `/health` 503 (`model_loaded=false`, `checkpoint_missing`); tunnel 7861 và static server 8765 tắt. Static server 8793 trả `/` và `/demo.html` 200, còn `/health` 404. | **Readiness chưa đạt.** Process 7860 chưa có checkpoint; 8793 chỉ phục vụ giao diện tĩnh, không phải inference API. |
| 9. Browser inference | Browser evidence xác nhận manual labeler nhận fixture cục bộ; demo 8793 báo không có API và khóa chạy. | **Chưa có model inference trong các phiên browser được kiểm tra.** Không có ảnh nào trong các phiên đó được gửi tới API; static UI smoke không tính là model test. |

## Kết luận tiến độ

Phần đã có bằng chứng trong workspace tập trung ở **code/schema và smoke tổng hợp**, cùng baseline comparator và một mẫu pixel adjudication nhỏ. Notebook/evaluator có gate group-level; Notebook có logic threshold validation-only, evidence hash và exclusive marker chống rerun; API v9 kiểm tra hash evidence/marker. Đây là trạng thái source tĩnh, không phải kết quả chạy. Workspace chưa có threshold evidence/marker runtime, chưa chứng minh nhóm nào đủ điều kiện và không được tính code hiện có là data/release gate pass. Pilot chưa qua cổng agreement; cả **33/33 cổng quota** đều chưa đạt. Workspace chưa có dataset conversion hay bằng chứng train, locked-test, deployment hoặc browser inference; Drive/VM từ xa chưa được kiểm tra. Không nên diễn đạt đây là một dự án “33% hoàn tất”: 33% chỉ là 1/3 metric pilot đạt ngưỡng; các cổng dữ liệu và phát hành độc lập vẫn chưa đạt.

## Bằng chứng đối chiếu

- [Checklist và trạng thái các bước](../checklist_kiem_thu.md), [kế hoạch và ngưỡng dữ liệu](../ke_hoach_hoan_tat_du_lieu.md).
- [Comparator summary](../../datasets/candidates/construction-ppe-pilot-draft/compare-v7-ai-a-b-normalized/summary.json), [audit số học comparator](comparator-v7-metric-arithmetic-audit-2026-11-28.md).
- [Pixel adjudication mẫu 13 ảnh](pilot-13-sample-independent-adjudication-2026-11-28.md), [inventory quota](data_readiness_gap_inventory_2026-11-28.csv), [quota reconciliation](quota-reconciliation-2026-11-28.md).
- [Backlog re-review pilot 175 ảnh — các việc P0–P5 chưa thực hiện](pilot-175-review-rework-backlog-2026-11-28.md).
- [Blockers conversion v9 history](candidate-v9-conversion-blockers-2026-11-28.md), [blockers conversion v10](candidate-v10-conversion-blockers-2026-11-28.md), [training/deployment readiness](training_deployment_readiness_2026-11-28.md).
- [Review gate từ chối subtype](non-target-hat-rejection-gate-code-review-2026-11-28.md), [Notebook 03](../../notebooks/03_train_hat_types_colab.ipynb), [evaluator](../../scripts/evaluate_hat_types.py), [API](../../service/app.py).
- [Live API/tunnel check](live-api-readiness-2026-11-28.md), [browser demo readiness](browser-demo-readiness-2026-11-28.md).

## Cập nhật cùng ngày sau rà soát code và trình duyệt

Phần kiểm kê phía trên phản ánh snapshot khi lập audit. Sau đó đã có các thay đổi code sau, chưa làm thay đổi cổng dữ liệu hoặc trạng thái phát hành:

- API v9 áp dụng ngưỡng hiệu lực `max(ngưỡng người gọi, ngưỡng khóa từ validation)` và cho phép ngưỡng đến `1.00`. Demo web nay chấp nhận ngưỡng hiệu lực hữu hạn nằm trong `[ngưỡng yêu cầu, 1.00]`, thanh trượt lên đến 100%, và giữ nút inference tắt cho đến khi `/health` xác nhận model sẵn sàng cùng class order. `py_compile`, `node --check`, kiểm tra hợp đồng ngưỡng và readiness-order đều qua; route contract dùng dependency stubs vì môi trường chưa cài FastAPI.
- Notebook 03 cell 11 kiểm tra hash ảnh/nhãn validation trước marker one-shot và trước khi xóa receipt cũ; sau khi tạo marker bằng exclusive-create mới dọn output cũ, đọc metadata/nhãn locked-test và chạy inference. Kiểm tra cú pháp và source-order qua. Cell 3 vẫn đọc số đếm nhãn test trong preflight để kiểm tra đủ dữ liệu; marker thể hiện bắt đầu lượt đánh giá locked-test trong cell 11, không phải lần đọc test tuyệt đối đầu tiên của toàn notebook.
- Snapshot trình duyệt 15:52–15:53 +07 (GET độc lập 15:57) xác nhận trang thử tại `http://127.0.0.1:7860/demo.html`: Docker preview API trả `/livez` 200 nhưng `/health` 503 (`model_not_loaded`, `checkpoint_missing`), nên nút inference bị khóa. Trang static riêng ở `http://127.0.0.1:8793/demo.html` trả 200 cùng với `/`, còn `/health`, `/docs`, `/openapi.json` trả 404; giao diện này không kết nối API. Thanh trượt confidence 1–100%. Trong các phiên browser được kiểm tra, không có ảnh được tải lên hoặc gửi đi. Có thể kiểm tra giao diện/trạng thái sẵn sàng trong trình duyệt, chưa thể chạy inference mô hình.
- Workspace search vẫn không tìm thấy `best.pt`, `deployment_release.json`, `deployment_test_summary.json`, `validation_threshold_evidence.json` hoặc `locked_test_start.json`. Docker preview cục bộ là process không có checkpoint, không phải API inference-ready. Lượt kiểm kê này không chạy training, locked-test, deploy hoặc inference model; Drive/VM từ xa chưa được kiểm tra.

Vì vậy các bản sửa tăng độ an toàn và sửa hợp đồng browser/API, đồng thời bổ sung một bản adjudication v10 cho lô 19 ảnh; **chúng chưa nâng quota hoặc gate release**: dữ liệu đủ điều kiện vẫn 0/33 cổng quota (CSV có thêm 1 discovery lead bị loại; CAP và SALSA là hai discovery leads riêng, chưa cộng quota), lô 19 ảnh vẫn chưa converter-eligible, và pilot 175 ảnh vẫn chưa qua cổng agreement.
