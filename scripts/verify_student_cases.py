"""Extra synthetic checks; never changes course data or the provided tests."""
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.common import Dataset, Issue, ERROR, load_config
from pipeline.checks import label_format, second_opinion
from pipeline.steps import autofix


def main():
    cfg = load_config()
    results = {}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "images").mkdir()
        (root / "labels").mkdir()
        Image.new("RGB", (640, 480)).save(root / "images/a.jpg")
        ds = Dataset(root, cfg["classes"])
        label = ds.label_path("a")
        label.write_text("0 .5 .5 .3 .4\n\n0 .95 .5 .2 .2\n", encoding="utf-8")
        changes = autofix.fix(ds, [
            Issue("synthetic", ERROR, "BOX_OUT_OF_IMAGE", "a", "", 3),
            Issue("synthetic", ERROR, "DUP_BOX", "a", "", 3),
        ], cfg)
        assert [(c["line"], c["action"]) for c in changes] == [(3, "drop_line")]
        assert label.read_text().splitlines() == ["0 .5 .5 .3 .4", ""]
        results["two_errors_and_blank_line"] = "pass"

        label.write_text("0 .5 .5 .3 .4\n\ninf .5 .5 .2 .2\n", encoding="utf-8")
        issues = label_format.run(ds, cfg)
        assert any(i.code == "BAD_FORMAT" and i.line == 3 for i in issues)
        predictions = {"a": [[0, .99, .5, .5, .3, .4],
                              [1, .99, .15, .3, .12, .3],
                              [2, .99, .85, .7, .12, .3]]}
        warnings = second_opinion.run(ds, cfg, predictions)
        assert [i.code for i in warnings] == ["POSSIBLE_MISSING", "POSSIBLE_MISSING"]
        results["nonfinite_class_and_multiple_predictions"] = "pass"

        label.write_text("0 .95 .5 .2 .2\n", encoding="utf-8")
        autofix.fix(ds, label_format.run(ds, cfg), cfg)
        before = label.read_bytes()
        assert autofix.fix(ds, label_format.run(ds, cfg), cfg) == []
        assert label.read_bytes() == before
        results["clip_then_repeat_is_idempotent"] = "pass"
    out = ROOT / "submission/evidence/student_cases.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results))


if __name__ == "__main__":
    main()
