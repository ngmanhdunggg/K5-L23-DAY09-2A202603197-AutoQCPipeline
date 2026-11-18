# Báo cáo Day 09 — Nguyễn Mạnh Dũng, 2A202603197

## 1. Kết luận trước
Pipeline kết luận Hold. Trong 224 ảnh đầu vào, 19 ảnh bị loại và 205 ảnh được giữ lại. Sau sửa tự động và mô phỏng duyệt 80 ảnh, không còn lỗi bắt buộc nhưng còn 38/205 ảnh cảnh báo chưa duyệt (18,54%), vượt ngưỡng 10%. Dataset được xuất dưới dạng bản nháp để thử nghiệm, chưa được phát hành.

## 2. Lỗi và phân việc
Thống kê từ `02_error_list_v1.csv`. Mẫu số: 224 ảnh đầu vào; sau intake còn 205 ảnh để QC nhãn. Một ảnh có thể có nhiều mã lỗi; cảnh báo ngữ nghĩa là nghi ngờ, chưa phải lỗi đã xác nhận. Người duyệt trong lần chạy này được mô phỏng.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2/224 ảnh | Máy (intake) | Loại ảnh không đọc được đầy đủ |
| `BAD_SIZE` | 3/224 ảnh | Máy (intake) | Loại ảnh dưới kích thước tối thiểu |
| `DUP_IMAGE_EXACT` | 8/224 ảnh | Máy (intake) | Loại bản trùng từng byte |
| `DUP_IMAGE_NEAR` | 2/224 ảnh | Máy (intake) | Loại ảnh gần trùng theo pHash |
| `LEAK_TEST` | 4/224 ảnh | Máy (intake) | Loại ảnh trùng kho test/val để tránh rò rỉ |
| `MISSING_LABEL_FILE` | 6/205 ảnh | Người | Máy chuyển hàng đợi, không tự tạo nhãn |
| `EMPTY_LABEL` | 12/205 ảnh | Người | Phân biệt ảnh nền với ảnh bị thiếu nhãn |
| `BAD_FORMAT` | 3 dòng / 3 ảnh | Máy | Xoá dòng sai định dạng YOLO |
| `BAD_CLASS_ID` | 6 dòng / 6 ảnh | Máy | Xoá dòng có ID lớp ngoài schema |
| `BOX_ZERO` | 4 dòng / 4 ảnh | Máy | Xoá box có cạnh không dương |
| `DUP_BOX` | 7 dòng / 7 ảnh | Máy | Xoá box lặp cùng lớp ở dòng sau |
| `BOX_OUT_OF_IMAGE` | 8 dòng / 8 ảnh | Máy | Cắt box về trong biên ảnh |
| `BAD_CLASS_NAME` | 2 lỗi / 1 file YAML | Máy | Ghi lại tên lớp theo cấu hình |
| `BOX_TINY` | 6 dòng / 4 ảnh | Người | Kiểm tra box có cạnh ngắn dưới 12 px |
| `BOX_HUGE` | 3 dòng / 3 ảnh | Người | Kiểm tra box chiếm hơn 95% diện tích ảnh |
| `CLASS_RARE` | 4 cảnh báo cấp dataset | Người | Xem lại phân bố lớp; không tự sửa nhãn để cân bằng |
| `POSSIBLE_MISSING` | 53 cảnh báo / 52 ảnh | Người | Xác minh vật thể có bị thiếu box không |
| `POSSIBLE_LOOSE_BOX` | 28 cảnh báo / 24 ảnh | Người | Kiểm tra độ khít của box |
| `POSSIBLE_WRONG_CLASS` | 18 cảnh báo / 18 ảnh | Người | Xác minh lớp của đối tượng |
| `POSSIBLE_FALSE_POS` | 29 cảnh báo / 27 ảnh | Người | Kiểm tra box không được model xác nhận |

