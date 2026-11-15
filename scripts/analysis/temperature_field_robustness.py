"""Prompt 8B.4: robustness of Standard-vs-n-fold equivalence across T and H.

Uses only the temperature_sweep campaign from one verified 8A.21 snapshot.
The primary decision remains the predeclared practical-equivalence criterion from 8B.1.
No CPU/speed-up quantities are used here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .load_results import DataContractError

TEMP_FIELD_SCHEMA_VERSION = "8B4.1"

_REQUIRED = (
    "analysis_snapshot", "comparison_id", "experiment_id", "study", "dynamics",
    "L", "N", "T", "J", "H", "runs",
    "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
    "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
    "equivalence_band_lo", "equivalence_band_hi", "ratio_ci_band_relation",
    "equivalence_status_8b",
)

@dataclass(frozen=True)
class TemperatureFieldResult:
    records: pd.DataFrame
    summary: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError("8B.4 missing required columns: " + ", ".join(missing))


def _series_status(group: pd.DataFrame) -> str:
    statuses = set(group["equivalence_status_8b"].astype(str).str.upper())
    relations = set(group["ratio_ci_band_relation"].astype(str))
    if "FAIL" in statuses or "OUTSIDE_EQUIVALENCE_BAND" in relations:
        return "DISCREPANCY_AT_SOME_T"
    if statuses == {"PASS"} and relations == {"INSIDE_EQUIVALENCE_BAND"}:
        return "ROBUST_ACROSS_TESTED_T"
    if "INCONCLUSIVE" in statuses and "FAIL" not in statuses:
        return "INCONCLUSIVE_AT_SOME_T"
    return "REVIEW_REQUIRED"


def analyze_temperature_field(records: pd.DataFrame) -> TemperatureFieldResult:
    _require_columns(records, _REQUIRED)
    if records.empty:
        raise DataContractError("8B.4 cannot analyze an empty 8B.1 table")

    df = records.copy()
    snapshots = df["analysis_snapshot"].dropna().astype(str).unique().tolist()
    if len(snapshots) != 1:
        raise DataContractError("8B.4 requires exactly one analysis_snapshot")
    snapshot_id = snapshots[0]

    sweep = df.loc[df["study"].astype(str) == "temperature_sweep"].copy()
    if sweep.empty:
        raise DataContractError("8B.4 found no temperature_sweep records")

    numeric = ["L","N","T","J","H","runs","mean_tau_standard_mcss","mean_tau_nfold_mcss",
               "lifetime_ratio_nfold_standard","ratio_ci95_lo","ratio_ci95_hi",
               "equivalence_band_lo","equivalence_band_hi"]
    for c in numeric:
        sweep[c] = pd.to_numeric(sweep[c], errors="coerce")

    bad = (sweep[["L","N","T","J","H"]].isna().any(axis=1) | (sweep["L"] <= 0) |
           (sweep["T"] <= 0) | (sweep["N"] != sweep["L"] * sweep["L"]))
    if bad.any():
        raise DataContractError("8B.4 found invalid physical context in temperature_sweep")

    key = ["dynamics", "H", "L", "J", "T"]
    dup = sweep.duplicated(subset=key, keep=False)
    if dup.any():
        raise DataContractError("8B.4 found duplicate temperature-sweep records")

    sweep["temperature_field_schema_version"] = TEMP_FIELD_SCHEMA_VERSION
    sweep["invT"] = 1.0 / sweep["T"]
    sweep["ratio_ci95_width_8b4"] = sweep["ratio_ci95_hi"] - sweep["ratio_ci95_lo"]
    sweep["abs_ratio_deviation_pct_8b4"] = 100.0 * (sweep["lifetime_ratio_nfold_standard"] - 1.0).abs()
    sweep["low_temperature_rank"] = sweep.groupby(["dynamics","H","L","J"])["T"].rank(method="dense")

    summary_rows = []
    group_cols = ["dynamics", "H", "L", "J"]
    for keys, g in sweep.groupby(group_cols, sort=True, dropna=False):
        dynamics, H, L, J = keys
        g = g.sort_values("T").reset_index(drop=True)
        if g["T"].nunique() < 2:
            raise DataContractError(f"8B.4 series has fewer than two temperatures: {keys}")
        statuses = g["equivalence_status_8b"].astype(str).str.upper()
        incon = g.loc[statuses == "INCONCLUSIVE", "T"]
        fail = g.loc[statuses == "FAIL", "T"]
        pass_t = g.loc[statuses == "PASS", "T"]

        summary_rows.append({
            "temperature_field_schema_version": TEMP_FIELD_SCHEMA_VERSION,
            "analysis_snapshot": snapshot_id,
            "dynamics": str(dynamics), "H": float(H), "L": int(L), "J": float(J),
            "T_count": int(g["T"].nunique()),
            "T_values": ";".join(f"{x:g}" for x in sorted(g["T"].unique())),
            "T_min": float(g["T"].min()), "T_max": float(g["T"].max()),
            "pass_count": int((statuses == "PASS").sum()),
            "inconclusive_count": int((statuses == "INCONCLUSIVE").sum()),
            "fail_count": int((statuses == "FAIL").sum()),
            "inconclusive_T_values": ";".join(f"{x:g}" for x in incon.tolist()),
            "fail_T_values": ";".join(f"{x:g}" for x in fail.tolist()),
            "lowest_pass_T": float(pass_t.min()) if len(pass_t) else np.nan,
            "max_abs_ratio_deviation_pct": float(g["abs_ratio_deviation_pct_8b4"].max()),
            "median_abs_ratio_deviation_pct": float(g["abs_ratio_deviation_pct_8b4"].median()),
            "max_ratio_ci95_width": float(g["ratio_ci95_width_8b4"].max()),
            "min_ratio_ci95_width": float(g["ratio_ci95_width_8b4"].min()),
            "ci_width_lowest_T": float(g.iloc[0]["ratio_ci95_width_8b4"]),
            "ci_width_highest_T": float(g.iloc[-1]["ratio_ci95_width_8b4"]),
            "tau_standard_lowest_T": float(g.iloc[0]["mean_tau_standard_mcss"]),
            "tau_nfold_lowest_T": float(g.iloc[0]["mean_tau_nfold_mcss"]),
            "runs_lowest_T": int(g.iloc[0]["runs"]),
            "temperature_robustness_status": _series_status(g),
        })

    summary = pd.DataFrame(summary_rows).sort_values(["dynamics","H"]).reset_index(drop=True)
    counts = summary["temperature_robustness_status"].value_counts()
    status_all = sweep["equivalence_status_8b"].astype(str).str.upper()

    diagnostics = pd.DataFrame([
        {"diagnostic":"analysis_snapshot", "value":snapshot_id},
        {"diagnostic":"temperature_records", "value":int(len(sweep))},
        {"diagnostic":"temperature_series", "value":int(len(summary))},
        {"diagnostic":"pass_records", "value":int((status_all == "PASS").sum())},
        {"diagnostic":"inconclusive_records", "value":int((status_all == "INCONCLUSIVE").sum())},
        {"diagnostic":"fail_records", "value":int((status_all == "FAIL").sum())},
        {"diagnostic":"robust_temperature_series", "value":int(counts.get("ROBUST_ACROSS_TESTED_T",0))},
        {"diagnostic":"inconclusive_temperature_series", "value":int(counts.get("INCONCLUSIVE_AT_SOME_T",0))},
        {"diagnostic":"discrepant_temperature_series", "value":int(counts.get("DISCREPANCY_AT_SOME_T",0))},
        {"diagnostic":"inconclusive_T_values", "value":";".join(f"{x:g}" for x in sorted(sweep.loc[status_all == "INCONCLUSIVE","T"].unique()))},
        {"diagnostic":"inconclusive_H_values", "value":";".join(f"{x:g}" for x in sorted(sweep.loc[status_all == "INCONCLUSIVE","H"].unique()))},
        {"diagnostic":"max_ratio_ci95_width", "value":float(sweep["ratio_ci95_width_8b4"].max())},
        {"diagnostic":"max_abs_ratio_deviation_pct", "value":float(sweep["abs_ratio_deviation_pct_8b4"].max())},
    ])

    return TemperatureFieldResult(
        records=sweep.sort_values(["dynamics","H","T"]).reset_index(drop=True),
        summary=summary,
        diagnostics=diagnostics,
    )
