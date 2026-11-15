"""Prompt 8B.2: cross-campaign reproducibility at repeated physical points.

The same physical point can appear in validation, L-scalability and temperature-sweep
campaigns.  Those records are not duplicates: they are independent campaign-level
measurements.  This module checks whether their Standard-vs-n-fold lifetime conclusions
are internally consistent without pooling them into a new pseudo-sample.

Primary reproducibility diagnostics are deliberately descriptive and audit-friendly:

* all campaigns preserve the same practical-equivalence status;
* bootstrap confidence intervals for R_tau overlap pairwise;
* the intervals share a common intersection (stronger descriptive check);
* campaign-to-campaign spans of the Standard and n-fold mean lifetimes are reported.

No CPU/speed-up quantity enters the reproducibility decision; those belong to Prompt 8C.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd

from .load_results import DataContractError

CAMPAIGN_CONSISTENCY_SCHEMA_VERSION = "8B2.1"

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
    "ratio_ci95_lo",
    "ratio_ci95_hi",
    "equivalence_status_8b",
)


@dataclass(frozen=True)
class CampaignConsistencyResult:
    repeated_records: pd.DataFrame
    point_summary: pd.DataFrame
    pairwise: pd.DataFrame
    diagnostics: pd.DataFrame


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataContractError(f"8B.2 missing required columns: {', '.join(missing)}")


def _relative_span_pct(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return float("nan")
    mean = float(np.mean(x))
    if mean == 0.0:
        return float("nan")
    return 100.0 * float(np.max(x) - np.min(x)) / abs(mean)


def _interval_overlap(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> tuple[bool, float, float]:
    lo = max(float(lo_a), float(lo_b))
    hi = min(float(hi_a), float(hi_b))
    return lo <= hi, lo, hi


def _status_for_group(group: pd.DataFrame, common_overlap: bool, all_pairwise_overlap: bool) -> str:
    statuses = set(group["equivalence_status_8b"].astype(str).str.upper())
    if statuses == {"PASS"} and common_overlap and all_pairwise_overlap:
        return "CONSISTENT_ACROSS_CAMPAIGNS"
    if "FAIL" in statuses:
        return "CROSS_CAMPAIGN_DISCREPANCY_PRESENT"
    if statuses != {"PASS"}:
        return "MIXED_OR_INCONCLUSIVE_ACROSS_CAMPAIGNS"
    if not common_overlap:
        return "PASS_BUT_NO_COMMON_RATIO_CI_INTERSECTION"
    if not all_pairwise_overlap:
        return "PASS_BUT_PAIRWISE_RATIO_CI_TENSION"
    return "REVIEW_REQUIRED"


def analyze_campaign_consistency(records: pd.DataFrame) -> CampaignConsistencyResult:
    """Analyze physical points measured in at least two distinct campaigns.

    Parameters
    ----------
    records:
        Output of Prompt 8B.1 (`physical_equivalence_8B1.csv` or the equivalent
        in-memory dataframe). Every row must come from one frozen 8A.21 snapshot.
    """
    _require_columns(records, _REQUIRED)
    if records.empty:
        raise DataContractError("8B.2 cannot analyze an empty 8B.1 table")

    df = records.copy()
    snapshots = df["analysis_snapshot"].dropna().astype(str).unique().tolist()
    if len(snapshots) != 1:
        raise DataContractError("8B.2 requires exactly one analysis_snapshot")
    snapshot_id = snapshots[0]

    for col in (
        "L", "N", "T", "J", "H",
        "mean_tau_standard_mcss", "mean_tau_nfold_mcss",
        "lifetime_ratio_nfold_standard", "ratio_ci95_lo", "ratio_ci95_hi",
    ):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["experiment_id"].isna().any():
        raise DataContractError("8B.2 requires a valid experiment_id for every row")

    study_counts = df.groupby("experiment_id")["study"].transform("nunique")
    repeated = df.loc[study_counts >= 2].copy()
    if repeated.empty:
        raise DataContractError("8B.2 found no physical point repeated across campaigns")

    # A campaign should contribute at most one comparison for a given physical point.
    dup = repeated.duplicated(subset=["experiment_id", "study"], keep=False)
    if dup.any():
        examples = repeated.loc[dup, ["experiment_id", "study"]].drop_duplicates().head(5)
        raise DataContractError(
            "8B.2 found duplicate records within the same campaign for repeated points: "
            + examples.astype(str).agg("/".join, axis=1).str.cat(sep=", ")
        )

    # Add a stable count and retain the original 8B.1 evidence untouched.
    repeated["campaign_count"] = repeated.groupby("experiment_id")["study"].transform("nunique")
    repeated["campaign_consistency_schema_version"] = CAMPAIGN_CONSISTENCY_SCHEMA_VERSION

    pair_rows: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []

    for experiment_id, group in repeated.groupby("experiment_id", sort=True):
        group = group.sort_values("study").reset_index(drop=True)
        identity_cols = ["dynamics", "L", "N", "T", "J", "H"]
        for col in identity_cols:
            if group[col].nunique(dropna=False) != 1:
                raise DataContractError(f"8B.2 inconsistent physical key for {experiment_id}: {col}")

        pair_overlaps: list[bool] = []
        for ia, ib in combinations(range(len(group)), 2):
            a, b = group.iloc[ia], group.iloc[ib]
            overlap, overlap_lo, overlap_hi = _interval_overlap(
                a["ratio_ci95_lo"], a["ratio_ci95_hi"], b["ratio_ci95_lo"], b["ratio_ci95_hi"]
            )
            pair_overlaps.append(overlap)
            std_ref = 0.5 * (float(a["mean_tau_standard_mcss"]) + float(b["mean_tau_standard_mcss"]))
            nf_ref = 0.5 * (float(a["mean_tau_nfold_mcss"]) + float(b["mean_tau_nfold_mcss"]))
            pair_rows.append({
                "campaign_consistency_schema_version": CAMPAIGN_CONSISTENCY_SCHEMA_VERSION,
                "analysis_snapshot": snapshot_id,
                "experiment_id": experiment_id,
                "dynamics": a["dynamics"],
                "L": int(a["L"]),
                "N": int(a["N"]),
                "T": float(a["T"]),
                "J": float(a["J"]),
                "H": float(a["H"]),
                "study_a": str(a["study"]),
                "study_b": str(b["study"]),
                "ratio_a": float(a["lifetime_ratio_nfold_standard"]),
                "ratio_b": float(b["lifetime_ratio_nfold_standard"]),
                "ratio_difference_b_minus_a": float(b["lifetime_ratio_nfold_standard"] - a["lifetime_ratio_nfold_standard"]),
                "abs_ratio_difference_percentage_points": 100.0 * abs(float(b["lifetime_ratio_nfold_standard"] - a["lifetime_ratio_nfold_standard"])),
                "ratio_ci_overlap": bool(overlap),
                "ratio_ci_overlap_lo": overlap_lo,
                "ratio_ci_overlap_hi": overlap_hi,
                "standard_tau_pair_relative_difference_pct": (
                    100.0 * abs(float(b["mean_tau_standard_mcss"] - a["mean_tau_standard_mcss"])) / abs(std_ref)
                    if std_ref != 0.0 else np.nan
                ),
                "nfold_tau_pair_relative_difference_pct": (
                    100.0 * abs(float(b["mean_tau_nfold_mcss"] - a["mean_tau_nfold_mcss"])) / abs(nf_ref)
                    if nf_ref != 0.0 else np.nan
                ),
                "same_equivalence_status": str(a["equivalence_status_8b"]) == str(b["equivalence_status_8b"]),
            })

        common_lo = float(group["ratio_ci95_lo"].max())
        common_hi = float(group["ratio_ci95_hi"].min())
        common_overlap = common_lo <= common_hi
        common_contains_one = common_overlap and common_lo <= 1.0 <= common_hi
        all_pairwise = bool(all(pair_overlaps))
        statuses = sorted(set(group["equivalence_status_8b"].astype(str).str.upper()))
        status = _status_for_group(group, common_overlap, all_pairwise)

        point_rows.append({
            "campaign_consistency_schema_version": CAMPAIGN_CONSISTENCY_SCHEMA_VERSION,
            "analysis_snapshot": snapshot_id,
            "experiment_id": experiment_id,
            "dynamics": str(group["dynamics"].iloc[0]),
            "L": int(group["L"].iloc[0]),
            "N": int(group["N"].iloc[0]),
            "T": float(group["T"].iloc[0]),
            "J": float(group["J"].iloc[0]),
            "H": float(group["H"].iloc[0]),
            "campaign_count": int(group["study"].nunique()),
            "studies": ";".join(sorted(group["study"].astype(str).unique())),
            "equivalence_statuses": ";".join(statuses),
            "all_campaigns_pass": statuses == ["PASS"],
            "ratio_min": float(group["lifetime_ratio_nfold_standard"].min()),
            "ratio_max": float(group["lifetime_ratio_nfold_standard"].max()),
            "ratio_span_percentage_points": 100.0 * float(
                group["lifetime_ratio_nfold_standard"].max() - group["lifetime_ratio_nfold_standard"].min()
            ),
            "max_abs_ratio_deviation_from_one_pct": 100.0 * float(
                (group["lifetime_ratio_nfold_standard"] - 1.0).abs().max()
            ),
            "common_ratio_ci_lo": common_lo,
            "common_ratio_ci_hi": common_hi,
            "common_ratio_ci_nonempty": bool(common_overlap),
            "common_ratio_ci_contains_one": bool(common_contains_one),
            "all_pairwise_ratio_ci_overlap": all_pairwise,
            "standard_tau_campaign_span_pct": _relative_span_pct(group["mean_tau_standard_mcss"]),
            "nfold_tau_campaign_span_pct": _relative_span_pct(group["mean_tau_nfold_mcss"]),
            "campaign_reproducible": status == "CONSISTENT_ACROSS_CAMPAIGNS",
            "campaign_consistency_status": status,
        })

    point_summary = pd.DataFrame(point_rows).sort_values(["dynamics", "H"]).reset_index(drop=True)
    pairwise = pd.DataFrame(pair_rows).sort_values(["dynamics", "H", "study_a", "study_b"]).reset_index(drop=True)

    status_counts = point_summary["campaign_consistency_status"].value_counts()
    diagnostics = pd.DataFrame([
        {"diagnostic": "analysis_snapshot", "value": snapshot_id},
        {"diagnostic": "repeated_campaign_records", "value": int(len(repeated))},
        {"diagnostic": "repeated_physical_points", "value": int(point_summary["experiment_id"].nunique())},
        {"diagnostic": "consistent_points", "value": int(status_counts.get("CONSISTENT_ACROSS_CAMPAIGNS", 0))},
        {"diagnostic": "mixed_or_inconclusive_points", "value": int(status_counts.get("MIXED_OR_INCONCLUSIVE_ACROSS_CAMPAIGNS", 0))},
        {"diagnostic": "cross_campaign_discrepancy_points", "value": int(status_counts.get("CROSS_CAMPAIGN_DISCREPANCY_PRESENT", 0))},
        {"diagnostic": "points_with_common_ratio_ci_intersection", "value": int(point_summary["common_ratio_ci_nonempty"].sum())},
        {"diagnostic": "points_common_ratio_ci_contains_one", "value": int(point_summary["common_ratio_ci_contains_one"].sum())},
        {"diagnostic": "pairwise_ratio_ci_comparisons", "value": int(len(pairwise))},
        {"diagnostic": "pairwise_ratio_ci_nonoverlap_count", "value": int((~pairwise["ratio_ci_overlap"]).sum())},
        {"diagnostic": "max_ratio_span_percentage_points", "value": float(point_summary["ratio_span_percentage_points"].max())},
        {"diagnostic": "max_standard_tau_campaign_span_pct", "value": float(point_summary["standard_tau_campaign_span_pct"].max())},
        {"diagnostic": "max_nfold_tau_campaign_span_pct", "value": float(point_summary["nfold_tau_campaign_span_pct"].max())},
    ])

    return CampaignConsistencyResult(
        repeated_records=repeated.sort_values(["dynamics", "H", "study"]).reset_index(drop=True),
        point_summary=point_summary,
        pairwise=pairwise,
        diagnostics=diagnostics,
    )
