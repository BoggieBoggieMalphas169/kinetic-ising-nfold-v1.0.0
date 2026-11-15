"""CLI for Prompt 8A.20: build the master experiment catalog and coverage reports."""

from __future__ import annotations

import argparse
from pathlib import Path

from .master_catalog import build_master_catalog, load_comparison_tables, load_experiment_design


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparisons",
        type=Path,
        nargs="+",
        default=[Path("results/processed/prompt6_comparison_summary.csv")],
        help="One or more comparison-summary CSVs using the 8A.19 contract",
    )
    parser.add_argument(
        "--design",
        type=Path,
        default=Path("results/metadata/experiment_design.json"),
        help="Versioned expected experiment design",
    )
    parser.add_argument(
        "--processed",
        type=Path,
        default=Path("results/processed"),
        help="Processed-data output directory",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("results/metadata"),
        help="Metadata/diagnostic output directory",
    )
    return parser.parse_args()


def _write(frame, path: Path) -> None:
    frame.to_csv(path, index=False)
    print(f"Wrote {path} ({len(frame)} rows)")


def main() -> None:
    args = parse_args()
    args.processed.mkdir(parents=True, exist_ok=True)
    args.metadata.mkdir(parents=True, exist_ok=True)

    comparisons = load_comparison_tables(args.comparisons)
    design = load_experiment_design(args.design if args.design.exists() else None)
    built = build_master_catalog(comparisons, design)

    _write(built.master_comparisons, args.processed / "master_comparisons.csv")
    _write(built.experiment_catalog, args.processed / "master_experiment_catalog.csv")
    _write(built.coverage_detail, args.metadata / "experiment_coverage.csv")
    _write(built.coverage_summary, args.metadata / "experiment_coverage_summary.csv")
    _write(built.missing_experiments, args.metadata / "missing_experiments.csv")
    _write(built.duplicate_experiments, args.metadata / "duplicate_experiments.csv")
    _write(built.unexpected_experiments, args.metadata / "unexpected_experiments.csv")

    partial = int((built.master_comparisons["catalog_status"] == "partial_context").sum()) if not built.master_comparisons.empty else 0
    duplicates = int(built.master_comparisons["duplicate_within_study"].fillna(False).sum()) if not built.master_comparisons.empty else 0
    overlaps = int(built.experiment_catalog["cross_study_overlap"].fillna(False).sum()) if not built.experiment_catalog.empty else 0
    print(
        f"Catalog: {len(built.master_comparisons)} comparison records, "
        f"{len(built.experiment_catalog)} unique physical points, "
        f"{overlaps} cross-study overlaps, {duplicates} duplicate records, "
        f"{partial} partial-context records"
    )


if __name__ == "__main__":
    main()
