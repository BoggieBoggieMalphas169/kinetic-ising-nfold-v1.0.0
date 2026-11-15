"""Prompt 8B.6: consolidate the physical Standard-vs-n-fold evidence.

This module does not introduce a new statistical test. It combines the already validated
8B.1--8B.5 outputs into a compact, machine-readable scientific conclusion while preserving
all precision limitations and avoiding any use of performance/speed-up as evidence of
physical equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .load_results import DataContractError

SYNTHESIS_SCHEMA_VERSION = "8B6.1"


@dataclass(frozen=True)
class PhysicalSynthesisResult:
    synthesis: pd.DataFrame
    limitations: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError(f"8B.6 {name} missing required columns: " + ", ".join(missing))


def _single_snapshot(*tables: pd.DataFrame) -> str:
    snapshots: set[str] = set()
    for df in tables:
        if "analysis_snapshot" in df.columns:
            snapshots.update(df["analysis_snapshot"].dropna().astype(str).unique())
    if len(snapshots) != 1:
        raise DataContractError("8B.6 requires exactly one shared analysis_snapshot")
    return next(iter(snapshots))


def synthesize_physical_comparison(
    equivalence_records: pd.DataFrame,
    campaign_summary: pd.DataFrame,
    size_summary: pd.DataFrame,
    temperature_summary: pd.DataFrame,
    dynamics_summary: pd.DataFrame,
    dynamics_pairs: pd.DataFrame,
) -> PhysicalSynthesisResult:
    _require_columns(equivalence_records, [
        "analysis_snapshot", "study", "dynamics", "H", "T", "L",
        "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
        "equivalence_status_8b",
    ], "8B.1 records")
    _require_columns(campaign_summary, [
        "analysis_snapshot", "campaign_reproducible", "campaign_consistency_status",
    ], "8B.2 summary")
    _require_columns(size_summary, [
        "analysis_snapshot", "size_robust", "size_robustness_status",
    ], "8B.3 summary")
    _require_columns(temperature_summary, [
        "analysis_snapshot", "dynamics", "H", "pass_count", "inconclusive_count",
        "fail_count", "inconclusive_T_values", "temperature_robustness_status",
    ], "8B.4 summary")
    _require_columns(dynamics_summary, [
        "analysis_snapshot", "dynamics", "pass_count", "inconclusive_count", "fail_count",
        "dynamics_equivalence_status",
    ], "8B.5 summary")
    _require_columns(dynamics_pairs, [
        "analysis_snapshot", "dynamic_contrast_preservation_abs_pct", "matched_pair_status",
    ], "8B.5 matched pairs")

    snapshot = _single_snapshot(
        equivalence_records, campaign_summary, size_summary,
        temperature_summary, dynamics_summary, dynamics_pairs,
    )

    eq = equivalence_records.copy()
    status = eq["equivalence_status_8b"].astype(str).str.upper()
    total = int(len(eq))
    pass_count = int((status == "PASS").sum())
    inconclusive_count = int((status == "INCONCLUSIVE").sum())
    fail_count = int((status == "FAIL").sum())

    if fail_count > 0:
        overall = "DISCREPANCY_DETECTED"
    elif inconclusive_count > 0:
        overall = "SUPPORTED_WITH_PRECISION_LIMITS"
    elif pass_count == total:
        overall = "SUPPORTED_ACROSS_TESTED_DOMAIN"
    else:
        overall = "REVIEW_REQUIRED"

    campaign_ok = bool(campaign_summary["campaign_reproducible"].astype(bool).all())
    size_ok = bool(size_summary["size_robust"].astype(bool).all())
    dyn_fail = int(pd.to_numeric(dynamics_summary["fail_count"], errors="coerce").fillna(0).sum())
    contrast_max = float(pd.to_numeric(
        dynamics_pairs["dynamic_contrast_preservation_abs_pct"], errors="coerce"
    ).max())
    contrast_within_5 = int((pd.to_numeric(
        dynamics_pairs["dynamic_contrast_preservation_abs_pct"], errors="coerce"
    ) <= 5.0).sum())

    synthesis = pd.DataFrame([{
        "synthesis_schema_version": SYNTHESIS_SCHEMA_VERSION,
        "analysis_snapshot": snapshot,
        "comparison_records": total,
        "pass_count": pass_count,
        "inconclusive_count": inconclusive_count,
        "fail_count": fail_count,
        "pass_fraction": pass_count / total if total else float("nan"),
        "unique_physical_points": int(eq["experiment_id"].nunique()) if "experiment_id" in eq.columns else pd.NA,
        "campaign_reproducible_points": int(campaign_summary["campaign_reproducible"].astype(bool).sum()),
        "campaign_repeated_points": int(len(campaign_summary)),
        "all_repeated_points_reproducible": campaign_ok,
        "size_series_robust": int(size_summary["size_robust"].astype(bool).sum()),
        "size_series_total": int(len(size_summary)),
        "all_size_series_robust": size_ok,
        "temperature_series_total": int(len(temperature_summary)),
        "temperature_series_with_precision_limits": int((temperature_summary["inconclusive_count"] > 0).sum()),
        "temperature_series_with_fail": int((temperature_summary["fail_count"] > 0).sum()),
        "dynamics_with_fail": dyn_fail,
        "matched_glauber_metropolis_points": int(len(dynamics_pairs)),
        "dynamic_contrast_within_5pct_count": contrast_within_5,
        "max_dynamic_contrast_preservation_abs_pct": contrast_max,
        "performance_used_as_equivalence_evidence": False,
        "overall_physical_conclusion": overall,
    }])

    limitations_rows = []
    inc = eq.loc[status == "INCONCLUSIVE"].copy()
    for _, r in inc.sort_values(["dynamics", "H", "T", "L"]).iterrows():
        limitations_rows.append({
            "synthesis_schema_version": SYNTHESIS_SCHEMA_VERSION,
            "analysis_snapshot": snapshot,
            "limitation_type": "STATISTICAL_PRECISION",
            "study": r.get("study", pd.NA),
            "dynamics": r.get("dynamics", pd.NA),
            "L": r.get("L", pd.NA),
            "T": r.get("T", pd.NA),
            "H": r.get("H", pd.NA),
            "lifetime_ratio_nfold_standard": r.get("lifetime_ratio_nfold_standard", pd.NA),
            "ratio_ci95_lo": r.get("ratio_ci95_lo", pd.NA),
            "ratio_ci95_hi": r.get("ratio_ci95_hi", pd.NA),
            "message": "Equivalence remains unresolved at the predefined ±5% margin with the available precision; this is not classified as a discrepancy.",
        })
    if not limitations_rows:
        limitations_rows.append({
            "synthesis_schema_version": SYNTHESIS_SCHEMA_VERSION,
            "analysis_snapshot": snapshot,
            "limitation_type": "NONE_DETECTED_IN_TESTED_DOMAIN",
            "study": pd.NA, "dynamics": pd.NA, "L": pd.NA, "T": pd.NA, "H": pd.NA,
            "lifetime_ratio_nfold_standard": pd.NA, "ratio_ci95_lo": pd.NA, "ratio_ci95_hi": pd.NA,
            "message": "No unresolved equivalence points in the tested domain.",
        })
    limitations = pd.DataFrame(limitations_rows)

    diagnostics = pd.DataFrame([
        {"diagnostic": "analysis_snapshot", "value": snapshot},
        {"diagnostic": "overall_physical_conclusion", "value": overall},
        {"diagnostic": "comparison_records", "value": total},
        {"diagnostic": "pass_count", "value": pass_count},
        {"diagnostic": "inconclusive_count", "value": inconclusive_count},
        {"diagnostic": "fail_count", "value": fail_count},
        {"diagnostic": "all_repeated_points_reproducible", "value": campaign_ok},
        {"diagnostic": "all_size_series_robust", "value": size_ok},
        {"diagnostic": "dynamic_contrast_within_5pct_count", "value": contrast_within_5},
        {"diagnostic": "matched_glauber_metropolis_points", "value": int(len(dynamics_pairs))},
        {"diagnostic": "performance_used_as_equivalence_evidence", "value": False},
    ])

    return PhysicalSynthesisResult(synthesis=synthesis, limitations=limitations, diagnostics=diagnostics)
