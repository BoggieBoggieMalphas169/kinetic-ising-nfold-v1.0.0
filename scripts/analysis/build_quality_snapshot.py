"""CLI for Prompt 8A.21 quality gate and reproducible snapshot creation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .load_results import DataContractError
from .quality_gate import create_snapshot, run_quality_gate, verify_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 8A.21 quality gate and freeze READY_FOR_8B data")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument(
        "--snapshots-dir",
        type=Path,
        default=Path("results/snapshots"),
        help="Snapshot directory (relative to root unless absolute)",
    )
    parser.add_argument(
        "--allow-unexpected",
        action="store_true",
        help="Do not block the gate solely because the catalog contains undeclared experiment points",
    )
    parser.add_argument(
        "--gate-only",
        action="store_true",
        help="Run the quality gate and write its report without creating a snapshot",
    )
    parser.add_argument(
        "--verify",
        type=Path,
        default=None,
        metavar="SNAPSHOT_DIR",
        help="Verify a previously created snapshot instead of building one",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verify is not None:
        ok, report = verify_snapshot(args.verify)
        print(report.to_string(index=False))
        print("SNAPSHOT VERIFIED" if ok else "SNAPSHOT VERIFICATION FAILED")
        raise SystemExit(0 if ok else 2)

    root = args.root.resolve()
    metadata = root / "results" / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)

    gate = run_quality_gate(root, allow_unexpected=args.allow_unexpected)
    report_path = metadata / "quality_gate_8A21.csv"
    gate.checks.to_csv(report_path, index=False)
    status_path = metadata / "scientific_status_8A21.csv"
    gate.scientific_status.to_csv(status_path, index=False)
    print(gate.checks.to_string(index=False))
    print(f"Wrote {report_path}")
    print(f"Wrote {status_path}")

    if not gate.ready_for_8b:
        print("QUALITY GATE: NOT READY FOR 8B")
        raise SystemExit(2)

    print("QUALITY GATE: READY FOR 8B")
    if args.gate_only:
        return

    try:
        snapshot = create_snapshot(
            root,
            snapshots_dir=args.snapshots_dir,
            allow_unexpected=args.allow_unexpected,
        )
    except DataContractError as exc:
        print(str(exc))
        raise SystemExit(2) from exc
    print(f"Snapshot: {snapshot.snapshot_id}")
    print(f"Path: {snapshot.path}")


if __name__ == "__main__":
    main()
