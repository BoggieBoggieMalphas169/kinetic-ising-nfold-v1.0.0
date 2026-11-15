"""CLI for Prompt 8C performance analysis."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .load_results import DataContractError
from .performance_analysis import analyze_performance


def _snapshot_id(snapshot_dir: Path) -> str:
    manifest = snapshot_dir / "manifest.json"
    if not manifest.exists():
        raise DataContractError(f"8C snapshot manifest does not exist: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    sid = data.get("snapshot_id") or snapshot_dir.name
    if sid != snapshot_dir.name:
        raise DataContractError("8C snapshot directory and manifest snapshot_id disagree")
    return sid


def main():
    p=argparse.ArgumentParser(description="Prompt 8C computational performance analysis")
    p.add_argument("--master", type=Path, default=Path("results/processed/master_comparisons.csv"))
    p.add_argument("--snapshot", type=Path, default=Path("results/snapshots/snap_0cc46433731097c4"))
    p.add_argument("--processed-dir", type=Path, default=Path("results/processed"))
    p.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    a=p.parse_args()
    if not a.master.exists():
        raise DataContractError(f"8C master dataset does not exist: {a.master}")
    sid=_snapshot_id(a.snapshot)
    out=analyze_performance(pd.read_csv(a.master), sid)
    a.processed_dir.mkdir(parents=True,exist_ok=True); a.metadata_dir.mkdir(parents=True,exist_ok=True)
    paths={
        "records":a.processed_dir/"performance_records_8C.csv",
        "temperature":a.processed_dir/"performance_temperature_8C.csv",
        "size":a.processed_dir/"performance_size_8C.csv",
        "synthesis":a.processed_dir/"performance_synthesis_8C.csv",
        "diagnostics":a.metadata_dir/"performance_diagnostics_8C.csv",
    }
    out.records.to_csv(paths["records"],index=False)
    out.temperature.to_csv(paths["temperature"],index=False)
    out.size.to_csv(paths["size"],index=False)
    out.synthesis.to_csv(paths["synthesis"],index=False)
    out.diagnostics.to_csv(paths["diagnostics"],index=False)
    s=out.synthesis.iloc[0]
    print(f"8C snapshot: {sid}")
    print(f"Performance conclusion: {s['overall_performance_conclusion']}")
    print(f"Maximum measured speed-up: {s['max_speedup']:.6g}x")
    print(f"Maximum measured Standard advantage: {s['max_standard_advantage']:.6g}x")
    for k,v in paths.items(): print(f"Wrote {v}")

if __name__=="__main__": main()
