"""Run the unchanged course checker with two explicit Windows compatibility fixes.

Protected paths use POSIX separators. Training records the exact manifest bytes,
so compare its digest without normalizing CRLF. All other checks stay intact.
"""
from pathlib import Path


if __name__ == "__main__":
    original = Path(__file__).with_name("check_submission.py")
    source = original.read_text(encoding="utf-8")
    fixes = {
        "str(p.relative_to(ROOT)) not in prot":
            "p.relative_to(ROOT).as_posix() not in prot",
        'r.get("manifest_sha1") != sha1(mf)':
            'r.get("manifest_sha1") != hashlib.sha1(mf.read_bytes()).hexdigest()',
    }
    for old, new in fixes.items():
        if source.count(old) != 1:
            raise RuntimeError(f"Course checker changed; review compatibility fix: {old}")
        source = source.replace(old, new)
    print("Windows compatibility: POSIX protected paths; exact manifest-byte hash.")
    exec(compile(source, str(original), "exec"),
         {"__name__": "__main__", "__file__": str(original)})
