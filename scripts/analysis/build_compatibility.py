"""CLI for Prompt 8A.19: import Prompt 6 aggregate summaries into the v8A19 contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from .prompt6_compat import load_prompt6_summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy",
        type=Path,
        default=Path("results/legacy/prompt6"),
        help="Directory containing Prompt 6 summary CSVs",
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=Path("results/metadata/prompt6_context.json"),
        help="Explicit sidecar metadata for legacy files that omitted L/T/J",
    )
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

    context = args.context if args.context.exists() else None
    loaded = load_prompt6_summaries(args.legacy, context_path=context)

    comparison_path = args.processed / "prompt6_comparison_summary.csv"
    report_path = args.metadata / "prompt6_compatibility_report.csv"
    loaded.comparisons.to_csv(comparison_path, index=False)
    loaded.report.to_csv(report_path, index=False)

    complete = int((loaded.report["contract_status"] == "complete").sum())
    partial = int((loaded.report["contract_status"] == "partial").sum())
    print(f"Imported {len(loaded.comparisons)} comparison rows from {len(loaded.report)} Prompt 6 summaries")
    print(f"Contracts: {complete} complete, {partial} partial")
    print(f"Wrote {comparison_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
