"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401


def run(ds, cfg):
    issues = []
    rules = cfg["label_format"]
    for path in ds.label_files():
        stem, seen = path.stem, []
        size = ds.image_size(stem)
        for line, text in ds.read_label_lines(stem) or []:
            def add(code, severity, message, **extra):
                issues.append(Issue("label_format", severity, code, stem, message, line, extra))
            try:
                c, x, y, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError) as exc:
                add("BAD_FORMAT", ERROR, str(exc))
                continue
            if not 0 <= c < len(ds.classes):
                add("BAD_CLASS_ID", ERROR, f"id lớp không hợp lệ: {c}")
                continue
            if w <= 0 or h <= 0:
                add("BOX_ZERO", ERROR, "box có cạnh không dương")
                continue
            box = (x, y, w, h)
            overflow = max(0, w / 2 - x, h / 2 - y, x + w / 2 - 1, y + h / 2 - 1)
            if overflow > rules["overflow_tol"]:
                add("BOX_OUT_OF_IMAGE", ERROR, "box vượt biên ảnh", overflow=overflow)
            if any(c == prev_c and iou_xywh(box, prev) > rules["dup_box_iou"] for prev_c, prev in seen):
                add("DUP_BOX", ERROR, "box trùng với dòng trước cùng lớp")
            seen.append((c, box))
            if size and min(w * size[0], h * size[1]) < rules["min_box_px"]:
                add("BOX_TINY", WARN, "cạnh ngắn dưới ngưỡng pixel")
            if w * h > rules["max_box_frac"]:
                add("BOX_HUGE", WARN, "box chiếm quá nhiều diện tích ảnh")
    return issues
