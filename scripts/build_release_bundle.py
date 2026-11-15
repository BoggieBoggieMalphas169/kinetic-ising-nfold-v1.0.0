from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PREFIX = f"kinetic-ising-nfold-v{VERSION}"
DIST = ROOT / "dist"
ZIP_PATH = DIST / f"{PREFIX}.zip"
HASH_PATH = DIST / f"{PREFIX}.zip.sha256"
FIXED_DT = (2026, 9, 30, 0, 0, 0)

EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "build-sanitize"}
EXCLUDED_SUFFIXES = {".pyc", ".tmp", ".bak"}


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS or part.startswith("build-") for part in rel.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def build() -> tuple[Path, Path]:
    DIST.mkdir(exist_ok=True)
    files = sorted(p for p in ROOT.rglob("*") if include(p))
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{PREFIX}/{rel}", date_time=FIXED_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
    HASH_PATH.write_text(f"{digest}  {ZIP_PATH.name}\n", encoding="utf-8")
    print(ZIP_PATH)
    print(HASH_PATH)
    return ZIP_PATH, HASH_PATH


if __name__ == "__main__":
    build()
