"""Prompt 8A.21 structural quality gate and reproducible dataset snapshots.

The gate answers a narrow question: *is the dataset structurally safe to use in 8B?*
It deliberately does not decide whether Standard and n-fold are scientifically equivalent.
`PASS`, `INCONCLUSIVE`, and even a future scientifically meaningful `FAIL` remain analysis
results rather than data-integrity failures.

A successful gate can be frozen into an immutable-ish snapshot directory containing exact
copies of the canonical analysis tables plus SHA-256 checksums.  The snapshot identifier is
deterministic for identical input bytes and the gate schema version.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from .contracts import COMPARISON_SUMMARY
from .load_results import DataContractError
from .master_catalog import MASTER_SCHEMA_VERSION

QUALITY_GATE_SCHEMA_VERSION = "8A21.1"
SNAPSHOT_SCHEMA_VERSION = "8A21-snapshot-v1"

# Paths are relative to the repository root.  Optional files are included in a snapshot
# when present, but only the canonical 8A.20 outputs are required by the gate.
REQUIRED_INPUTS = (
    "results/processed/master_comparisons.csv",
    "results/processed/master_experiment_catalog.csv",
    "results/metadata/experiment_coverage_summary.csv",
    "results/metadata/missing_experiments.csv",
    "results/metadata/duplicate_experiments.csv",
    "results/metadata/unexpected_experiments.csv",
    "results/metadata/experiment_design.json",
)

OPTIONAL_INPUTS = (
    "results/processed/prompt6_comparison_summary.csv",
    "results/metadata/prompt6_compatibility_report.csv",
    "results/metadata/prompt6_context.json",
)


@dataclass(frozen=True)
class GateResult:
    ready_for_8b: bool
    checks: pd.DataFrame
    scientific_status: pd.DataFrame


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_id: str
    path: Path
    manifest: dict[str, object]
    gate: GateResult


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise DataContractError(f"8A.21 required file is missing: {label} ({path})")
    try:
        return pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas error details vary
        raise DataContractError(f"Cannot read {label}: {path}: {exc}") from exc


def _append_check(
    rows: list[dict[str, object]],
    check_id: str,
    passed: bool,
    observed: object,
    expected: object,
    message: str,
    severity: str = "BLOCKER",
) -> None:
    rows.append(
        {
            "gate_schema_version": QUALITY_GATE_SCHEMA_VERSION,
            "check_id": check_id,
            "severity": severity,
            "passed": bool(passed),
            "observed": observed,
            "expected": expected,
            "message": message,
        }
    )


def run_quality_gate(root: str | Path = ".", *, allow_unexpected: bool = False) -> GateResult:
    root = Path(root).resolve()
    rows: list[dict[str, object]] = []

    # Existence is reported explicitly instead of failing at the first missing file.
    missing_paths: list[str] = []
    for relative in REQUIRED_INPUTS:
        if not (root / relative).exists():
            missing_paths.append(relative)
    _append_check(
        rows,
        "required_files_present",
        not missing_paths,
        ";".join(missing_paths) if missing_paths else "all present",
        "all required 8A.20 files",
        "Canonical catalog/design files required before entering 8B.",
    )
    if missing_paths:
        checks = pd.DataFrame(rows)
        return GateResult(False, checks, pd.DataFrame(columns=["equivalence_status", "count"]))

    master = _read_csv(root / "results/processed/master_comparisons.csv", "master comparisons")
    catalog = _read_csv(root / "results/processed/master_experiment_catalog.csv", "experiment catalog")
    coverage = _read_csv(root / "results/metadata/experiment_coverage_summary.csv", "coverage summary")
    missing = _read_csv(root / "results/metadata/missing_experiments.csv", "missing experiments")
    duplicates = _read_csv(root / "results/metadata/duplicate_experiments.csv", "duplicate experiments")
    unexpected = _read_csv(root / "results/metadata/unexpected_experiments.csv", "unexpected experiments")

    # Schema and identity checks.
    schema_values = sorted(set(master.get("master_schema_version", pd.Series(dtype=str)).dropna().astype(str)))
    _append_check(rows, "master_schema", schema_values == [MASTER_SCHEMA_VERSION], schema_values, MASTER_SCHEMA_VERSION,
                  "All comparison records must use the current 8A.20 master schema.")

    levels = sorted(set(master.get("record_level", pd.Series(dtype=str)).dropna().astype(str)))
    _append_check(rows, "record_level", levels == [COMPARISON_SUMMARY], levels, COMPARISON_SUMMARY,
                  "8B consumes Standard-vs-n-fold comparison summaries, not raw runs.")

    comparison_ids = master.get("comparison_id", pd.Series(dtype="string"))
    id_ok = len(master) > 0 and comparison_ids.notna().all() and comparison_ids.is_unique
    _append_check(rows, "comparison_ids_unique", id_ok, int(comparison_ids.nunique(dropna=True)), len(master),
                  "Every observed comparison must have one unique deterministic comparison_id.")

    exp_ids = master.get("experiment_id", pd.Series(dtype="string"))
    exp_ok = len(master) > 0 and exp_ids.notna().all()
    _append_check(rows, "physical_ids_complete", exp_ok, int(exp_ids.notna().sum()), len(master),
                  "Every comparison entering 8B must have complete physical context and experiment_id.")

    analysis_ready = master.get("analysis_ready", pd.Series(False, index=master.index)).fillna(False).astype(bool)
    _append_check(rows, "all_records_analysis_ready", bool(len(master) and analysis_ready.all()),
                  int(analysis_ready.sum()), len(master),
                  "No partial-context or ambiguous within-study duplicate may enter 8B.")

    duplicate_flags = master.get("duplicate_within_study", pd.Series(False, index=master.index)).fillna(False).astype(bool)
    _append_check(rows, "no_within_study_duplicate_flags", not duplicate_flags.any(), int(duplicate_flags.sum()), 0,
                  "Cross-study overlaps are allowed; within-study duplicate comparisons are not.")

    contract = master.get("contract_status", pd.Series("", index=master.index)).astype(str).str.lower()
    incomplete_contracts = int((contract != "complete").sum())
    _append_check(rows, "contracts_complete", incomplete_contracts == 0, incomplete_contracts, 0,
                  "Historical inputs must be normalized with complete physical context.")

    # Catalog coherence.
    catalog_ids = catalog.get("experiment_id", pd.Series(dtype="string"))
    catalog_unique = len(catalog) > 0 and catalog_ids.notna().all() and catalog_ids.is_unique
    _append_check(rows, "catalog_ids_unique", catalog_unique, int(catalog_ids.nunique(dropna=True)), len(catalog),
                  "Master experiment catalog must contain one row per unique physical point.")

    master_unique_ids = set(exp_ids.dropna().astype(str))
    catalog_id_set = set(catalog_ids.dropna().astype(str))
    _append_check(rows, "catalog_matches_master", master_unique_ids == catalog_id_set,
                  len(master_unique_ids.symmetric_difference(catalog_id_set)), 0,
                  "The catalog must contain exactly the physical points referenced by master_comparisons.")

    # Coverage/design checks.
    full_coverage = (
        not coverage.empty
        and "coverage_fraction" in coverage
        and pd.to_numeric(coverage["coverage_fraction"], errors="coerce").notna().all()
        and (pd.to_numeric(coverage["coverage_fraction"], errors="coerce") == 1.0).all()
    )
    min_cov = float(pd.to_numeric(coverage.get("coverage_fraction", pd.Series(dtype=float)), errors="coerce").min()) if not coverage.empty else float("nan")
    _append_check(rows, "declared_design_full_coverage", bool(full_coverage), min_cov, 1.0,
                  "Every point declared by experiment_design.json must be represented exactly once per study.")

    _append_check(rows, "no_missing_experiments", missing.empty, len(missing), 0,
                  "Declared experiments may not be absent from the 8B input dataset.")
    _append_check(rows, "no_duplicate_experiments", duplicates.empty, len(duplicates), 0,
                  "No declared point may appear ambiguously more than once inside one study.")
    _append_check(rows, "unexpected_experiments", allow_unexpected or unexpected.empty, len(unexpected),
                  "0 (unless --allow-unexpected)",
                  "Unexpected points are retained by 8A.20 but require explicit opt-in before 8B.")

    # Informational checks: these never block the gate.
    overlaps = master.get("cross_study_overlap", pd.Series(False, index=master.index)).fillna(False).astype(bool)
    _append_check(rows, "cross_study_overlaps_documented", True, int(overlaps.sum()), "allowed",
                  "Repeated physical points across campaigns are legitimate replication/overlap.", severity="INFO")

    statuses = master.get("equivalence_status", pd.Series("UNSPECIFIED", index=master.index)).fillna("UNSPECIFIED").astype(str)
    status_table = statuses.value_counts(dropna=False).rename_axis("equivalence_status").reset_index(name="count")
    status_text = ";".join(f"{r.equivalence_status}:{int(r.count)}" for r in status_table.itertuples())
    _append_check(rows, "scientific_equivalence_status", True, status_text, "informational only",
                  "PASS/INCONCLUSIVE/FAIL are scientific outcomes and do not determine data integrity.", severity="INFO")

    checks = pd.DataFrame(rows)
    blockers = checks[checks["severity"] == "BLOCKER"]
    ready = bool(not blockers.empty and blockers["passed"].astype(bool).all())
    return GateResult(ready, checks, status_table)


def _input_paths(root: Path) -> list[Path]:
    paths = [root / p for p in REQUIRED_INPUTS]
    paths.extend(root / p for p in OPTIONAL_INPUTS if (root / p).exists())
    return sorted(paths, key=lambda p: p.relative_to(root).as_posix())


def _hash_records(root: Path, paths: Iterable[Path]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in paths:
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def _deterministic_snapshot_id(file_records: list[dict[str, object]]) -> str:
    payload = {
        "gate_schema_version": QUALITY_GATE_SCHEMA_VERSION,
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "files": [{"path": x["path"], "sha256": x["sha256"]} for x in file_records],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "snap_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def create_snapshot(
    root: str | Path = ".",
    *,
    snapshots_dir: str | Path = "results/snapshots",
    allow_unexpected: bool = False,
) -> SnapshotResult:
    root = Path(root).resolve()
    gate = run_quality_gate(root, allow_unexpected=allow_unexpected)
    if not gate.ready_for_8b:
        failed = gate.checks[(gate.checks["severity"] == "BLOCKER") & (~gate.checks["passed"].astype(bool))]
        failed_ids = ", ".join(failed["check_id"].astype(str))
        raise DataContractError(f"8A.21 quality gate FAILED; snapshot not created. Failed: {failed_ids}")

    files = _hash_records(root, _input_paths(root))
    snapshot_id = _deterministic_snapshot_id(files)
    base = Path(snapshots_dir)
    if not base.is_absolute():
        base = root / base
    snapshot_path = base / snapshot_id
    data_dir = snapshot_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Copy exact bytes, preserving repository-relative paths under data/.
    for record in files:
        rel = Path(str(record["path"]))
        dest = data_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dest)

    gate.checks.to_csv(snapshot_path / "quality_gate_report.csv", index=False)
    gate.scientific_status.to_csv(snapshot_path / "scientific_status_summary.csv", index=False)

    manifest: dict[str, object] = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "quality_gate_schema_version": QUALITY_GATE_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "status": "READY_FOR_8B",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "records": {
            "master_comparisons": int(pd.read_csv(root / "results/processed/master_comparisons.csv").shape[0]),
            "unique_physical_points": int(pd.read_csv(root / "results/processed/master_experiment_catalog.csv").shape[0]),
        },
        "scientific_status": {
            str(row.equivalence_status): int(row.count) for row in gate.scientific_status.itertuples()
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
    }
    with (snapshot_path / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    (snapshot_path / "README.txt").write_text(
        "Prompt 8A.21 frozen dataset snapshot\n"
        f"snapshot_id: {snapshot_id}\n"
        "status: READY_FOR_8B\n\n"
        "Files under data/ are exact copies of the canonical analysis inputs.\n"
        "Run `python -m scripts.analysis.build_quality_snapshot --verify <snapshot>` "
        "to verify their SHA-256 checksums.\n",
        encoding="utf-8",
    )
    return SnapshotResult(snapshot_id, snapshot_path, manifest, gate)


def verify_snapshot(snapshot_path: str | Path) -> tuple[bool, pd.DataFrame]:
    path = Path(snapshot_path)
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise DataContractError(f"Snapshot manifest missing: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("snapshot_schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise DataContractError(
            f"Unsupported snapshot schema {manifest.get('snapshot_schema_version')!r}"
        )

    rows: list[dict[str, object]] = []
    for record in manifest.get("files", []):
        rel = Path(record["path"])
        file_path = path / "data" / rel
        exists = file_path.exists()
        actual = sha256_file(file_path) if exists else None
        expected = str(record["sha256"])
        rows.append(
            {
                "path": rel.as_posix(),
                "exists": exists,
                "sha256_expected": expected,
                "sha256_actual": actual,
                "match": bool(exists and actual == expected),
            }
        )
    report = pd.DataFrame(rows)
    ok = bool(not report.empty and report["match"].all())
    return ok, report