Hàng đợi có 125 ảnh, xếp theo tổng trọng số các cảnh báo (có xét confidence) và dấu vết sửa tự động; điểm bằng nhau thì xếp theo tên ảnh. `img_0020` đứng đầu với 11,524 điểm do có `FIXED_DROP_LINE`, `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`. Ảnh thiếu nhãn có điểm `NEEDS_LABEL = 10`. Ngân sách mô phỏng xử lý 80/125 ảnh, gồm 74 ảnh có cảnh báo ngữ nghĩa và 6 ảnh thiếu file nhãn. Đây là số ảnh được xem, không có nghĩa mọi cảnh báo đều là lỗi thật. Sau duyệt vẫn còn 38/205 ảnh cảnh báo chưa duyệt.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 4 | Gần trùng: 1,00 / 0,50 → 1,00 / 0,67 | Tăng recall, ưu tiên tránh loại nhầm ảnh. |
| `second_opinion.conf` | 0.25 | 0.6 | Nhầm lớp: 0,56 / 0,83 → 0,62 / 0,83; thiếu box: 0,50 / 1,00 → 0,57 / 1,00 | Giảm báo động giả; đánh đổi recall box lỏng từ 0,40 xuống 0,20. |

Hạn chế: calib chỉ có 39 ảnh nên kết quả tốt chưa bảo đảm đúng trên raw. Ví dụ, công cụ hỗ trợ kiểm tra thấy ngưỡng pHash 16 có precision 1,00 trên calib nhưng gộp nhầm `img_0008` và `img_0011` là hai cảnh khác nhau (`evidence/raw_pairs.jpg`). Vì vậy chọn ngưỡng 4, chấp nhận bỏ sót 2/6 ca gần trùng trên calib.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
(a) chứng minh gate chặn đúng: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên ảnh thiếu file nhãn còn nguyên), chỉ ra kết luận **Rework**, mã thoát 20 và việc **không xuất** dataset. (Đừng sửa tay `work/run/ds`: pipeline dựng lại thư mục này từ raw mỗi lần chạy.) (b) ≥ 2 điểm mù có bằng chứng (box lỏng nhẹ, nhầm lớp mà model lớn cũng nhầm, ảnh trùng biến đổi mạnh…).

Với `--budget 0`, pipeline còn 6 lỗi thiếu nhãn nên trả về **Rework**, mã thoát **20** và không xuất dataset. Điểm mù trên calib: bỏ sót **2/6 ca gần trùng** ở `phash_dist=4` và **4/5 ca box lỏng** ở `conf=0.6` (theo `calibration/calibration_report.md`).

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.663 ± 0.016 | 0.469 ± 0.002 | 0.733 ± 0.022 | 0.589 ± 0.046 |
| clean | 205 | 2 | 0.680 ± 0.011 | 0.488 ± 0.001 | 0.808 ± 0.002 | 0.556 ± 0.048 |

Chênh mAP50 (clean − raw) = **+0.018**.

Chênh mAP50 (clean − raw) là +0,018, cùng cỡ độ lệch chuẩn giữa các seed (raw: 0,016, clean: 0,011), nên chưa đủ bằng chứng kết luận clean tốt hơn ổn định. Cần chạy thêm seed để kiểm chứng.
- Giả thuyết 1: ảnh trùng/rò rỉ test trong raw có thể làm điểm raw cao hơn thực tế. Kiểm tra bằng cách loại ảnh rò rỉ rồi train lại cùng cấu hình.
- Giả thuyết 2: clean vẫn còn nhãn máy chưa được duyệt, có thể hạn chế chất lượng model. Kiểm tra bằng cách duyệt thêm nhãn rồi train lại cùng cấu hình.


## 6. Quyết định và ghi chú AI

*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.

a, Quyết định: Giữ Hold vì còn 38/205 ảnh cảnh báo chưa duyệt (18,54%). Để đạt Release, cần duyệt và xử lý thêm, chạy lại QC để không còn lỗi bắt buộc và tỷ lệ cảnh báo chưa duyệt dưới 10%.
Ghi chú AI:
- Prompt chính: Hỗ trợ hoàn thiện 4 module theo hướng dẫn và test có sẵn của đề.
- Cách kiểm: Tôi trực tiếp chạy 79 test đều pass, calibration, pipeline và train raw/clean trên GPU máy cá nhân. Tôi cũng kiểm tra khi không có người duyệt, xác nhận pipeline chặn xuất dữ liệu còn thiếu nhãn.
- AI sai: Code ban đầu chưa xử lý ID lớp inf, gây OverflowError; AI phát hiện khi kiểm tra bổ sung và sửa cách bắt lỗi.
CVAT: Chưa thực hiện phần thưởng tùy chọn.