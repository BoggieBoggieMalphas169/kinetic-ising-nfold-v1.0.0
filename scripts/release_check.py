from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
SNAPSHOT = "snap_0cc46433731097c4"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def structural_checks() -> list[str]:
    errors: list[str] = []
    required = [
        "README.md", "README_ES.md", "VERSION", "LICENSE", "CITATION.cff",
        "CHANGELOG.md", "RELEASE_NOTES.md", "CONTRIBUTING.md",
        "requirements.txt", "requirements-analysis.txt", "pytest.ini",
        "CMakeLists.txt", "Makefile", ".github/workflows/full-ci.yml",
        "simulator/CMakeLists.txt", "simulator/Makefile", "simulator/README.md",
        "simulator/src/ising.c", "simulator/src/standard_mc.c", "simulator/src/nfold.c",
        "simulator/include/ising.h", "simulator/include/standard_mc.h", "simulator/include/nfold.h",
        "simulator/tests/test_physics.c", "simulator/tests/test_nfold.c",
        "simulator/scripts/check_csv_invariants.py",
        "simulator/results/production_report_L32/validation_summary.csv",
        "simulator/results/scalability_L/scalability_summary.csv",
        "simulator/results/temperature_sweep/temperature_sweep_summary.csv",
        "docs/reproducibility.md", "docs/integration_with_simulator.md",
        "results/metadata/final_artifacts_8D_manifest.csv",
        f"results/snapshots/{SNAPSHOT}/manifest.json",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")

    if (ROOT / "VERSION").is_file() and (ROOT / "VERSION").read_text().strip() != VERSION:
        errors.append("VERSION file does not match release checker")

    if list(ROOT.glob("README_PROMPT*.md")):
        errors.append("development-history README_PROMPT files found in repository root")

    figs = ROOT / "figures/final"
    supp = ROOT / "figures/supplementary"
    tables = ROOT / "results/final_tables"
    if len(list(figs.glob("*.png"))) != 6 or len(list(figs.glob("*.pdf"))) != 6:
        errors.append("expected 6 final PNG and 6 final PDF figures")
    if len(list(supp.glob("*.png"))) != 2 or len(list(supp.glob("*.pdf"))) != 2:
        errors.append("expected 2 supplementary PNG and 2 supplementary PDF figures")
    if len(list(tables.glob("*.csv"))) != 7 or len(list(tables.glob("*.md"))) != 7 or len(list(tables.glob("*.tex"))) != 7:
        errors.append("expected 7 final tables in each of CSV/Markdown/LaTeX")

    af = ROOT / "results/metadata/final_artifacts_8D_manifest.csv"
    if af.is_file():
        with af.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 37:
            errors.append(f"8D manifest should contain 37 artifacts, found {len(rows)}")
        if any(r.get("analysis_snapshot") != SNAPSHOT for r in rows):
            errors.append("8D manifest contains a different analysis snapshot")

    meta = ROOT / "release/release_metadata.json"
    if meta.is_file():
        obj = json.loads(meta.read_text(encoding="utf-8"))
        if obj.get("version") != VERSION:
            errors.append("release metadata version mismatch")
        if obj.get("analysis_snapshot") != SNAPSHOT:
            errors.append("release metadata snapshot mismatch")
        if obj.get("simulator_core_included") is not True:
            errors.append("release metadata must state simulator_core_included=true")

    return errors


def verify_frozen() -> list[str]:
    errors: list[str] = []
    manifest = ROOT / "release/release_manifest.csv"
    if not manifest.is_file():
        return ["release/release_manifest.csv is missing"]
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        p = ROOT / r["path"]
        if not p.is_file():
            errors.append(f"manifest file missing: {r['path']}")
            continue
        if str(p.stat().st_size) != r["size_bytes"]:
            errors.append(f"size mismatch: {r['path']}")
        if sha256(p) != r["sha256"]:
            errors.append(f"sha256 mismatch: {r['path']}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the complete GitHub release")
    ap.add_argument("--structural", action="store_true")
    ap.add_argument("--verify-frozen", action="store_true")
    args = ap.parse_args()
    if not args.structural and not args.verify_frozen:
        args.structural = args.verify_frozen = True
    errors: list[str] = []
    if args.structural: errors += structural_checks()
    if args.verify_frozen: errors += verify_frozen()
    if errors:
        print("RELEASE CHECK: FAIL")
        for e in errors: print(f"- {e}")
        return 1
    print("RELEASE CHECK: PASS")
    print(f"version={VERSION}")
    print(f"analysis_snapshot={SNAPSHOT}")
    print("simulator_core_included=true")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
