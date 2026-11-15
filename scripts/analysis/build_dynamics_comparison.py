"""CLI for Prompt 8B.5 dynamics-separated analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .dynamics_comparison import analyze_dynamics
from .load_results import DataContractError
from .physical_equivalence import analyze_physical_equivalence
from .quality_gate import verify_snapshot


def _snapshot_master(snapshot: Path):
    ok, report = verify_snapshot(snapshot)
    if not ok:
        bad = report.loc[~report["match"].astype(bool), "path"].astype(str).tolist()
        raise DataContractError("8B.5 snapshot verification failed: " + ", ".join(bad))
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    snapshot_id = str(manifest["snapshot_id"])
    master = snapshot / "data/results/processed/master_comparisons.csv"
    if not master.exists():
        raise DataContractError(f"Snapshot lacks master_comparisons.csv: {master}")
    return pd.read_csv(master), snapshot_id


def main():
    p = argparse.ArgumentParser(description="Prompt 8B.5 Glauber/Metropolis separated analysis")
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("results/processed"))
    p.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    a = p.parse_args()

    master, sid = _snapshot_master(a.snapshot)
    eq = analyze_physical_equivalence(master, snapshot_id=sid)
    out = analyze_dynamics(eq.records)

    a.output_dir.mkdir(parents=True, exist_ok=True)
    a.metadata_dir.mkdir(parents=True, exist_ok=True)
    rp = a.output_dir / "dynamics_records_8B5.csv"
    sp = a.output_dir / "dynamics_summary_8B5.csv"
    pp = a.output_dir / "dynamics_matched_pairs_8B5.csv"
    dp = a.metadata_dir / "dynamics_diagnostics_8B5.csv"
    out.records.to_csv(rp, index=False)
    out.dynamics_summary.to_csv(sp, index=False)
    out.matched_pairs.to_csv(pp, index=False)
    out.diagnostics.to_csv(dp, index=False)

    print(f"8B.5 snapshot: {sid}")
    print(f"Wrote {rp} ({len(out.records)} rows)")
    print(f"Wrote {sp} ({len(out.dynamics_summary)} dynamics)")
    print(f"Wrote {pp} ({len(out.matched_pairs)} matched points)")
    print(f"Wrote {dp}")
    print(out.dynamics_summary.to_string(index=False))


if __name__ == "__main__":
    main()
