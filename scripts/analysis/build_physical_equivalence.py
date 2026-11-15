"""CLI for Prompt 8B.1 physical Standard-vs-n-fold equivalence analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .physical_equivalence import analyze_physical_equivalence
from .quality_gate import verify_snapshot
from .load_results import DataContractError


def _snapshot_master(snapshot: Path) -> tuple[pd.DataFrame, str]:
    ok, report = verify_snapshot(snapshot)
    if not ok:
        bad = report.loc[~report["match"].astype(bool), "path"].astype(str).tolist()
        raise DataContractError("8B.1 snapshot verification failed: " + ", ".join(bad))
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot_id = str(manifest["snapshot_id"])
    master_path = snapshot / "data/results/processed/master_comparisons.csv"
    if not master_path.exists():
        raise DataContractError(f"Snapshot lacks master_comparisons.csv: {master_path}")
    return pd.read_csv(master_path), snapshot_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt 8B.1 physical equivalence analysis")
    parser.add_argument("--snapshot", type=Path, required=True,
                        help="Verified 8A.21 snapshot directory; this is the recommended/strict input.")
    parser.add_argument("--output-dir", type=Path, default=Path("results/processed"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    args = parser.parse_args()

    master, snapshot_id = _snapshot_master(args.snapshot)
    result = analyze_physical_equivalence(master, snapshot_id=snapshot_id)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metadata_dir.mkdir(parents=True, exist_ok=True)
    records_path = args.output_dir / "physical_equivalence_8B1.csv"
    summary_path = args.output_dir / "physical_equivalence_summary_8B1.csv"
    diag_path = args.metadata_dir / "physical_equivalence_diagnostics_8B1.csv"
    result.records.to_csv(records_path, index=False)
    result.summary.to_csv(summary_path, index=False)
    result.diagnostics.to_csv(diag_path, index=False)

    print(f"8B.1 snapshot: {snapshot_id}")
    print(f"Wrote {records_path} ({len(result.records)} rows)")
    print(f"Wrote {summary_path} ({len(result.summary)} rows)")
    print(f"Wrote {diag_path}")
    print(result.diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
