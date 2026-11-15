"""CLI for Prompt 8B.2 cross-campaign reproducibility analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .campaign_consistency import analyze_campaign_consistency
from .physical_equivalence import analyze_physical_equivalence
from .quality_gate import verify_snapshot
from .load_results import DataContractError


def _snapshot_master(snapshot: Path) -> tuple[pd.DataFrame, str]:
    ok, report = verify_snapshot(snapshot)
    if not ok:
        bad = report.loc[~report["match"].astype(bool), "path"].astype(str).tolist()
        raise DataContractError("8B.2 snapshot verification failed: " + ", ".join(bad))
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    snapshot_id = str(manifest["snapshot_id"])
    master_path = snapshot / "data/results/processed/master_comparisons.csv"
    if not master_path.exists():
        raise DataContractError(f"Snapshot lacks master_comparisons.csv: {master_path}")
    return pd.read_csv(master_path), snapshot_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt 8B.2 cross-campaign reproducibility")
    parser.add_argument("--snapshot", type=Path, required=True,
                        help="Verified 8A.21 snapshot directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("results/processed"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    args = parser.parse_args()

    master, snapshot_id = _snapshot_master(args.snapshot)
    eq = analyze_physical_equivalence(master, snapshot_id=snapshot_id)
    result = analyze_campaign_consistency(eq.records)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metadata_dir.mkdir(parents=True, exist_ok=True)

    repeated_path = args.output_dir / "campaign_repeated_records_8B2.csv"
    summary_path = args.output_dir / "campaign_consistency_summary_8B2.csv"
    pairwise_path = args.output_dir / "campaign_pairwise_consistency_8B2.csv"
    diag_path = args.metadata_dir / "campaign_consistency_diagnostics_8B2.csv"

    result.repeated_records.to_csv(repeated_path, index=False)
    result.point_summary.to_csv(summary_path, index=False)
    result.pairwise.to_csv(pairwise_path, index=False)
    result.diagnostics.to_csv(diag_path, index=False)

    print(f"8B.2 snapshot: {snapshot_id}")
    print(f"Wrote {repeated_path} ({len(result.repeated_records)} rows)")
    print(f"Wrote {summary_path} ({len(result.point_summary)} physical points)")
    print(f"Wrote {pairwise_path} ({len(result.pairwise)} campaign pairs)")
    print(f"Wrote {diag_path}")
    print(result.diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
