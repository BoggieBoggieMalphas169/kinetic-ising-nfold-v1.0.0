"""CLI for Prompt 8B.6 final physical synthesis."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .load_results import DataContractError
from .physical_synthesis import synthesize_physical_comparison


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DataContractError(f"8B.6 required input does not exist: {path}")
    return pd.read_csv(path)


def main():
    p = argparse.ArgumentParser(description="Prompt 8B.6 final physical synthesis")
    p.add_argument("--processed-dir", type=Path, default=Path("results/processed"))
    p.add_argument("--metadata-dir", type=Path, default=Path("results/metadata"))
    a = p.parse_args()

    d = a.processed_dir
    out = synthesize_physical_comparison(
        _read(d / "physical_equivalence_8B1.csv"),
        _read(d / "campaign_consistency_summary_8B2.csv"),
        _read(d / "size_scaling_summary_8B3.csv"),
        _read(d / "temperature_field_summary_8B4.csv"),
        _read(d / "dynamics_summary_8B5.csv"),
        _read(d / "dynamics_matched_pairs_8B5.csv"),
    )

    d.mkdir(parents=True, exist_ok=True)
    a.metadata_dir.mkdir(parents=True, exist_ok=True)
    sp = d / "physical_synthesis_8B6.csv"
    lp = a.metadata_dir / "physical_limitations_8B6.csv"
    dp = a.metadata_dir / "physical_synthesis_diagnostics_8B6.csv"
    out.synthesis.to_csv(sp, index=False)
    out.limitations.to_csv(lp, index=False)
    out.diagnostics.to_csv(dp, index=False)

    row = out.synthesis.iloc[0]
    print(f"8B.6 snapshot: {row['analysis_snapshot']}")
    print(f"Physical conclusion: {row['overall_physical_conclusion']}")
    print(f"PASS / INCONCLUSIVE / FAIL = {row['pass_count']} / {row['inconclusive_count']} / {row['fail_count']}")
    print(f"Wrote {sp}")
    print(f"Wrote {lp}")
    print(f"Wrote {dp}")


if __name__ == "__main__":
    main()
