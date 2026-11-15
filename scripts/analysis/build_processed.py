"""CLI for Prompt 8A.18: raw CSV -> canonical run table -> aggregate summary."""

from __future__ import annotations

import argparse
from pathlib import Path

from .aggregate_runs import aggregate_runs
from .load_results import load_raw_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("results/raw"), help="Raw-results root")
    parser.add_argument(
        "--processed", type=Path, default=Path("results/processed"), help="Output directory"
    )
    parser.add_argument(
        "--metadata", type=Path, default=Path("results/metadata"), help="Metadata output directory"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.processed.mkdir(parents=True, exist_ok=True)
    args.metadata.mkdir(parents=True, exist_ok=True)

    loaded = load_raw_results(args.raw)
    summary = aggregate_runs(loaded.runs)

    runs_path = args.processed / "run_level.csv"
    summary_path = args.processed / "summary.csv"
    manifest_path = args.metadata / "raw_manifest.csv"

    loaded.runs.to_csv(runs_path, index=False)
    summary.to_csv(summary_path, index=False)
    loaded.manifest.to_csv(manifest_path, index=False)

    print(f"Loaded {len(loaded.runs)} runs from {len(loaded.manifest)} raw CSV files")
    print(f"Wrote {runs_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
