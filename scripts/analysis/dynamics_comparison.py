"""Prompt 8B.5: analyze Glauber and Metropolis separately, then compare their contrasts.

The scientific target remains Standard-vs-n-fold equivalence *within each underlying
dynamics*. Glauber and Metropolis are not treated as interchangeable dynamics.

A secondary, descriptive paired diagnostic compares the Glauber/Metropolis lifetime
contrast produced by Standard and n-fold at the same physical point. No CPU or speed-up
quantities are used here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .load_results import DataContractError

DYNAMICS_SCHEMA_VERSION = "8B5.1"

_REQUIRED = (
    "analysis_snapshot", "comparison_id", "experiment_id", "study", "dynamics",
    "L", "N", "T", "J", "H",
    "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
    "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
    "equivalence_band_lo", "equivalence_band_hi", "ratio_ci_band_relation",
    "equivalence_status_8b",
)

_ALLOWED_DYNAMICS = {"glauber", "metropolis"}


@dataclass(frozen=True)
class DynamicsComparisonResult:
    records: pd.DataFrame
    dynamics_summary: pd.DataFrame
    matched_pairs: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError("8B.5 missing required columns: " + ", ".join(missing))


def _dynamics_status(g: pd.DataFrame) -> str:
    statuses = set(g["equivalence_status_8b"].astype(str).str.upper())
    relations = set(g["ratio_ci_band_relation"].astype(str))
    if "FAIL" in statuses or "OUTSIDE_EQUIVALENCE_BAND" in relations:
        return "DISCREPANCY_DETECTED"
    if statuses == {"PASS"} and relations == {"INSIDE_EQUIVALENCE_BAND"}:
        return "ROBUST_IN_TESTED_DOMAIN"
    if "INCONCLUSIVE" in statuses and "FAIL" not in statuses:
        return "NO_DISCREPANCY_WITH_PRECISION_LIMITS"
    return "REVIEW_REQUIRED"


def _matched_pair_status(row: pd.Series) -> str:
    a = str(row["equivalence_status_8b_glauber"]).upper()
    b = str(row["equivalence_status_8b_metropolis"]).upper()
    if "FAIL" in {a, b}:
        return "AT_LEAST_ONE_FAIL"
    if "INCONCLUSIVE" in {a, b}:
        return "AT_LEAST_ONE_INCONCLUSIVE"
    if a == "PASS" and b == "PASS":
        return "BOTH_PASS"
    return "REVIEW_REQUIRED"


def analyze_dynamics(records: pd.DataFrame) -> DynamicsComparisonResult:
    _require_columns(records, _REQUIRED)
    if records.empty:
        raise DataContractError("8B.5 cannot analyze an empty 8B.1 table")

    df = records.copy()
    snapshots = df["analysis_snapshot"].dropna().astype(str).unique().tolist()
    if len(snapshots) != 1:
        raise DataContractError("8B.5 requires exactly one analysis_snapshot")
    snapshot_id = snapshots[0]

    df["dynamics"] = df["dynamics"].astype(str).str.lower().str.strip()
    observed = set(df["dynamics"].dropna().unique())
    unknown = observed - _ALLOWED_DYNAMICS
    if unknown:
        raise DataContractError("8B.5 found unsupported dynamics: " + ", ".join(sorted(unknown)))
    missing_dyn = _ALLOWED_DYNAMICS - observed
    if missing_dyn:
        raise DataContractError("8B.5 requires both dynamics: " + ", ".join(sorted(missing_dyn)))

    numeric = [
        "L", "N", "T", "J", "H",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
        "equivalence_band_lo", "equivalence_band_hi",
    ]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    bad = (
        df[["L", "N", "T", "J", "H"]].isna().any(axis=1)
        | (df["L"] <= 0) | (df["T"] <= 0)
        | (df["N"] != df["L"] * df["L"])
    )
    if bad.any():
        raise DataContractError("8B.5 found invalid physical context")

    duplicate_key = ["study", "dynamics", "L", "N", "T", "J", "H"]
    if df.duplicated(subset=duplicate_key, keep=False).any():
        raise DataContractError("8B.5 found duplicate records within a dynamics/campaign point")

    df["dynamics_schema_version"] = DYNAMICS_SCHEMA_VERSION
    df["abs_ratio_deviation_pct_8b5"] = 100.0 * (df["lifetime_ratio_nfold_standard"] - 1.0).abs()
    df["ratio_ci95_width_8b5"] = df["ratio_ci95_hi"] - df["ratio_ci95_lo"]

    summary_rows = []
    for dynamics, g in df.groupby("dynamics", sort=True):
        status = g["equivalence_status_8b"].astype(str).str.upper()
        ci_contains_one = (g["ratio_ci95_lo"] <= 1.0) & (g["ratio_ci95_hi"] >= 1.0)
        inside_band = g["ratio_ci_band_relation"].astype(str) == "INSIDE_EQUIVALENCE_BAND"
        summary_rows.append({
            "dynamics_schema_version": DYNAMICS_SCHEMA_VERSION,
            "analysis_snapshot": snapshot_id,
            "dynamics": dynamics,
            "record_count": int(len(g)),
            "unique_physical_points": int(g["experiment_id"].nunique()),
            "studies": ";".join(sorted(g["study"].astype(str).unique())),
            "pass_count": int((status == "PASS").sum()),
            "inconclusive_count": int((status == "INCONCLUSIVE").sum()),
            "fail_count": int((status == "FAIL").sum()),
            "inside_equivalence_band_count": int(inside_band.sum()),
            "ci_contains_one_count": int(ci_contains_one.sum()),
            "median_abs_ratio_deviation_pct": float(g["abs_ratio_deviation_pct_8b5"].median()),
            "mean_abs_ratio_deviation_pct": float(g["abs_ratio_deviation_pct_8b5"].mean()),
            "max_abs_ratio_deviation_pct": float(g["abs_ratio_deviation_pct_8b5"].max()),
            "min_lifetime_ratio": float(g["lifetime_ratio_nfold_standard"].min()),
            "max_lifetime_ratio": float(g["lifetime_ratio_nfold_standard"].max()),
            "max_ratio_ci95_width": float(g["ratio_ci95_width_8b5"].max()),
            "dynamics_equivalence_status": _dynamics_status(g),
        })
    dynamics_summary = pd.DataFrame(summary_rows).sort_values("dynamics").reset_index(drop=True)

    pair_key = ["study", "L", "N", "T", "J", "H"]
    selected = df[pair_key + [
        "dynamics", "comparison_id", "experiment_id",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
        "equivalence_status_8b",
    ]].copy()

    counts = selected.groupby(pair_key, dropna=False)["dynamics"].nunique()
    incomplete_keys = counts[counts != 2]
    if len(incomplete_keys):
        raise DataContractError("8B.5 requires matched Glauber/Metropolis records at every campaign point")

    pivot = selected.pivot(index=pair_key, columns="dynamics", values=[
        "comparison_id", "experiment_id",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
        "equivalence_status_8b",
    ]).reset_index()
    pivot.columns = [
        "_".join(str(v) for v in c if str(v) != "") if isinstance(c, tuple) else str(c)
        for c in pivot.columns
    ]

    pivot["dynamics_schema_version"] = DYNAMICS_SCHEMA_VERSION
    pivot["analysis_snapshot"] = snapshot_id
    pivot["tau_glauber_over_metropolis_standard"] = (
        pivot["mean_tau_standard_mcss_glauber"] / pivot["mean_tau_standard_mcss_metropolis"]
    )
    pivot["tau_glauber_over_metropolis_nfold"] = (
        pivot["mean_tau_nfold_mcss_glauber"] / pivot["mean_tau_nfold_mcss_metropolis"]
    )
    pivot["dynamic_contrast_preservation_ratio"] = (
        pivot["tau_glauber_over_metropolis_nfold"] / pivot["tau_glauber_over_metropolis_standard"]
    )
    pivot["dynamic_contrast_preservation_abs_pct"] = (
        100.0 * (pivot["dynamic_contrast_preservation_ratio"] - 1.0).abs()
    )
    pivot["matched_pair_status"] = pivot.apply(_matched_pair_status, axis=1)

    diagnostics = pd.DataFrame([
        {"diagnostic": "analysis_snapshot", "value": snapshot_id},
        {"diagnostic": "records_total", "value": int(len(df))},
        {"diagnostic": "glauber_records", "value": int((df["dynamics"] == "glauber").sum())},
        {"diagnostic": "metropolis_records", "value": int((df["dynamics"] == "metropolis").sum())},
        {"diagnostic": "matched_physical_campaign_pairs", "value": int(len(pivot))},
        {"diagnostic": "both_pass_pairs", "value": int((pivot["matched_pair_status"] == "BOTH_PASS").sum())},
        {"diagnostic": "pairs_with_inconclusive", "value": int((pivot["matched_pair_status"] == "AT_LEAST_ONE_INCONCLUSIVE").sum())},
        {"diagnostic": "pairs_with_fail", "value": int((pivot["matched_pair_status"] == "AT_LEAST_ONE_FAIL").sum())},
        {"diagnostic": "glauber_tau_gt_metropolis_standard_count", "value": int((pivot["tau_glauber_over_metropolis_standard"] > 1).sum())},
        {"diagnostic": "glauber_tau_gt_metropolis_nfold_count", "value": int((pivot["tau_glauber_over_metropolis_nfold"] > 1).sum())},
        {"diagnostic": "median_dynamic_contrast_preservation_abs_pct", "value": float(pivot["dynamic_contrast_preservation_abs_pct"].median())},
        {"diagnostic": "max_dynamic_contrast_preservation_abs_pct", "value": float(pivot["dynamic_contrast_preservation_abs_pct"].max())},
        {"diagnostic": "dynamic_contrast_preservation_within_5pct_count", "value": int(((pivot["dynamic_contrast_preservation_ratio"] >= 0.95) & (pivot["dynamic_contrast_preservation_ratio"] <= 1.05)).sum())},
    ])

    return DynamicsComparisonResult(
        records=df.sort_values(["dynamics", "study", "H", "T", "L"]).reset_index(drop=True),
        dynamics_summary=dynamics_summary,
        matched_pairs=pivot.sort_values(["study", "H", "T", "L"]).reset_index(drop=True),
        diagnostics=diagnostics,
    )
