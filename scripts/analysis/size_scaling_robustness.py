"""Prompt 8B.3: robustness of Standard-vs-n-fold physical equivalence with lattice size L.

This module uses only the *scalability_L* campaign from the frozen 8A.21 snapshot.
It asks whether the practical-equivalence conclusion for the metastable lifetime survives
as L increases.  Computational performance is intentionally excluded; those quantities
belong to Prompt 8C.

The primary robustness decision is deliberately conservative and audit-friendly:

* every tested L must preserve the 8B.1 practical-equivalence status PASS;
* every bootstrap interval for R_tau must lie fully inside the predeclared equivalence band;
* there must be at most one record for each physical L point within a scaling series.

Linear slopes versus log2(L) are reported only as descriptive drift diagnostics. They are
not treated as fitted critical exponents or as formal hypothesis tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .load_results import DataContractError

SIZE_SCALING_SCHEMA_VERSION = "8B3.1"

_REQUIRED = (
    "analysis_snapshot",
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
    "relative_difference_pct",
    "ratio_ci95_lo",
    "ratio_ci95_hi",
    "equivalence_band_lo",
    "equivalence_band_hi",
    "ratio_ci_contains_one_8b",
    "ratio_ci_band_relation",
    "equivalence_status_8b",
)


@dataclass(frozen=True)
class SizeScalingResult:
    records: pd.DataFrame
    summary: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError(f"8B.3 missing required columns: {', '.join(missing)}")


def _relative_span_pct(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return float("nan")
    mean = float(np.mean(x))
    if mean == 0.0:
        return float("nan")
    return 100.0 * float(np.max(x) - np.min(x)) / abs(mean)


def _descriptive_slope_per_doubling(L: np.ndarray, y: np.ndarray) -> float:
    if len(L) < 2:
        return float("nan")
    x = np.log2(L.astype(float))
    return float(np.polyfit(x, y.astype(float), 1)[0])


def _size_status(group: pd.DataFrame) -> str:
    statuses = set(group["equivalence_status_8b"].astype(str).str.upper())
    relations = set(group["ratio_ci_band_relation"].astype(str))
    if "FAIL" in statuses or "OUTSIDE_EQUIVALENCE_BAND" in relations:
        return "DISCREPANCY_AT_SOME_L"
    if statuses != {"PASS"}:
        return "INCONCLUSIVE_AT_SOME_L"
    if relations == {"INSIDE_EQUIVALENCE_BAND"}:
        return "ROBUST_ACROSS_TESTED_L"
    return "PASS_STATUS_BUT_CI_REVIEW_REQUIRED"


def analyze_size_scaling(records: pd.DataFrame) -> SizeScalingResult:
    """Analyze practical-equivalence robustness along the lattice-size campaign.

    Parameters
    ----------
    records:
        Output of Prompt 8B.1. All rows must belong to exactly one frozen snapshot.
    """
    _require_columns(records, _REQUIRED)
    if records.empty:
        raise DataContractError("8B.3 cannot analyze an empty 8B.1 table")

    df = records.copy()
    snapshots = df["analysis_snapshot"].dropna().astype(str).unique().tolist()
    if len(snapshots) != 1:
        raise DataContractError("8B.3 requires exactly one analysis_snapshot")
    snapshot_id = snapshots[0]

    scale = df.loc[df["study"].astype(str) == "scalability_L"].copy()
    if scale.empty:
        raise DataContractError("8B.3 found no scalability_L records")

    numeric_cols = (
        "L", "N", "T", "J", "H",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "relative_difference_pct",
        "ratio_ci95_lo", "ratio_ci95_hi", "equivalence_band_lo", "equivalence_band_hi",
    )
    for col in numeric_cols:
        scale[col] = pd.to_numeric(scale[col], errors="coerce")

    invalid = (
        scale[["L", "N", "T", "J", "H"]].isna().any(axis=1)
        | (scale["L"] <= 0)
        | (scale["T"] <= 0)
        | (scale["N"] != scale["L"] * scale["L"])
    )
    if invalid.any():
        raise DataContractError("8B.3 found invalid physical context in scalability_L")

    # One campaign-level comparison per physical size point.
    key = ["dynamics", "H", "T", "J", "L"]
    dup = scale.duplicated(subset=key, keep=False)
    if dup.any():
        examples = scale.loc[dup, key].drop_duplicates().head(5)
        raise DataContractError(
            "8B.3 found duplicate scalability records: "
            + examples.astype(str).agg("/".join, axis=1).str.cat(sep=", ")
        )

    scale["size_scaling_schema_version"] = SIZE_SCALING_SCHEMA_VERSION
    scale["log2_L"] = np.log2(scale["L"].astype(float))
    scale["ratio_distance_from_one"] = scale["lifetime_ratio_nfold_standard"] - 1.0
    scale["ratio_distance_from_one_pct"] = 100.0 * scale["ratio_distance_from_one"]
    scale["size_series_key"] = (
        scale["dynamics"].astype(str)
        + "|H=" + scale["H"].map(lambda x: f"{x:.12g}")
        + "|T=" + scale["T"].map(lambda x: f"{x:.12g}")
        + "|J=" + scale["J"].map(lambda x: f"{x:.12g}")
    )

    summary_rows: list[dict[str, object]] = []
    group_key = ["dynamics", "H", "T", "J"]
    for keys, group in scale.groupby(group_key, sort=True, dropna=False):
        dynamics, H, T, J = keys
        g = group.sort_values("L").reset_index(drop=True)
        if g["L"].nunique() < 2:
            raise DataContractError(f"8B.3 size series has fewer than two L values: {keys}")

        L = g["L"].to_numpy(dtype=float)
        ratio = g["lifetime_ratio_nfold_standard"].to_numpy(dtype=float)
        diff_pct = 100.0 * (ratio - 1.0)
        std_tau = g["mean_tau_standard_mcss"].to_numpy(dtype=float)
        nf_tau = g["mean_tau_nfold_mcss"].to_numpy(dtype=float)

        status = _size_status(g)
        std_log_slope = _descriptive_slope_per_doubling(L, np.log(std_tau))
        nf_log_slope = _descriptive_slope_per_doubling(L, np.log(nf_tau))

        summary_rows.append({
            "size_scaling_schema_version": SIZE_SCALING_SCHEMA_VERSION,
            "analysis_snapshot": snapshot_id,
            "dynamics": str(dynamics),
            "H": float(H),
            "T": float(T),
            "J": float(J),
            "L_count": int(g["L"].nunique()),
            "L_values": ";".join(str(int(v)) for v in sorted(g["L"].unique())),
            "L_min": int(g["L"].min()),
            "L_max": int(g["L"].max()),
            "N_min": int(g["N"].min()),
            "N_max": int(g["N"].max()),
            "pass_count": int((g["equivalence_status_8b"].astype(str).str.upper() == "PASS").sum()),
            "inconclusive_count": int((g["equivalence_status_8b"].astype(str).str.upper() == "INCONCLUSIVE").sum()),
            "fail_count": int((g["equivalence_status_8b"].astype(str).str.upper() == "FAIL").sum()),
            "ci_inside_equivalence_band_count": int((g["ratio_ci_band_relation"] == "INSIDE_EQUIVALENCE_BAND").sum()),
            "ci_contains_one_count": int(g["ratio_ci_contains_one_8b"].astype(bool).sum()),
            "ratio_min": float(np.min(ratio)),
            "ratio_max": float(np.max(ratio)),
            "ratio_span_percentage_points": 100.0 * float(np.max(ratio) - np.min(ratio)),
            "median_abs_ratio_deviation_pct": float(np.median(np.abs(diff_pct))),
            "max_abs_ratio_deviation_pct": float(np.max(np.abs(diff_pct))),
            "ratio_slope_percentage_points_per_L_doubling": _descriptive_slope_per_doubling(L, diff_pct),
            "endpoint_ratio_change_percentage_points": float(diff_pct[-1] - diff_pct[0]),
            "standard_tau_relative_span_pct": _relative_span_pct(g["mean_tau_standard_mcss"]),
            "nfold_tau_relative_span_pct": _relative_span_pct(g["mean_tau_nfold_mcss"]),
            "standard_tau_endpoint_ratio_Lmax_over_Lmin": float(std_tau[-1] / std_tau[0]),
            "nfold_tau_endpoint_ratio_Lmax_over_Lmin": float(nf_tau[-1] / nf_tau[0]),
            # Descriptive effective slopes of log(tau) vs log2(L), not critical exponents.
            "standard_log_tau_slope_per_L_doubling": std_log_slope,
            "nfold_log_tau_slope_per_L_doubling": nf_log_slope,
            "delta_log_tau_slope_nfold_minus_standard": nf_log_slope - std_log_slope,
            "size_robust": status == "ROBUST_ACROSS_TESTED_L",
            "size_robustness_status": status,
        })

    summary = pd.DataFrame(summary_rows).sort_values(["dynamics", "H"]).reset_index(drop=True)
    status_counts = summary["size_robustness_status"].value_counts()

    diagnostics = pd.DataFrame([
        {"diagnostic": "analysis_snapshot", "value": snapshot_id},
        {"diagnostic": "scalability_records", "value": int(len(scale))},
        {"diagnostic": "size_series", "value": int(len(summary))},
        {"diagnostic": "unique_L_values", "value": ";".join(str(int(v)) for v in sorted(scale["L"].unique()))},
        {"diagnostic": "robust_series", "value": int(status_counts.get("ROBUST_ACROSS_TESTED_L", 0))},
        {"diagnostic": "inconclusive_series", "value": int(status_counts.get("INCONCLUSIVE_AT_SOME_L", 0))},
        {"diagnostic": "discrepant_series", "value": int(status_counts.get("DISCREPANCY_AT_SOME_L", 0))},
        {"diagnostic": "pass_records", "value": int((scale["equivalence_status_8b"].astype(str).str.upper() == "PASS").sum())},
        {"diagnostic": "inconclusive_records", "value": int((scale["equivalence_status_8b"].astype(str).str.upper() == "INCONCLUSIVE").sum())},
        {"diagnostic": "fail_records", "value": int((scale["equivalence_status_8b"].astype(str).str.upper() == "FAIL").sum())},
        {"diagnostic": "ci_inside_equivalence_band_records", "value": int((scale["ratio_ci_band_relation"] == "INSIDE_EQUIVALENCE_BAND").sum())},
        {"diagnostic": "ci_contains_one_records", "value": int(scale["ratio_ci_contains_one_8b"].astype(bool).sum())},
        {"diagnostic": "max_abs_ratio_deviation_pct", "value": float(summary["max_abs_ratio_deviation_pct"].max())},
        {"diagnostic": "max_abs_ratio_drift_per_doubling_pp", "value": float(summary["ratio_slope_percentage_points_per_L_doubling"].abs().max())},
        {"diagnostic": "max_abs_delta_log_tau_slope", "value": float(summary["delta_log_tau_slope_nfold_minus_standard"].abs().max())},
    ])

    return SizeScalingResult(
        records=scale.sort_values(["dynamics", "H", "L"]).reset_index(drop=True),
        summary=summary,
        diagnostics=diagnostics,
    )
