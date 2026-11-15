"""Statistical utilities for independent runs and correlated Monte Carlo series."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd


def finite_values(values) -> np.ndarray:
    arr = np.asarray(values, dtype=float).ravel()
    return arr[np.isfinite(arr)]


def mean_ci(values, confidence: float = 0.95) -> dict[str, float | int]:
    """Descriptive statistics and a normal-approximation CI for independent runs.

    The result is intended for replicate-level quantities (e.g. one lifetime per
    independently seeded escape), not raw autocorrelated time-series samples.
    """
    x = finite_values(values)
    n = int(x.size)
    if n == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "sd": np.nan, "sem": np.nan,
                "ci_lo": np.nan, "ci_hi": np.nan}

    mean = float(np.mean(x))
    median = float(np.median(x))
    if n == 1:
        return {"n": 1, "mean": mean, "median": median, "sd": np.nan, "sem": np.nan,
                "ci_lo": np.nan, "ci_hi": np.nan}

    sd = float(np.std(x, ddof=1))
    sem = sd / np.sqrt(n)
    alpha = 1.0 - confidence
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    half = z * sem
    return {"n": n, "mean": mean, "median": median, "sd": sd, "sem": float(sem),
            "ci_lo": float(mean - half), "ci_hi": float(mean + half)}


def bootstrap_mean_ci(
    values,
    confidence: float = 0.95,
    n_resamples: int = 10_000,
    seed: int = 17_031,
) -> tuple[float, float]:
    """Deterministic percentile-bootstrap CI for the mean of independent replicates."""
    x = finite_values(values)
    if x.size < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples, dtype=float)
    # Chunked loop avoids allocating an n_resamples x n matrix for large campaigns.
    for i in range(n_resamples):
        means[i] = np.mean(rng.choice(x, size=x.size, replace=True))
    alpha = 1.0 - confidence
    lo, hi = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lo), float(hi)


def blocking_table(values, min_blocks: int = 8) -> pd.DataFrame:
    """Return blocking/binning diagnostics for a correlated scalar series.

    Each row uses non-overlapping blocks of size 1, 2, 4, ... and reports the
    standard error of the block means. This does *not* automatically choose a
    plateau; it provides the evidence needed for the later uncertainty block.
    """
    x = finite_values(values)
    rows: list[dict[str, float | int]] = []
    block_size = 1

    while block_size <= x.size:
        n_blocks = x.size // block_size
        if n_blocks < min_blocks:
            break
        trimmed = x[: n_blocks * block_size]
        block_means = trimmed.reshape(n_blocks, block_size).mean(axis=1)
        sd_blocks = float(np.std(block_means, ddof=1)) if n_blocks > 1 else np.nan
        sem = sd_blocks / np.sqrt(n_blocks) if n_blocks > 1 else np.nan
        rows.append(
            {
                "block_size": block_size,
                "n_blocks": n_blocks,
                "mean": float(np.mean(block_means)),
                "sd_block_means": sd_blocks,
                "sem_blocked": sem,
            }
        )
        block_size *= 2

    return pd.DataFrame(rows)
