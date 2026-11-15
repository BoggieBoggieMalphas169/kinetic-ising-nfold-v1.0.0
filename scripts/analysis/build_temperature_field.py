"""CLI for Prompt 8B.4 temperature/field robustness analysis."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .load_results import DataContractError
from .physical_equivalence import analyze_physical_equivalence
from .quality_gate import verify_snapshot
from .temperature_field_robustness import analyze_temperature_field

def _snapshot_master(snapshot: Path):
    ok, report = verify_snapshot(snapshot)
    if not ok:
        bad = report.loc[~report["match"].astype(bool), "path"].astype(str).tolist()
        raise DataContractError("8B.4 snapshot verification failed: " + ", ".join(bad))
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    snapshot_id = str(manifest["snapshot_id"])
    master = snapshot / "data/results/processed/master_comparisons.csv"
    if not master.exists():
        raise DataContractError(f"Snapshot lacks master_comparisons.csv: {master}")
    return pd.read_csv(master), snapshot_id

def main():
    p = argparse.ArgumentParser(description="Prompt 8B.4 temperature and field robustness")
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("results/processed"))
    p.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    a = p.parse_args()
    master, sid = _snapshot_master(a.snapshot)
    eq = analyze_physical_equivalence(master, snapshot_id=sid)
    out = analyze_temperature_field(eq.records)
    a.output_dir.mkdir(parents=True, exist_ok=True); a.metadata_dir.mkdir(parents=True, exist_ok=True)
    rp=a.output_dir/"temperature_field_records_8B4.csv"
    sp=a.output_dir/"temperature_field_summary_8B4.csv"
    dp=a.metadata_dir/"temperature_field_diagnostics_8B4.csv"
    out.records.to_csv(rp,index=False); out.summary.to_csv(sp,index=False); out.diagnostics.to_csv(dp,index=False)
    print(f"8B.4 snapshot: {sid}")
    print(f"Wrote {rp} ({len(out.records)} rows)")
    print(f"Wrote {sp} ({len(out.summary)} series)")
    print(f"Wrote {dp}")
    print(out.diagnostics.to_string(index=False))
if __name__ == "__main__": main()
