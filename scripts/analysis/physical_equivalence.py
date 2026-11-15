"""Prompt 8B.1: scientific Standard-vs-n-fold equivalence analysis.

This module deliberately analyzes *physics*, not computational performance.  The primary
endpoint is the metastable escape-time law.  The practical-equivalence criterion uses the
predeclared bootstrap confidence interval for the mean lifetime ratio.  KS results, when
available, are kept as a complementary distributional diagnostic: failure to reject a KS
null is not treated as proof of equality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .load_results import DataContractError

PHYSICAL_EQUIVALENCE_SCHEMA_VERSION = "8B1.1"

_REQUIRED = (
    "comparison_id",
    "experiment_id",
    "study",
    "dynamics",
    "L",
    "N",
    "T",
    "J",
    "H",
    "mean_tau_standard_mcss",
    "mean_tau_nfold_mcss",
    "lifetime_ratio_nfold_standard",
    "ratio_ci95_lo",
    "ratio_ci95_hi",
    "equivalence_margin",
    "equivalence_pass",
    "equivalence_status",
)

_NUMERIC = (
    "L", "N", "T", "J", "H",
    "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
    "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
    "equivalence_margin", "ks_statistic", "ks_pvalue",
)


@dataclass(frozen=True)
class PhysicalEquivalenceResult:
    records: pd.DataFrame
    summary: pd.DataFrame
    diagnostics: pd.DataFrame


def _to_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.fillna(False).astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False})


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError(f"8B.1 missing required columns: {', '.join(missing)}")


def _normalize_status(row: pd.Series) -> str:
    raw = str(row.get("equivalence_status", "")).strip().upper()
    if raw in {"PASS", "INCONCLUSIVE", "FAIL"}:
        return raw

    passed = row.get("equivalence_pass")
    if pd.notna(passed) and bool(passed):
        return "PASS"

    lo = row.get("ratio_ci95_lo")
    hi = row.get("ratio_ci95_hi")
    margin = row.get("equivalence_margin")
    if pd.notna(lo) and pd.notna(hi) and pd.notna(margin):
        band_lo, band_hi = 1.0 - float(margin), 1.0 + float(margin)
        if float(lo) >= band_lo and float(hi) <= band_hi:
            return "PASS"
        if float(hi) < band_lo or float(lo) > band_hi:
            return "FAIL"
        return "INCONCLUSIVE"
    return "INCONCLUSIVE"


def _ci_band_relation(lo: float, hi: float, margin: float) -> str:
    if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(margin)):
        return "UNAVAILABLE"
    band_lo, band_hi = 1.0 - margin, 1.0 + margin
    if lo >= band_lo and hi <= band_hi:
        return "INSIDE_EQUIVALENCE_BAND"
    if hi < band_lo or lo > band_hi:
        return "OUTSIDE_EQUIVALENCE_BAND"
    return "OVERLAPS_EQUIVALENCE_BOUNDARY"


def _combined_evidence(row: pd.Series) -> str:
    status = row["equivalence_status_8b"]
    ks_available = bool(row["ks_available"])
    ks_holm = row.get("ks_holm_reject_fwer_0p05")

    if status == "FAIL":
        return "DISCREPANCY_IN_MEAN_LIFETIME"
    if status == "INCONCLUSIVE":
        return "INCONCLUSIVE_PRECISION"
    if ks_available and pd.notna(ks_holm) and bool(ks_holm):
        return "MIXED_MEAN_EQUIVALENT_BUT_DISTRIBUTION_REJECTED"
    if ks_available:
        return "SUPPORTED_WITHIN_TESTED_METRICS"
    return "MEAN_EQUIVALENCE_SUPPORTED_KS_UNAVAILABLE"


def prepare_physical_equivalence(master: pd.DataFrame, *, snapshot_id: str = "UNFROZEN") -> pd.DataFrame:
    """Create one scientific-equivalence record per campaign comparison.

    Historical scientific decisions are preserved. Derived columns summarize effect size and
    precision without rewriting the original bootstrap/KS outcomes.
    """
    _require_columns(master, _REQUIRED)
    if master.empty:
        raise DataContractError("8B.1 cannot analyze an empty master comparison table")

    df = master.copy()
    for col in _NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Structural physics checks repeated at the analysis boundary.
    bad = (
        df["L"].isna() | df["N"].isna() | df["T"].isna() | df["J"].isna() | df["H"].isna()
        | (df["L"] <= 0) | (df["T"] <= 0)
        | (df["N"] != df["L"] * df["L"])
    )
    if bad.any():
        ids = ", ".join(df.loc[bad, "comparison_id"].astype(str).head(5))
        raise DataContractError(f"8B.1 found invalid physical context; examples: {ids}")

    eq_bool = _to_bool(df["equivalence_pass"])
    df["equivalence_pass"] = eq_bool
    df["equivalence_status_8b"] = df.apply(_normalize_status, axis=1)

    ratio = df["lifetime_ratio_nfold_standard"]
    if (ratio <= 0).any() or ratio.isna().any():
        raise DataContractError("8B.1 requires positive finite lifetime ratios")

    df["log_lifetime_ratio"] = np.log(ratio)
    df["relative_difference_pct"] = 100.0 * (ratio - 1.0)
    df["absolute_relative_difference_pct"] = df["relative_difference_pct"].abs()
    df["equivalence_band_lo"] = 1.0 - df["equivalence_margin"]
    df["equivalence_band_hi"] = 1.0 + df["equivalence_margin"]
    df["ratio_ci95_width"] = df["ratio_ci95_hi"] - df["ratio_ci95_lo"]
    df["ratio_ci_contains_one_8b"] = (df["ratio_ci95_lo"] <= 1.0) & (df["ratio_ci95_hi"] >= 1.0)
    df["ratio_ci_band_relation"] = [
        _ci_band_relation(lo, hi, margin)
        for lo, hi, margin in zip(df["ratio_ci95_lo"], df["ratio_ci95_hi"], df["equivalence_margin"])
    ]

    if "ks_statistic" not in df:
        df["ks_statistic"] = np.nan
    if "ks_pvalue" not in df:
        df["ks_pvalue"] = np.nan
    df["ks_available"] = df["ks_statistic"].notna() & df["ks_pvalue"].notna()

    if "ks_holm_reject_fwer_0p05" in df:
        holm = _to_bool(df["ks_holm_reject_fwer_0p05"])
        # Preserve unavailable values rather than coercing them to False.
        raw_missing = df["ks_holm_reject_fwer_0p05"].isna()
        holm = holm.astype("boolean")
        holm.loc[raw_missing] = pd.NA
        df["ks_holm_reject_fwer_0p05"] = holm
    else:
        df["ks_holm_reject_fwer_0p05"] = pd.Series(pd.NA, index=df.index, dtype="boolean")

    df["combined_evidence"] = df.apply(_combined_evidence, axis=1)
    df["analysis_schema_version"] = PHYSICAL_EQUIVALENCE_SCHEMA_VERSION
    df["analysis_snapshot"] = snapshot_id

    front = [
        "analysis_schema_version", "analysis_snapshot", "comparison_id", "experiment_id",
        "study", "dynamics", "L", "N", "T", "J", "H",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "log_lifetime_ratio",
        "relative_difference_pct", "absolute_relative_difference_pct",
        "ratio_ci95_lo", "ratio_ci95_hi", "ratio_ci95_width",
        "equivalence_margin", "equivalence_band_lo", "equivalence_band_hi",
        "ratio_ci_contains_one_8b", "ratio_ci_band_relation",
        "equivalence_pass", "equivalence_status_8b",
        "ks_available", "ks_statistic", "ks_pvalue", "ks_holm_reject_fwer_0p05",
        "combined_evidence",
    ]
    remainder = [c for c in df.columns if c not in front]
    return df[front + remainder]


def summarize_physical_equivalence(records: pd.DataFrame) -> pd.DataFrame:
    """Summarize equivalence without pooling distinct physical regimes."""
    group_cols = ["study", "dynamics", "H"]
    rows: list[dict[str, object]] = []
    for key, group in records.groupby(group_cols, dropna=False, sort=True):
        study, dynamics, H = key
        statuses = group["equivalence_status_8b"].value_counts()
        holm = group["ks_holm_reject_fwer_0p05"]
        rows.append({
            "analysis_schema_version": PHYSICAL_EQUIVALENCE_SCHEMA_VERSION,
            "analysis_snapshot": str(group["analysis_snapshot"].iloc[0]),
            "study": study,
            "dynamics": dynamics,
            "H": H,
            "records": int(len(group)),
            "pass_count": int(statuses.get("PASS", 0)),
            "inconclusive_count": int(statuses.get("INCONCLUSIVE", 0)),
            "fail_count": int(statuses.get("FAIL", 0)),
            "median_lifetime_ratio": float(group["lifetime_ratio_nfold_standard"].median()),
            "median_abs_relative_difference_pct": float(group["absolute_relative_difference_pct"].median()),
            "max_abs_relative_difference_pct": float(group["absolute_relative_difference_pct"].max()),
            "max_ratio_ci95_width": float(group["ratio_ci95_width"].max()),
            "ks_available_count": int(group["ks_available"].sum()),
            "ks_holm_rejection_count": int(holm.fillna(False).astype(bool).sum()),
        })
    return pd.DataFrame(rows)


def diagnostics_table(records: pd.DataFrame) -> pd.DataFrame:
    """Small audit table for the primary 8B.1 claims."""
    status = records["equivalence_status_8b"].value_counts()
    ks = records.loc[records["ks_available"], "ks_holm_reject_fwer_0p05"]
    rows = [
        {"diagnostic": "comparison_records", "value": int(len(records))},
        {"diagnostic": "unique_physical_points", "value": int(records["experiment_id"].nunique())},
        {"diagnostic": "pass_count", "value": int(status.get("PASS", 0))},
        {"diagnostic": "inconclusive_count", "value": int(status.get("INCONCLUSIVE", 0))},
        {"diagnostic": "fail_count", "value": int(status.get("FAIL", 0))},
        {"diagnostic": "ks_available_count", "value": int(records["ks_available"].sum())},
        {"diagnostic": "ks_holm_rejection_count", "value": int(ks.fillna(False).astype(bool).sum())},
        {"diagnostic": "median_abs_relative_difference_pct", "value": float(records["absolute_relative_difference_pct"].median())},
        {"diagnostic": "max_abs_relative_difference_pct", "value": float(records["absolute_relative_difference_pct"].max())},
    ]
    return pd.DataFrame(rows)


def analyze_physical_equivalence(master: pd.DataFrame, *, snapshot_id: str = "UNFROZEN") -> PhysicalEquivalenceResult:
    records = prepare_physical_equivalence(master, snapshot_id=snapshot_id)
    return PhysicalEquivalenceResult(
        records=records,
        summary=summarize_physical_equivalence(records),
        diagnostics=diagnostics_table(records),
    )
