"""Load and normalize raw Ising simulation CSV files.

The analysis layer deliberately uses a canonical *run-level* schema so that the
standard random-update Monte Carlo and the n-fold implementation can be analysed
with the same downstream code without erasing their different clock semantics.

Raw files are never modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


class DataContractError(ValueError):
    """Raised when a raw result file violates the analysis data contract."""


CANONICAL_COLUMNS = [
    "algorithm",
    "dynamics",
    "run",
    "L",
    "N",
    "T",
    "J",
    "H",
    "seed",
    "stream",
    "time_mcss",
    "attempts",
    "equivalent_attempts",
    "events",
    "accepted",
    "acceptance_rate",
    "final_M",
    "final_E",
    "reached_M0",
    "cpu_seconds",
    "source_file",
]

# Aliases are intentionally conservative: they cover names already used in the
# project and obvious future variants, while avoiding ambiguous remappings.
ALIASES: dict[str, tuple[str, ...]] = {
    "algorithm": ("algorithm", "algo", "method"),
    "dynamics": ("dynamics", "dynamic", "rule"),
    "run": ("run", "replica", "replicate", "trial"),
    "L": ("L", "l", "linear_size"),
    "N": ("N", "n_spins", "spins"),
    "T": ("T", "temperature", "temp"),
    "J": ("J", "coupling"),
    "H": ("H", "field", "magnetic_field"),
    "seed": ("seed", "rng_seed"),
    "stream": ("stream", "rng_stream"),
    "time_mcss": ("time_mcss", "mcss", "tau_mcss", "lifetime_mcss"),
    "attempts": ("attempts", "mcs", "spin_attempts"),
    "equivalent_attempts": (
        "equivalent_attempts",
        "equiv_attempts",
        "attempts_equiv",
        "nfold_equiv_attempts",
    ),
    "events": ("events", "n_events", "nfold_events", "accepted_events"),
    "accepted": ("accepted", "accepted_flips", "n_accepted"),
    "acceptance_rate": ("acceptance_rate", "acceptance_fraction", "acceptance"),
    "final_M": ("final_M", "M_final", "final_magnetization"),
    "final_E": ("final_E", "E_final", "final_energy"),
    "reached_M0": ("reached_M0", "reached_m0", "escaped", "success"),
    "cpu_seconds": ("cpu_seconds", "cpu_s", "elapsed_seconds", "wall_seconds"),
}

NUMERIC_COLUMNS = [
    "run",
    "L",
    "N",
    "T",
    "J",
    "H",
    "seed",
    "stream",
    "time_mcss",
    "attempts",
    "equivalent_attempts",
    "events",
    "accepted",
    "acceptance_rate",
    "final_M",
    "final_E",
    "cpu_seconds",
]


@dataclass(frozen=True)
class LoadedResults:
    runs: pd.DataFrame
    manifest: pd.DataFrame


def _first_present(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lookup = {str(c).lower(): str(c) for c in columns}
    for candidate in candidates:
        hit = lookup.get(candidate.lower())
        if hit is not None:
            return hit
    return None


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for canonical, candidates in ALIASES.items():
        present = _first_present(df.columns, candidates)
        if present is not None and present != canonical and canonical not in df.columns:
            rename[present] = canonical
    return df.rename(columns=rename)


def _infer_algorithm(path: Path, df: pd.DataFrame) -> str:
    if "algorithm" in df.columns:
        values = df["algorithm"].dropna().astype(str).str.lower().unique()
        if len(values) == 1:
            value = values[0]
            if "nfold" in value or "n-fold" in value or "n_fold" in value:
                return "nfold"
            if "standard" in value or "metropolis" in value or "glauber" in value:
                return "standard"

    token = str(path).lower().replace("-", "_")
    if "nfold" in token or "n_fold" in token:
        return "nfold"
    if "standard" in token or "conventional" in token:
        return "standard"

    cols = {str(c).lower() for c in df.columns}
    if cols.intersection({"equivalent_attempts", "equiv_attempts", "nfold_events", "mean_wait"}):
        return "nfold"
    if "attempts" in cols and ("accepted" in cols or "acceptance_rate" in cols):
        return "standard"

    raise DataContractError(
        f"Cannot infer algorithm for {path}. Add an 'algorithm' column or place "
        "the file below results/raw/standard or results/raw/nfold."
    )


def _coerce_bool(series: pd.Series) -> pd.Series:
    true_values = {"1", "true", "t", "yes", "y", "pass"}
    false_values = {"0", "false", "f", "no", "n", "fail"}

    def convert(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        key = str(value).strip().lower()
        if key in true_values:
            return True
        if key in false_values:
            return False
        raise DataContractError(f"Cannot interpret boolean value {value!r}")

    return series.map(convert).astype("boolean")


def _normalize_one(path: Path, raw_root: Path | None = None) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas provides details
        raise DataContractError(f"Could not read CSV {path}: {exc}") from exc

    if df.empty:
        raise DataContractError(f"Raw result file is empty: {path}")

    df = _canonicalize_columns(df)
    algorithm = _infer_algorithm(path, df)
    df["algorithm"] = algorithm

    required = {"L", "T", "J", "H", "time_mcss"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise DataContractError(f"{path} is missing required columns: {missing}")

    if "N" not in df.columns:
        df["N"] = pd.to_numeric(df["L"], errors="coerce") ** 2

    # Preserve the two clocks. For the conventional algorithm, attempts are also
    # the natural equivalent-attempt count. For n-fold we never pretend that one
    # rejection-free event is one attempted spin update.
    if algorithm == "standard":
        if "attempts" not in df.columns:
            df["attempts"] = pd.to_numeric(df["time_mcss"], errors="coerce") * pd.to_numeric(
                df["N"], errors="coerce"
            )
        if "equivalent_attempts" not in df.columns:
            df["equivalent_attempts"] = df["attempts"]
    else:
        if "equivalent_attempts" not in df.columns:
            # time_mcss * N is the represented attempted-update time for the
            # discrete/continuum n-fold clocks used in this project.
            df["equivalent_attempts"] = pd.to_numeric(df["time_mcss"], errors="coerce") * pd.to_numeric(
                df["N"], errors="coerce"
            )
        if "attempts" not in df.columns:
            df["attempts"] = np.nan

    if "run" not in df.columns:
        df["run"] = np.arange(len(df), dtype=int)

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "reached_M0" in df.columns:
        df["reached_M0"] = _coerce_bool(df["reached_M0"])

    L = pd.to_numeric(df["L"], errors="coerce")
    N = pd.to_numeric(df["N"], errors="coerce")
    bad_lattice = L.notna() & N.notna() & ~np.isclose(N, L * L)
    if bad_lattice.any():
        indices = df.index[bad_lattice].tolist()[:5]
        raise DataContractError(f"{path}: N != L^2 in rows {indices}")

    if (pd.to_numeric(df["T"], errors="coerce") <= 0).any():
        raise DataContractError(f"{path}: temperature T must be positive")

    if (pd.to_numeric(df["time_mcss"], errors="coerce") < 0).any():
        raise DataContractError(f"{path}: time_mcss cannot be negative")

    if "acceptance_rate" in df.columns:
        rate = pd.to_numeric(df["acceptance_rate"], errors="coerce")
        invalid_rate = rate.notna() & ((rate < 0) | (rate > 1))
        if invalid_rate.any():
            raise DataContractError(f"{path}: acceptance_rate must lie in [0, 1]")

    try:
        source = str(path.relative_to(raw_root)) if raw_root else str(path)
    except ValueError:
        source = str(path)
    df["source_file"] = source.replace("\\", "/")

    # Missing optional fields stay explicit rather than being silently fabricated.
    for column in CANONICAL_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    return df[CANONICAL_COLUMNS].copy()


def discover_csv_files(raw_root: str | Path) -> list[Path]:
    root = Path(raw_root)
    if not root.exists():
        raise FileNotFoundError(f"Raw results directory does not exist: {root}")
    files = sorted(p for p in root.rglob("*.csv") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No CSV files found below {root}")
    return files


def load_raw_results(raw_root: str | Path) -> LoadedResults:
    """Load every raw CSV below *raw_root* and return canonical run data + provenance."""
    root = Path(raw_root)
    frames: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, object]] = []

    for path in discover_csv_files(root):
        normalized = _normalize_one(path, raw_root=root)
        frames.append(normalized)
        manifest_rows.append(
            {
                "source_file": normalized["source_file"].iloc[0],
                "algorithm": normalized["algorithm"].iloc[0],
                "rows": len(normalized),
                "L_values": ";".join(map(str, sorted(normalized["L"].dropna().unique()))),
                "T_values": ";".join(map(str, sorted(normalized["T"].dropna().unique()))),
                "H_values": ";".join(map(str, sorted(normalized["H"].dropna().unique()))),
            }
        )

    # Concatenate column-wise to preserve the canonical schema without relying on
    # pandas' deprecated all-NA dtype inference across heterogeneous raw files.
    runs = pd.DataFrame(
        {column: pd.concat([frame[column] for frame in frames], ignore_index=True)
         for column in CANONICAL_COLUMNS}
    )
    manifest = pd.DataFrame(manifest_rows).sort_values("source_file", ignore_index=True)
    return LoadedResults(runs=runs, manifest=manifest)
