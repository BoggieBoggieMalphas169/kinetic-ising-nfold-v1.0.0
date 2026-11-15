"""Aggregate canonical run-level Ising results without mixing clock semantics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .statistics import mean_ci


GROUP_COLUMNS = ["algorithm", "dynamics", "L", "N", "T", "J", "H"]


def _add_stats(out: dict[str, object], prefix: str, series: pd.Series) -> None:
    stats = mean_ci(series)
    out[f"n_{prefix}"] = stats["n"]
    out[f"mean_{prefix}"] = stats["mean"]
    out[f"median_{prefix}"] = stats["median"]
    out[f"sd_{prefix}"] = stats["sd"]
    out[f"sem_{prefix}"] = stats["sem"]
    out[f"{prefix}_ci95_lo"] = stats["ci_lo"]
    out[f"{prefix}_ci95_hi"] = stats["ci_hi"]


def aggregate_runs(runs: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in GROUP_COLUMNS + ["time_mcss"] if c not in runs.columns]
    if missing:
        raise ValueError(f"Canonical run table is missing columns: {missing}")

    rows: list[dict[str, object]] = []
    grouped = runs.groupby(GROUP_COLUMNS, dropna=False, sort=True)

    for key, group in grouped:
        row = dict(zip(GROUP_COLUMNS, key, strict=True))
        row["runs"] = int(len(group))
        row["source_files"] = ";".join(sorted(set(group["source_file"].dropna().astype(str))))

        _add_stats(row, "tau_mcss", group["time_mcss"])

        optional_metrics = {
            "equivalent_attempts": "equiv_attempts",
            "attempts": "attempts",
            "events": "events",
            "accepted": "accepted",
            "acceptance_rate": "acceptance_rate",
            "final_E": "final_E",
            "final_M": "final_M",
            "cpu_seconds": "cpu_seconds",
        }
        for column, prefix in optional_metrics.items():
            if column in group and pd.to_numeric(group[column], errors="coerce").notna().any():
                _add_stats(row, prefix, pd.to_numeric(group[column], errors="coerce"))

        if "reached_M0" in group:
            reached = group["reached_M0"].dropna()
            row["reached_M0_fraction"] = float(reached.astype(float).mean()) if len(reached) else np.nan

        if row["algorithm"] == "nfold":
            events = pd.to_numeric(group["events"], errors="coerce")
            equiv = pd.to_numeric(group["equivalent_attempts"], errors="coerce")
            valid = events.notna() & equiv.notna() & (events > 0)
            row["mean_equiv_attempts_per_event"] = (
                float((equiv[valid] / events[valid]).mean()) if valid.any() else np.nan
            )
        else:
            row["mean_equiv_attempts_per_event"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows).sort_values(GROUP_COLUMNS, ignore_index=True)
