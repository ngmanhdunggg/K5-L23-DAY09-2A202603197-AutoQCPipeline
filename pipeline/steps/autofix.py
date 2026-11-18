"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


def fix(ds, issues, cfg):
    changes = []
    errors = [i for i in issues if i.severity == ERROR]
    def record(image, line, action, before, after):
        changes.append(dict(image=image, line=line, action=action, before=before, after=after))

    # Image removal wins over all line edits on the same image.
    removed = set()
    for issue in errors:
        if issue.code.startswith("DUP_IMAGE_") or issue.code in {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}:
            path = ds.image_path(issue.image)
            if path and issue.image not in removed:
                record(issue.image, None, "remove_image", path.name, "")
                path.unlink()
                ds.label_path(issue.image).unlink(missing_ok=True)
                removed.add(issue.image)
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) if ds.yaml_path.exists() else {}
        data = data or {}
        if ds.yaml_names() != dict(enumerate(cfg["classes"])):
            before = data.get("names", {})
            data["names"] = list(cfg["classes"])
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            record("data.yaml", None, "rename_classes", str(before), str(data["names"]))
    grouped = defaultdict(lambda: defaultdict(set))
    missing = set()
    for issue in errors:
        if issue.image in removed:
            continue
        if issue.code == "MISSING_LABEL_FILE" and issue.image not in missing and not ds.label_path(issue.image).exists():
            record(issue.image, None, "needs_label", "(không có file)", "chuyển người gán")
            missing.add(issue.image)
        if issue.line is not None:
            grouped[issue.image][issue.line].add(issue.code)
    drops = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
    for stem in sorted(grouped):
        path = ds.label_path(stem)
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8").splitlines()
        output, changed = [], False
        for line, text in enumerate(original, 1):
            codes = grouped[stem].get(line, set())
            action, after = None, text
            if codes & drops:
                action, after = "drop_line", ""
            elif "BOX_OUT_OF_IMAGE" in codes:
                try:
                    c, x, y, w, h = parse_yolo_line(text)
                except (ValueError, OverflowError):
                    action, after = "drop_line", ""
                else:
                    left, top = max(0.0, x - w / 2), max(0.0, y - h / 2)
                    right, bottom = min(1.0, x + w / 2), min(1.0, y + h / 2)
                    if right <= left or bottom <= top:
                        action, after = "drop_line", ""
                    elif (left, top, right, bottom) != (x - w / 2, y - h / 2, x + w / 2, y + h / 2):
                        action = "clip_box"
                        after = f"{c} {(left + right) / 2:.10f} {(top + bottom) / 2:.10f} {right - left:.10f} {bottom - top:.10f}"
            if action:
                changed = True
                record(stem, line, action, text, after)
            if action != "drop_line":
                output.append(after)
        if changed:
            path.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")
    return changes
