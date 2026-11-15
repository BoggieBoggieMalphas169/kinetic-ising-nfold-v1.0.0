from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/release_manifest.csv"
SUMS = ROOT / "release/SHA256SUMS"
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "build-sanitize"}
EXCLUDED = {
    MANIFEST.relative_to(ROOT).as_posix(),
    SUMS.relative_to(ROOT).as_posix(),
}
EXCLUDED_SUFFIXES = {".pyc", ".tmp", ".bak"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def include(path: Path) -> bool:
    if not path.is_file():
        return False
    rel = path.relative_to(ROOT)
    if rel.as_posix() in EXCLUDED:
        return False
    if any(part in EXCLUDED_PARTS or part.startswith("build-") for part in rel.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def freeze() -> None:
    files = sorted(p for p in ROOT.rglob("*") if include(p))
    rows = []
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        rows.append({"path": rel, "size_bytes": p.stat().st_size, "sha256": sha256(p)})
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "size_bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)
    SUMS.write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in rows), encoding="utf-8")
    print(f"Frozen {len(rows)} files")
    print(MANIFEST)
    print(SUMS)


if __name__ == "__main__":
    freeze()
