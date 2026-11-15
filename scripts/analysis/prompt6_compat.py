"""Compatibility adapter for Prompt 6 validation/scalability/temperature summaries.

The Prompt 6 campaign predates the versioned Prompt 8A analysis contract.  Its three
summary CSVs use related but not identical column names.  This module converts them into
one *comparison-level* schema while preserving provenance and, crucially, without
pretending that already-aggregated rows are raw independent runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .contracts import (
    COMPARISON_COLUMNS,
    COMPARISON_SUMMARY,
    CONTEXT_SCHEMA_VERSION,
    PHYSICAL_CONTEXT_FIELDS,
    SCHEMA_VERSION,
)
from .load_results import DataContractError


@dataclass(frozen=True)
class CompatibilityResults:
    comparisons: pd.DataFrame
    report: pd.DataFrame


SIGNATURES: dict[str, set[str]] = {
    "validation": {
        "mean_standard_mcss",
        "mean_nfold_mcss",
        "ratio_nfold_standard",
        "ks_D",
        "mean_standard_attempts",
        "mean_nfold_events",
    },
    "scalability_L": {
        "L",
        "runs",
        "mean_tau_standard_mcss",
        "mean_tau_nfold_mcss",
        "cpu_standard_s_per_escape",
        "speedup_standard_over_nfold",
    },
    "temperature_sweep": {
        "T",
        "invT",
        "equivalence_status",
        "ks_holm_reject_fwer_0p05",
        "mean_tau_standard_mcss",
        "mean_tau_nfold_mcss",
    },
}

SOURCE_SCHEMAS = {
    "validation": "prompt6.validation_summary.v1",
    "scalability_L": "prompt6.scalability_summary.v1",
    "temperature_sweep": "prompt6.temperature_sweep_summary.v1",
}

# Canonical comparison field -> historical alternatives, in preference order.
COLUMN_MAP: dict[str, tuple[str, ...]] = {
    "dynamics": ("dynamics",),
    "L": ("L",),
    "N": ("N",),
    "T": ("T",),
    "invT": ("invT",),
    "J": ("J",),
    "H": ("H",),
    "runs": ("runs",),
    "n_standard": ("n_standard",),
    "n_nfold": ("n_nfold",),
    "mean_tau_standard_mcss": ("mean_tau_standard_mcss", "mean_standard_mcss"),
    "median_tau_standard_mcss": ("median_tau_standard_mcss", "median_standard_mcss"),
    "sd_tau_standard_mcss": ("sd_tau_standard_mcss", "sd_standard_mcss"),
    "mean_tau_nfold_mcss": ("mean_tau_nfold_mcss", "mean_nfold_mcss"),
    "median_tau_nfold_mcss": ("median_tau_nfold_mcss", "median_nfold_mcss"),
    "sd_tau_nfold_mcss": ("sd_tau_nfold_mcss", "sd_nfold_mcss"),
    "mean_tau_standard_ci95_lo": ("mean_standard_ci95_lo",),
    "mean_tau_standard_ci95_hi": ("mean_standard_ci95_hi",),
    "mean_tau_nfold_ci95_lo": ("mean_nfold_ci95_lo",),
    "mean_tau_nfold_ci95_hi": ("mean_nfold_ci95_hi",),
    "lifetime_ratio_nfold_standard": ("lifetime_ratio_nfold_standard", "ratio_nfold_standard"),
    "ratio_ci95_lo": ("ratio_bootstrap_ci95_lo",),
    "ratio_ci95_hi": ("ratio_bootstrap_ci95_hi",),
    "equivalence_margin": ("equivalence_margin",),
    "equivalence_pass": ("equivalence_pass",),
    "equivalence_status": ("equivalence_status",),
    "ratio_ci_contains_one": ("ratio_ci_contains_one",),
    "ks_statistic": ("ks_statistic", "ks_D"),
    "ks_pvalue": ("ks_pvalue", "ks_p"),
    "ks_holm_reject_fwer_0p05": ("ks_holm_reject_fwer_0p05",),
    "cpu_standard_s_per_escape": ("cpu_standard_s_per_escape",),
    "cpu_nfold_s_per_escape": ("cpu_nfold_s_per_escape",),
    "speedup_standard_over_nfold": (
        "speedup_standard_over_nfold",
        "mean_per_run_cpu_ratio_std_over_nfold",
    ),
    "mean_standard_attempts_per_escape": (
        "mean_standard_attempts_per_escape",
        "mean_standard_attempts",
    ),
    "mean_nfold_equiv_attempts_per_escape": (
        "mean_nfold_equiv_attempts_per_escape",
        "mean_nfold_equiv_attempts",
    ),
    "mean_nfold_events_per_escape": ("mean_nfold_events_per_escape", "mean_nfold_events"),
    "nfold_equiv_attempts_per_event": (
        "nfold_equiv_attempts_per_event",
        "nfold_weighted_mean_wait",
    ),
    "standard_acceptance_fraction": ("standard_acceptance_fraction",),
    "standard_cpu_ns_per_attempt": ("standard_cpu_ns_per_attempt",),
    "nfold_cpu_ns_per_event": ("nfold_cpu_ns_per_event",),
}

BOOLEAN_COLUMNS = {
    "equivalence_pass",
    "ratio_ci_contains_one",
    "ks_holm_reject_fwer_0p05",
}

NUMERIC_COLUMNS = set(COLUMN_MAP).difference(BOOLEAN_COLUMNS).difference({"dynamics", "equivalence_status"})


def _first_present(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    actual = {str(c).lower(): str(c) for c in columns}
    for candidate in candidates:
        hit = actual.get(candidate.lower())
        if hit is not None:
            return hit
    return None


def detect_prompt6_study(df: pd.DataFrame, path: str | Path = "<dataframe>") -> str:
    columns = set(map(str, df.columns))
    # Temperature sweep is a strict extension of much of the scalability schema,
    # so detect the most specific signatures first.
    for study in ("temperature_sweep", "validation", "scalability_L"):
        if SIGNATURES[study].issubset(columns):
            return study
    raise DataContractError(
        f"Cannot identify Prompt 6 summary schema for {path}. "
        f"Columns include: {sorted(columns)}"
    )


def _coerce_bool_value(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer, float, np.floating)) and np.isfinite(value):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
    key = str(value).strip().lower()
    if key in {"1", "true", "t", "yes", "y", "pass"}:
        return True
    if key in {"0", "false", "f", "no", "n", "fail"}:
        return False
    raise DataContractError(f"Cannot interpret boolean value {value!r}")


def load_context(path: str | Path | None) -> dict[str, dict[str, object]]:
    """Load explicit metadata for legacy files that omitted physical parameters."""
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    version = payload.get("schema_version")
    if version != CONTEXT_SCHEMA_VERSION:
        raise DataContractError(
            f"Context file {p} has schema_version={version!r}; expected {CONTEXT_SCHEMA_VERSION!r}"
        )
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise DataContractError(f"Context file {p}: 'files' must be a JSON object")
    return {str(k): dict(v) for k, v in files.items()}


def _context_for(path: Path, context: dict[str, dict[str, object]]) -> dict[str, object]:
    # Prefer an exact relative/path key if supplied, then basename for portability.
    for key in (path.as_posix(), path.name):
        if key in context:
            return context[key]
    return {}


def _copy_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for canonical, candidates in COLUMN_MAP.items():
        present = _first_present(df.columns, candidates)
        out[canonical] = df[present] if present is not None else pd.NA
    return out


def _apply_context(
    out: pd.DataFrame,
    context_values: dict[str, object],
    source_file: str,
) -> list[str]:
    applied: list[str] = []
    for field, value in context_values.items():
        if field not in {"L", "N", "T", "invT", "J", "H", "dynamics"}:
            continue
        if field not in out.columns:
            continue
        existing = out[field]
        present = existing.notna()
        if present.any():
            if field == "dynamics":
                conflict = present & (existing.astype(str).str.lower() != str(value).lower())
            else:
                numeric = pd.to_numeric(existing, errors="coerce")
                conflict = present & ~np.isclose(numeric, float(value), equal_nan=False)
            if conflict.any():
                rows = out.index[conflict].tolist()[:5]
                raise DataContractError(
                    f"Context for {source_file} conflicts with stored {field} in rows {rows}"
                )
        missing = ~present
        if missing.any():
            out.loc[missing, field] = value
            applied.append(field)
    return applied


def _derive_non_destructive(out: pd.DataFrame) -> None:
    """Fill only mathematically redundant fields; never replace recorded measurements."""
    L = pd.to_numeric(out["L"], errors="coerce")
    N = pd.to_numeric(out["N"], errors="coerce")
    missing_n = N.isna() & L.notna()
    out.loc[missing_n, "N"] = L[missing_n] ** 2

    T = pd.to_numeric(out["T"], errors="coerce")
    invT = pd.to_numeric(out["invT"], errors="coerce")
    missing_inv = invT.isna() & T.notna() & (T != 0)
    out.loc[missing_inv, "invT"] = 1.0 / T[missing_inv]

    runs = pd.to_numeric(out["runs"], errors="coerce")
    ns = pd.to_numeric(out["n_standard"], errors="coerce")
    nn = pd.to_numeric(out["n_nfold"], errors="coerce")
    missing_runs = runs.isna() & ns.notna() & nn.notna() & np.isclose(ns, nn)
    out.loc[missing_runs, "runs"] = ns[missing_runs]

    ratio = pd.to_numeric(out["lifetime_ratio_nfold_standard"], errors="coerce")
    std = pd.to_numeric(out["mean_tau_standard_mcss"], errors="coerce")
    nf = pd.to_numeric(out["mean_tau_nfold_mcss"], errors="coerce")
    missing_ratio = ratio.isna() & std.notna() & nf.notna() & (std != 0)
    out.loc[missing_ratio, "lifetime_ratio_nfold_standard"] = nf[missing_ratio] / std[missing_ratio]

    comp = pd.to_numeric(out["nfold_equiv_attempts_per_event"], errors="coerce")
    equiv = pd.to_numeric(out["mean_nfold_equiv_attempts_per_escape"], errors="coerce")
    events = pd.to_numeric(out["mean_nfold_events_per_escape"], errors="coerce")
    missing_comp = comp.isna() & equiv.notna() & events.notna() & (events > 0)
    out.loc[missing_comp, "nfold_equiv_attempts_per_event"] = equiv[missing_comp] / events[missing_comp]

    speed = pd.to_numeric(out["speedup_standard_over_nfold"], errors="coerce")
    cpu_s = pd.to_numeric(out["cpu_standard_s_per_escape"], errors="coerce")
    cpu_n = pd.to_numeric(out["cpu_nfold_s_per_escape"], errors="coerce")
    missing_speed = speed.isna() & cpu_s.notna() & cpu_n.notna() & (cpu_n > 0)
    out.loc[missing_speed, "speedup_standard_over_nfold"] = cpu_s[missing_speed] / cpu_n[missing_speed]


def _validate_physics(out: pd.DataFrame, source_file: str) -> None:
    L = pd.to_numeric(out["L"], errors="coerce")
    N = pd.to_numeric(out["N"], errors="coerce")
    both = L.notna() & N.notna()
    if (both & ~np.isclose(N, L * L)).any():
        rows = out.index[both & ~np.isclose(N, L * L)].tolist()[:5]
        raise DataContractError(f"{source_file}: N != L^2 in rows {rows}")

    T = pd.to_numeric(out["T"], errors="coerce")
    if (T.notna() & (T <= 0)).any():
        raise DataContractError(f"{source_file}: T must be positive")

    for field in ("equivalence_margin", "standard_acceptance_fraction"):
        x = pd.to_numeric(out[field], errors="coerce")
        if (x.notna() & (x < 0)).any():
            raise DataContractError(f"{source_file}: {field} cannot be negative")
    acceptance = pd.to_numeric(out["standard_acceptance_fraction"], errors="coerce")
    if (acceptance.notna() & (acceptance > 1)).any():
        raise DataContractError(f"{source_file}: standard_acceptance_fraction must lie in [0, 1]")


def normalize_prompt6_summary(
    df: pd.DataFrame,
    source_file: str | Path,
    context_values: dict[str, object] | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if df.empty:
        raise DataContractError(f"Legacy summary is empty: {source_file}")

    source = Path(source_file)
    study = detect_prompt6_study(df, source)
    out = _copy_columns(df)
    applied = _apply_context(out, context_values or {}, source.as_posix())
    _derive_non_destructive(out)

    # Validation summary predates an explicit PASS/INCONCLUSIVE string.  Preserve
    # uncertainty: false means NOT_PASS, not automatically a scientific FAIL.
    if out["equivalence_status"].isna().all():
        def status_from_pass(value: object) -> object:
            if pd.isna(value):
                return pd.NA
            return "PASS" if _coerce_bool_value(value) else "NOT_PASS"
        out["equivalence_status"] = out["equivalence_pass"].map(status_from_pass)

    for col in BOOLEAN_COLUMNS:
        out[col] = out[col].map(_coerce_bool_value).astype("boolean")

    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    _validate_physics(out, source.as_posix())

    out.insert(0, "schema_version", SCHEMA_VERSION)
    out.insert(1, "record_level", COMPARISON_SUMMARY)
    out.insert(2, "source_schema", SOURCE_SCHEMAS[study])
    out.insert(3, "study", study)
    out.insert(4, "source_file", source.as_posix())
    out.insert(5, "source_row", np.arange(len(out), dtype=int))

    missing_context = [field for field in PHYSICAL_CONTEXT_FIELDS if out[field].isna().any()]
    contract_status = "complete" if not missing_context else "partial"
    out["contract_status"] = contract_status
    out["context_fields_applied"] = ";".join(sorted(applied))

    # Ensure deterministic order and explicit missing optionals.
    for column in COMPARISON_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    out = out[COMPARISON_COLUMNS].copy()

    report = {
        "source_file": source.as_posix(),
        "source_schema": SOURCE_SCHEMAS[study],
        "study": study,
        "rows": int(len(out)),
        "contract_status": contract_status,
        "missing_physical_context": ";".join(missing_context),
        "context_fields_applied": ";".join(sorted(applied)),
    }
    return out, report


def discover_prompt6_summaries(root: str | Path) -> list[Path]:
    base = Path(root)
    if not base.exists():
        raise FileNotFoundError(f"Legacy Prompt 6 directory does not exist: {base}")
    preferred = {
        "validation_summary.csv",
        "scalability_summary.csv",
        "temperature_sweep_summary.csv",
    }
    files = sorted(p for p in base.rglob("*.csv") if p.is_file() and p.name in preferred)
    if not files:
        raise FileNotFoundError(
            f"No Prompt 6 summary CSVs found below {base}; expected one or more of {sorted(preferred)}"
        )
    return files


def load_prompt6_summaries(
    root: str | Path,
    context_path: str | Path | None = None,
) -> CompatibilityResults:
    context = load_context(context_path)
    frames: list[pd.DataFrame] = []
    reports: list[dict[str, object]] = []
    base = Path(root)

    for path in discover_prompt6_summaries(base):
        try:
            relative = path.relative_to(base)
        except ValueError:
            relative = path
        df = pd.read_csv(path)
        context_values = _context_for(path, context)
        normalized, report = normalize_prompt6_summary(df, relative, context_values)
        frames.append(normalized)
        reports.append(report)

    comparisons = pd.concat(frames, ignore_index=True)
    report_df = pd.DataFrame(reports).sort_values(["study", "source_file"], ignore_index=True)
    return CompatibilityResults(comparisons=comparisons, report=report_df)
