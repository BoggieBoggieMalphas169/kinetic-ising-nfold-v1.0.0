"""Prompt 8C: performance analysis for Standard MC versus n-fold.

Physical equivalence is assumed to have been assessed independently in Prompt 8B.
This module analyzes computational cost only; speed-up is never used as evidence of
physical equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import math

import numpy as np
import pandas as pd

from .load_results import DataContractError

PERFORMANCE_SCHEMA_VERSION = "8C.1"


@dataclass(frozen=True)
class PerformanceResult:
    records: pd.DataFrame
    temperature: pd.DataFrame
    size: pd.DataFrame
    synthesis: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError("8C missing required columns: " + ", ".join(missing))


def _single_snapshot(df: pd.DataFrame) -> str:
    if "analysis_snapshot" in df.columns:
        vals = df["analysis_snapshot"].dropna().astype(str).unique()
    elif "snapshot_id" in df.columns:
        vals = df["snapshot_id"].dropna().astype(str).unique()
    else:
        # master_comparisons predates the 8B analysis_snapshot field; its parent
        # snapshot is attached by the CLI after verification.
        vals = []
    if len(vals) > 1:
        raise DataContractError("8C requires exactly one analysis snapshot")
    return vals[0] if len(vals) == 1 else "UNSPECIFIED"


def _loglinear_crossover(T: np.ndarray, S: np.ndarray):
    order = np.argsort(T)
    T, S = T[order], S[order]
    for t1, s1, t2, s2 in zip(T[:-1], S[:-1], T[1:], S[1:]):
        if not (np.isfinite(s1) and np.isfinite(s2)) or s1 <= 0 or s2 <= 0:
            continue
        if (s1 - 1.0) * (s2 - 1.0) <= 0 and s1 != s2:
            y1, y2 = math.log(s1), math.log(s2)
            if y2 == y1:
                return float((t1 + t2) / 2), float(t1), float(t2)
            tc = t1 + (0.0 - y1) * (t2 - t1) / (y2 - y1)
            return float(tc), float(t1), float(t2)
    return math.nan, math.nan, math.nan


def analyze_performance(master: pd.DataFrame, analysis_snapshot: str) -> PerformanceResult:
    req = [
        "study", "dynamics", "H", "L", "N", "T", "J",
        "cpu_standard_s_per_escape", "cpu_nfold_s_per_escape",
        "speedup_standard_over_nfold", "mean_standard_attempts_per_escape",
        "mean_nfold_equiv_attempts_per_escape", "mean_nfold_events_per_escape",
        "nfold_equiv_attempts_per_event",
    ]
    _require_columns(master, req)
    if not analysis_snapshot or analysis_snapshot == "UNSPECIFIED":
        raise DataContractError("8C requires an explicit verified analysis_snapshot")

    df = master.copy()
    numeric = [c for c in req if c not in {"study", "dynamics"}]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["speedup_standard_over_nfold"].notna()].copy()
    if df.empty:
        raise DataContractError("8C found no performance records")
    if (df["speedup_standard_over_nfold"] <= 0).any():
        raise DataContractError("8C speed-up must be positive")
    if (df["nfold_equiv_attempts_per_event"] <= 0).any():
        raise DataContractError("8C event compression must be positive")

    df.insert(0, "performance_schema_version", PERFORMANCE_SCHEMA_VERSION)
    df.insert(1, "analysis_snapshot", analysis_snapshot)
    df["performance_winner"] = np.where(
        df["speedup_standard_over_nfold"] > 1.0, "NFOLD_FASTER",
        np.where(df["speedup_standard_over_nfold"] < 1.0, "STANDARD_FASTER", "BREAK_EVEN")
    )
    df["standard_advantage_over_nfold"] = 1.0 / df["speedup_standard_over_nfold"]

    # Mechanistic decomposition when elementary CPU costs are available.
    if {"standard_cpu_ns_per_attempt", "nfold_cpu_ns_per_event"}.issubset(df.columns):
        df["event_cost_ratio_nfold_over_standard"] = (
            pd.to_numeric(df["nfold_cpu_ns_per_event"], errors="coerce") /
            pd.to_numeric(df["standard_cpu_ns_per_attempt"], errors="coerce")
        )
        df["standard_to_nfold_equiv_attempt_ratio"] = (
            df["mean_standard_attempts_per_escape"] /
            df["mean_nfold_equiv_attempts_per_escape"]
        )
        df["break_even_compression"] = (
            df["event_cost_ratio_nfold_over_standard"] /
            df["standard_to_nfold_equiv_attempt_ratio"]
        )
        df["mechanistic_speedup"] = (
            df["nfold_equiv_attempts_per_event"] *
            df["standard_to_nfold_equiv_attempt_ratio"] /
            df["event_cost_ratio_nfold_over_standard"]
        )
        df["mechanistic_speedup_rel_error"] = (
            (df["mechanistic_speedup"] - df["speedup_standard_over_nfold"]).abs() /
            df["speedup_standard_over_nfold"]
        )
    else:
        for c in ["event_cost_ratio_nfold_over_standard", "standard_to_nfold_equiv_attempt_ratio",
                  "break_even_compression", "mechanistic_speedup", "mechanistic_speedup_rel_error"]:
            df[c] = np.nan

    if "standard_acceptance_fraction" in df.columns:
        acc = pd.to_numeric(df["standard_acceptance_fraction"], errors="coerce")
        df["inverse_standard_acceptance"] = 1.0 / acc
        df["compression_over_inverse_acceptance"] = (
            df["nfold_equiv_attempts_per_event"] / df["inverse_standard_acceptance"]
        )
    else:
        df["inverse_standard_acceptance"] = np.nan
        df["compression_over_inverse_acceptance"] = np.nan

    # 8C temperature/field campaign only: avoids counting repeated campaign points.
    tdf = df[df["study"] == "temperature_sweep"].copy()
    temp_rows = []
    if not tdf.empty:
        if tdf.duplicated(["dynamics", "H", "T"]).any():
            raise DataContractError("8C temperature_sweep has duplicate dynamics/H/T records")
        for (dyn, H), g in tdf.groupby(["dynamics", "H"], sort=True):
            g = g.sort_values("T")
            S = g["speedup_standard_over_nfold"].to_numpy(float)
            T = g["T"].to_numpy(float)
            tc, tlo, thi = _loglinear_crossover(T, S)
            if np.all(S > 1):
                regime = "NFOLD_FASTER_ACROSS_TESTED_T"
            elif np.all(S < 1):
                regime = "STANDARD_FASTER_ACROSS_TESTED_T"
            else:
                regime = "CROSSOVER_WITHIN_TESTED_T"
            acc_rel = pd.to_numeric(g["compression_over_inverse_acceptance"], errors="coerce")
            temp_rows.append({
                "performance_schema_version": PERFORMANCE_SCHEMA_VERSION,
                "analysis_snapshot": analysis_snapshot,
                "dynamics": dyn, "H": H,
                "T_min": float(T.min()), "T_max": float(T.max()), "points": int(len(g)),
                "speedup_min": float(S.min()), "speedup_max": float(S.max()),
                "nfold_faster_points": int((S > 1).sum()),
                "standard_faster_points": int((S < 1).sum()),
                "performance_regime": regime,
                "crossover_T_loglinear": tc,
                "crossover_bracket_T_lo": tlo,
                "crossover_bracket_T_hi": thi,
                "compression_min": float(g["nfold_equiv_attempts_per_event"].min()),
                "compression_max": float(g["nfold_equiv_attempts_per_event"].max()),
                "event_cost_ratio_median": float(pd.to_numeric(g["event_cost_ratio_nfold_over_standard"], errors="coerce").median()),
                "break_even_compression_median": float(pd.to_numeric(g["break_even_compression"], errors="coerce").median()),
                "compression_vs_inverse_acceptance_max_rel_dev": float((acc_rel - 1.0).abs().max()) if acc_rel.notna().any() else np.nan,
            })
    temperature = pd.DataFrame(temp_rows)

    # 8C finite-size performance campaign.
    sdf = df[df["study"] == "scalability_L"].copy()
    size_rows = []
    if not sdf.empty:
        if sdf.duplicated(["dynamics", "H", "L"]).any():
            raise DataContractError("8C scalability_L has duplicate dynamics/H/L records")
        for (dyn, H), g in sdf.groupby(["dynamics", "H"], sort=True):
            g = g.sort_values("L")
            x = np.log(g["L"].to_numpy(float))
            def slope(col):
                y = np.log(g[col].to_numpy(float))
                return float(np.polyfit(x, y, 1)[0])
            S = g["speedup_standard_over_nfold"].to_numpy(float)
            size_rows.append({
                "performance_schema_version": PERFORMANCE_SCHEMA_VERSION,
                "analysis_snapshot": analysis_snapshot,
                "dynamics": dyn, "H": H,
                "L_min": int(g["L"].min()), "L_max": int(g["L"].max()), "points": int(len(g)),
                "standard_cpu_scaling_exponent_vs_L": slope("cpu_standard_s_per_escape"),
                "nfold_cpu_scaling_exponent_vs_L": slope("cpu_nfold_s_per_escape"),
                "speedup_scaling_exponent_vs_L": slope("speedup_standard_over_nfold"),
                "speedup_geometric_mean": float(np.exp(np.mean(np.log(S)))),
                "speedup_at_L_min": float(S[0]), "speedup_at_L_max": float(S[-1]),
                "speedup_ratio_Lmax_over_Lmin": float(S[-1] / S[0]),
                "performance_winner_all_L": "NFOLD" if np.all(S > 1) else ("STANDARD" if np.all(S < 1) else "MIXED"),
            })
    size = pd.DataFrame(size_rows)

    # Synthesis uses designated campaigns rather than pooling repeated points as iid data.
    temp_max_idx = tdf["speedup_standard_over_nfold"].idxmax() if not tdf.empty else None
    temp_min_idx = tdf["speedup_standard_over_nfold"].idxmin() if not tdf.empty else None
    maxrow = tdf.loc[temp_max_idx] if temp_max_idx is not None else None
    minrow = tdf.loc[temp_min_idx] if temp_min_idx is not None else None
    mechanistic_err = pd.to_numeric(df["mechanistic_speedup_rel_error"], errors="coerce")
    compression_accept_dev = pd.to_numeric(tdf["compression_over_inverse_acceptance"], errors="coerce") if not tdf.empty else pd.Series(dtype=float)

    synthesis = pd.DataFrame([{
        "performance_schema_version": PERFORMANCE_SCHEMA_VERSION,
        "analysis_snapshot": analysis_snapshot,
        "performance_records": int(len(df)),
        "temperature_records": int(len(tdf)),
        "size_records": int(len(sdf)),
        "temperature_nfold_faster_count": int((tdf["speedup_standard_over_nfold"] > 1).sum()),
        "temperature_standard_faster_count": int((tdf["speedup_standard_over_nfold"] < 1).sum()),
        "max_speedup": float(maxrow["speedup_standard_over_nfold"]) if maxrow is not None else np.nan,
        "max_speedup_dynamics": maxrow["dynamics"] if maxrow is not None else pd.NA,
        "max_speedup_H": float(maxrow["H"]) if maxrow is not None else np.nan,
        "max_speedup_T": float(maxrow["T"]) if maxrow is not None else np.nan,
        "min_speedup": float(minrow["speedup_standard_over_nfold"]) if minrow is not None else np.nan,
        "min_speedup_dynamics": minrow["dynamics"] if minrow is not None else pd.NA,
        "min_speedup_H": float(minrow["H"]) if minrow is not None else np.nan,
        "min_speedup_T": float(minrow["T"]) if minrow is not None else np.nan,
        "max_standard_advantage": float(1.0 / minrow["speedup_standard_over_nfold"]) if minrow is not None else np.nan,
        "max_event_compression_temperature_sweep": float(tdf["nfold_equiv_attempts_per_event"].max()) if not tdf.empty else np.nan,
        "median_event_cost_ratio_nfold_over_standard": float(pd.to_numeric(df["event_cost_ratio_nfold_over_standard"], errors="coerce").median()),
        "max_mechanistic_speedup_relative_error": float(mechanistic_err.max()) if mechanistic_err.notna().any() else np.nan,
        "max_compression_inverse_acceptance_relative_deviation": float((compression_accept_dev - 1.0).abs().max()) if compression_accept_dev.notna().any() else np.nan,
        "performance_used_as_physical_equivalence_evidence": False,
        "overall_performance_conclusion": "REGIME_DEPENDENT",
    }])

    diagnostics = pd.DataFrame([
        {"diagnostic": "analysis_snapshot", "value": analysis_snapshot},
        {"diagnostic": "performance_records", "value": int(len(df))},
        {"diagnostic": "temperature_records", "value": int(len(tdf))},
        {"diagnostic": "size_records", "value": int(len(sdf))},
        {"diagnostic": "performance_used_as_physical_equivalence_evidence", "value": False},
        {"diagnostic": "temperature_campaign_is_primary_for_T_H_conclusions", "value": True},
        {"diagnostic": "scalability_campaign_is_primary_for_L_conclusions", "value": True},
    ])
    return PerformanceResult(df, temperature, size, synthesis, diagnostics)
