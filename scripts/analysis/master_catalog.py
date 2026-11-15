"""Prompt 8A.20 master experiment catalog and coverage diagnostics.

This module works exclusively at the *comparison-summary* level.  It never treats an
aggregate Prompt 6 row as a raw Monte Carlo run.

Two complementary products are built:

* ``master_comparisons``: one row per observed Standard-vs-n-fold comparison record,
  augmented with deterministic IDs and catalog diagnostics.
* ``experiment_catalog``: one row per unique physical point
  (dynamics, L, N, T, J, H), independent of which campaign measured it.

A versioned experiment-design sidecar can additionally define the points expected in each
campaign.  Coverage is then classified as observed, missing, duplicate-within-study, or
unexpected.  The same physical point appearing in several campaigns is deliberately
classified as a *cross-study overlap*, not as an error.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from .contracts import COMPARISON_SUMMARY
from .load_results import DataContractError

MASTER_SCHEMA_VERSION = "8A20.1"
DESIGN_SCHEMA_VERSION = "8A20-design-v1"

PHYSICAL_KEY_FIELDS = ("dynamics", "L", "N", "T", "J", "H")
REQUIRED_PHYSICAL_FIELDS = ("dynamics", "L", "T", "J", "H")


@dataclass(frozen=True)
class CatalogResults:
    master_comparisons: pd.DataFrame
    experiment_catalog: pd.DataFrame
    coverage_detail: pd.DataFrame
    coverage_summary: pd.DataFrame
    missing_experiments: pd.DataFrame
    duplicate_experiments: pd.DataFrame
    unexpected_experiments: pd.DataFrame


def _is_missing(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _canonical_number(value: object) -> str:
    """Stable textual representation for IDs and exact catalog matching."""
    if _is_missing(value):
        raise DataContractError("Cannot canonicalize a missing physical parameter")
    x = float(value)
    if not np.isfinite(x):
        raise DataContractError(f"Physical parameter must be finite, got {value!r}")
    if x == 0.0:
        x = 0.0  # collapse -0.0 and +0.0
    return format(x, ".12g")


def _canonical_int(value: object, field: str) -> str:
    if _is_missing(value):
        raise DataContractError(f"Cannot canonicalize missing {field}")
    x = float(value)
    if not np.isfinite(x) or not x.is_integer():
        raise DataContractError(f"{field} must be an integer, got {value!r}")
    return str(int(x))


def canonical_physical_key(row: Mapping[str, object] | pd.Series) -> str:
    dynamics = str(row["dynamics"]).strip().lower()
    if not dynamics or dynamics in {"nan", "<na>"}:
        raise DataContractError("dynamics is missing")
    return "|".join(
        [
            f"dynamics={dynamics}",
            f"L={_canonical_int(row['L'], 'L')}",
            f"N={_canonical_int(row['N'], 'N')}",
            f"T={_canonical_number(row['T'])}",
            f"J={_canonical_number(row['J'])}",
            f"H={_canonical_number(row['H'])}",
        ]
    )


def experiment_id_from_key(key: str) -> str:
    return "exp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def comparison_id_for_row(row: Mapping[str, object] | pd.Series) -> str:
    experiment_id = str(row["experiment_id"])
    pieces = [
        experiment_id,
        str(row.get("study", "")).strip(),
        str(row.get("source_file", "")).strip(),
        str(row.get("source_row", "")).strip(),
    ]
    payload = "|".join(pieces)
    return "cmp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _physical_context_complete(row: pd.Series) -> bool:
    return all(not _is_missing(row.get(field, pd.NA)) for field in REQUIRED_PHYSICAL_FIELDS)


def _validate_and_prepare_comparisons(comparisons: pd.DataFrame) -> pd.DataFrame:
    if comparisons.empty:
        return comparisons.copy()

    out = comparisons.copy().reset_index(drop=True)
    required_meta = {"study", "record_level", "source_file", "source_row"}
    missing = required_meta.difference(out.columns)
    if missing:
        raise DataContractError(
            "Comparison table is missing catalog metadata columns: " + ", ".join(sorted(missing))
        )

    bad_level = out["record_level"].astype("string") != COMPARISON_SUMMARY
    if bad_level.fillna(True).any():
        values = sorted(set(out.loc[bad_level.fillna(True), "record_level"].astype(str)))
        raise DataContractError(
            f"8A.20 only accepts record_level={COMPARISON_SUMMARY!r}; found {values}"
        )

    # Ensure all physical columns exist, but preserve partial historical rows as partial.
    for field in PHYSICAL_KEY_FIELDS:
        if field not in out.columns:
            out[field] = pd.NA

    # Derive N only when L is known. Never guess L from N.
    mask_n_missing = out["N"].isna() & out["L"].notna()
    out.loc[mask_n_missing, "N"] = pd.to_numeric(out.loc[mask_n_missing, "L"], errors="coerce") ** 2

    complete_flags: list[bool] = []
    keys: list[object] = []
    ids: list[object] = []
    for _, row in out.iterrows():
        complete = _physical_context_complete(row) and not _is_missing(row.get("N", pd.NA))
        complete_flags.append(complete)
        if not complete:
            keys.append(pd.NA)
            ids.append(pd.NA)
            continue

        # Validate lattice identity before assigning a stable physical ID.
        L = float(row["L"])
        N = float(row["N"])
        if not L.is_integer() or L <= 0:
            raise DataContractError(f"L must be a positive integer, got {row['L']!r}")
        if not N.is_integer() or int(N) != int(L) ** 2:
            raise DataContractError(
                f"Catalog row has N != L^2: L={row['L']!r}, N={row['N']!r}"
            )
        if float(row["T"]) <= 0:
            raise DataContractError(f"T must be positive, got {row['T']!r}")

        key = canonical_physical_key(row)
        keys.append(key)
        ids.append(experiment_id_from_key(key))

    out["physical_context_complete"] = pd.Series(complete_flags, dtype="boolean")
    out["physical_key"] = pd.Series(keys, dtype="string")
    out["experiment_id"] = pd.Series(ids, dtype="string")

    complete = out["physical_context_complete"].fillna(False)
    out["within_study_count"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out["cross_study_count"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if complete.any():
        complete_df = out.loc[complete]
        within = complete_df.groupby(["study", "experiment_id"], dropna=False)["experiment_id"].transform("size")
        cross = complete_df.groupby("experiment_id", dropna=False)["study"].transform("nunique")
        out.loc[complete, "within_study_count"] = within.astype("Int64")
        out.loc[complete, "cross_study_count"] = cross.astype("Int64")

    out["duplicate_within_study"] = (out["within_study_count"] > 1).fillna(False).astype("boolean")
    out["cross_study_overlap"] = (out["cross_study_count"] > 1).fillna(False).astype("boolean")

    comparison_ids: list[object] = []
    for _, row in out.iterrows():
        if not bool(row["physical_context_complete"]):
            comparison_ids.append(pd.NA)
        else:
            comparison_ids.append(comparison_id_for_row(row))
    out["comparison_id"] = pd.Series(comparison_ids, dtype="string")

    out["catalog_status"] = "observed"
    out.loc[~complete, "catalog_status"] = "partial_context"
    out.loc[out["duplicate_within_study"].fillna(False), "catalog_status"] = "duplicate_within_study"
    out["analysis_ready"] = (
        complete & ~out["duplicate_within_study"].fillna(False)
    ).astype("boolean")
    out["master_schema_version"] = MASTER_SCHEMA_VERSION
    return out


def load_experiment_design(path: str | Path | None) -> dict[str, object]:
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise DataContractError(
            f"Experiment design {p} has schema_version={payload.get('schema_version')!r}; "
            f"expected {DESIGN_SCHEMA_VERSION!r}"
        )
    studies = payload.get("studies")
    if not isinstance(studies, dict):
        raise DataContractError("Experiment design must contain a 'studies' object")
    return payload


def _normalize_design_point(study: str, point: Mapping[str, object]) -> dict[str, object]:
    missing = set(REQUIRED_PHYSICAL_FIELDS).difference(point)
    if missing:
        raise DataContractError(
            f"Design study {study!r} is missing fields: {', '.join(sorted(missing))}"
        )
    row = dict(point)
    row["study"] = study
    L = float(row["L"])
    if not L.is_integer() or L <= 0:
        raise DataContractError(f"Design study {study!r}: L must be a positive integer")
    expected_n = int(L) ** 2
    if "N" in row and not _is_missing(row["N"]):
        supplied_n = float(row["N"])
        if not supplied_n.is_integer() or int(supplied_n) != expected_n:
            raise DataContractError(
                f"Design study {study!r}: N={row['N']!r} conflicts with L^2={expected_n}"
            )
    row["L"] = int(L)
    row["N"] = expected_n
    row["T"] = float(row["T"])
    row["J"] = float(row["J"])
    row["H"] = float(row["H"])
    row["dynamics"] = str(row["dynamics"]).strip().lower()
    if row["T"] <= 0:
        raise DataContractError(f"Design study {study!r}: T must be positive")
    row["physical_key"] = canonical_physical_key(row)
    row["experiment_id"] = experiment_id_from_key(row["physical_key"])
    return row


def expand_experiment_design(payload: Mapping[str, object]) -> pd.DataFrame:
    """Expand Cartesian parameter grids or explicit point lists into expected rows."""
    if not payload:
        return pd.DataFrame(
            columns=["study", *PHYSICAL_KEY_FIELDS, "physical_key", "experiment_id"]
        )

    rows: list[dict[str, object]] = []
    studies = payload.get("studies", {})
    assert isinstance(studies, Mapping)
    for study, spec_obj in studies.items():
        if not isinstance(spec_obj, Mapping):
            raise DataContractError(f"Design study {study!r} must be an object")
        spec = dict(spec_obj)
        if "points" in spec:
            points = spec["points"]
            if not isinstance(points, list):
                raise DataContractError(f"Design study {study!r}: 'points' must be a list")
            for point in points:
                if not isinstance(point, Mapping):
                    raise DataContractError(f"Design study {study!r}: each point must be an object")
                rows.append(_normalize_design_point(str(study), point))
            continue

        parameters = spec.get("parameters")
        if not isinstance(parameters, Mapping):
            raise DataContractError(
                f"Design study {study!r} must contain either 'parameters' or 'points'"
            )
        missing = set(REQUIRED_PHYSICAL_FIELDS).difference(parameters)
        if missing:
            raise DataContractError(
                f"Design study {study!r} parameter grid is missing: {', '.join(sorted(missing))}"
            )
        fields = list(REQUIRED_PHYSICAL_FIELDS)
        value_lists: list[list[object]] = []
        for field in fields:
            values = parameters[field]
            if not isinstance(values, list) or not values:
                raise DataContractError(
                    f"Design study {study!r}: parameter {field!r} must be a non-empty list"
                )
            value_lists.append(values)
        for combo in itertools.product(*value_lists):
            rows.append(_normalize_design_point(str(study), dict(zip(fields, combo))))

    expected = pd.DataFrame(rows)
    if expected.empty:
        return expected
    duplicated = expected.duplicated(["study", "experiment_id"], keep=False)
    if duplicated.any():
        dup = expected.loc[duplicated, ["study", "physical_key"]]
        raise DataContractError(
            "Experiment design contains duplicate expected points: "
            + "; ".join(f"{r.study}: {r.physical_key}" for r in dup.itertuples())
        )
    return expected.sort_values(["study", "dynamics", "H", "T", "L"]).reset_index(drop=True)


def _build_experiment_catalog(master: pd.DataFrame) -> pd.DataFrame:
    complete = master[master["physical_context_complete"].fillna(False)].copy()
    if complete.empty:
        return pd.DataFrame(
            columns=[
                "master_schema_version",
                "experiment_id",
                "physical_key",
                *PHYSICAL_KEY_FIELDS,
                "comparison_records",
                "study_count",
                "studies",
                "source_files",
                "cross_study_overlap",
                "duplicate_within_study_any",
                "analysis_ready_records",
            ]
        )

    rows: list[dict[str, object]] = []
    for experiment_id, group in complete.groupby("experiment_id", sort=True):
        first = group.iloc[0]
        rows.append(
            {
                "master_schema_version": MASTER_SCHEMA_VERSION,
                "experiment_id": experiment_id,
                "physical_key": first["physical_key"],
                **{field: first[field] for field in PHYSICAL_KEY_FIELDS},
                "comparison_records": int(len(group)),
                "study_count": int(group["study"].nunique()),
                "studies": ";".join(sorted(map(str, group["study"].dropna().unique()))),
                "source_files": ";".join(sorted(map(str, group["source_file"].dropna().unique()))),
                "cross_study_overlap": bool(group["study"].nunique() > 1),
                "duplicate_within_study_any": bool(group["duplicate_within_study"].fillna(False).any()),
                "analysis_ready_records": int(group["analysis_ready"].fillna(False).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["dynamics", "H", "T", "L"], kind="stable"
    ).reset_index(drop=True)


def _coverage_products(
    master: pd.DataFrame,
    expected: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    detail_cols = [
        "study",
        "experiment_id",
        "physical_key",
        *PHYSICAL_KEY_FIELDS,
        "observed_records",
        "coverage_status",
    ]
    if expected.empty:
        empty = pd.DataFrame(columns=detail_cols)
        summary = pd.DataFrame(
            columns=[
                "study",
                "expected_points",
                "observed_expected_points",
                "missing_points",
                "duplicate_expected_points",
                "unexpected_points",
                "coverage_fraction",
            ]
        )
        return empty, summary, empty.copy(), empty.copy(), empty.copy()

    complete = master[master["physical_context_complete"].fillna(False)].copy()
    counts = (
        complete.groupby(["study", "experiment_id"], dropna=False)
        .size()
        .rename("observed_records")
        .reset_index()
    )
    detail = expected.merge(counts, on=["study", "experiment_id"], how="left")
    detail["observed_records"] = detail["observed_records"].fillna(0).astype(int)
    detail["coverage_status"] = np.select(
        [detail["observed_records"] == 0, detail["observed_records"] > 1],
        ["missing", "duplicate"],
        default="observed",
    )
    detail = detail[detail_cols]

    expected_keys = set(zip(expected["study"].astype(str), expected["experiment_id"].astype(str)))
    unexpected_mask = complete.apply(
        lambda r: (str(r["study"]), str(r["experiment_id"])) not in expected_keys,
        axis=1,
    )
    unexpected = complete.loc[
        unexpected_mask,
        ["study", "experiment_id", "physical_key", *PHYSICAL_KEY_FIELDS],
    ].drop_duplicates(["study", "experiment_id"])
    if not unexpected.empty:
        unexpected = unexpected.assign(observed_records=1, coverage_status="unexpected")
        unexpected = unexpected[detail_cols]
    else:
        unexpected = pd.DataFrame(columns=detail_cols)

    missing = detail[detail["coverage_status"] == "missing"].copy()
    duplicate = detail[detail["coverage_status"] == "duplicate"].copy()

    summary_rows: list[dict[str, object]] = []
    all_studies = sorted(set(expected["study"].astype(str)) | set(complete["study"].astype(str)))
    for study in all_studies:
        d = detail[detail["study"].astype(str) == study]
        u = unexpected[unexpected["study"].astype(str) == study]
        expected_n = int(len(d))
        observed_expected = int((d["observed_records"] >= 1).sum())
        summary_rows.append(
            {
                "study": study,
                "expected_points": expected_n,
                "observed_expected_points": observed_expected,
                "missing_points": int((d["coverage_status"] == "missing").sum()),
                "duplicate_expected_points": int((d["coverage_status"] == "duplicate").sum()),
                "unexpected_points": int(len(u)),
                "coverage_fraction": (observed_expected / expected_n) if expected_n else np.nan,
            }
        )
    summary = pd.DataFrame(summary_rows)
    return detail, summary, missing, duplicate, unexpected


def build_master_catalog(
    comparisons: pd.DataFrame,
    design: Mapping[str, object] | None = None,
) -> CatalogResults:
    master = _validate_and_prepare_comparisons(comparisons)
    expected = expand_experiment_design(design or {})

    if not expected.empty and not master.empty:
        expected_keys = set(zip(expected["study"].astype(str), expected["experiment_id"].astype(str)))
        design_status: list[str] = []
        for _, row in master.iterrows():
            if not bool(row["physical_context_complete"]):
                design_status.append("partial_context")
            elif (str(row["study"]), str(row["experiment_id"])) in expected_keys:
                design_status.append("expected")
            else:
                design_status.append("unexpected")
        master["design_status"] = design_status
    else:
        master["design_status"] = "not_checked"

    catalog = _build_experiment_catalog(master)
    detail, summary, missing, duplicate, unexpected = _coverage_products(master, expected)

    preferred = [
        "master_schema_version",
        "comparison_id",
        "experiment_id",
        "physical_key",
        "physical_context_complete",
        "catalog_status",
        "design_status",
        "analysis_ready",
        "duplicate_within_study",
        "cross_study_overlap",
        "within_study_count",
        "cross_study_count",
    ]
    master = master[[c for c in preferred if c in master.columns] + [c for c in master.columns if c not in preferred]]
    return CatalogResults(master, catalog, detail, summary, missing, duplicate, unexpected)


def load_comparison_tables(paths: Iterable[str | Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path_like in paths:
        path = Path(path_like)
        if not path.exists():
            raise DataContractError(f"Comparison input does not exist: {path}")
        frame = pd.read_csv(path)
        frame["catalog_input_file"] = path.as_posix()
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)
