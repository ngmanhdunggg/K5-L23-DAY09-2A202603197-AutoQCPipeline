"""Package existing pipeline output for manual CVAT bonus work; do not change data."""
import csv
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    export = ROOT / "submission/export/clean_v1"
    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    images = {Path(name).stem: name for name in manifest["images"]}
    reports = ROOT / "submission/reports"
    with (reports / "05_review_queue.csv").open(encoding="utf-8", newline="") as f:
        selected = [r["image"] for r in list(csv.DictReader(f))[:20]]
    with (reports / "07_error_list_v3.csv").open(encoding="utf-8", newline="") as f:
        tiny = {r["image"] for r in csv.DictReader(f) if r["code"] == "BOX_TINY"}
    selected = list(dict.fromkeys(selected + sorted(tiny)))
    selected = [stem for stem in selected if stem in images]
    out = ROOT / "work/cvat_bonus"
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    with ZipFile(out / "images.zip", "w", ZIP_DEFLATED) as iz, ZipFile(out / "labels_yolo11.zip", "w", ZIP_DEFLATED) as lz:
        classes = manifest["classes"]
        lz.writestr("obj.names", "\n".join(classes) + "\n")
        lz.writestr("obj.data", f"classes = {len(classes)}\ntrain = train.txt\nnames = obj.names\nbackup = backup/\n")
        lz.writestr("train.txt", "".join(f"obj_train_data/{images[s]}\n" for s in selected))
        for stem in selected:
            name = images[stem]
            iz.write(ROOT / "data/raw/images" / name, name)
            lz.write(export / "labels" / f"{stem}.txt", f"obj_train_data/{stem}.txt")
            summary.append({"image": name, "pipeline_BOX_TINY": stem in tiny})
    (out / "selected_images.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(selected)} images; {sum(s['pipeline_BOX_TINY'] for s in summary)} have BOX_TINY warnings.")
    print(out / "images.zip")
    print(out / "labels_yolo11.zip")
    print("CVAT labels schema: cvat/labels.json")


if __name__ == "__main__":
    main()
