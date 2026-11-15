#!/usr/bin/env python3
"""Compare standard and n-fold metastable lifetime samples without third-party packages."""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from pathlib import Path


def read_times(path: Path) -> list[float]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: no data rows")
    vals = []
    for row in rows:
        if row.get("reached_M0", "1") not in {"1", "true", "True"}:
            continue
        vals.append(float(row["time_mcss"]))
    if not vals:
        raise ValueError(f"{path}: no completed M=0 escapes")
    return vals


def summary(x: list[float]) -> dict[str, float]:
    return {
        "n": float(len(x)),
        "mean": statistics.fmean(x),
        "median": statistics.median(x),
        "stdev": statistics.stdev(x) if len(x) > 1 else 0.0,
    }


def ks_statistic(a: list[float], b: list[float]) -> float:
    a = sorted(a)
    b = sorted(b)
    i = j = 0
    na, nb = len(a), len(b)
    d = 0.0
    while i < na or j < nb:
        if j >= nb or (i < na and a[i] <= b[j]):
            x = a[i]
        else:
            x = b[j]
        while i < na and a[i] <= x:
            i += 1
        while j < nb and b[j] <= x:
            j += 1
        d = max(d, abs(i / na - j / nb))
    return d


def ks_pvalue_asymptotic(d: float, na: int, nb: int) -> float:
    if d <= 0.0:
        return 1.0
    en = math.sqrt(na * nb / (na + nb))
    lam = (en + 0.12 + 0.11 / en) * d
    s = 0.0
    for k in range(1, 101):
        term = 2.0 * ((-1.0) ** (k - 1)) * math.exp(-2.0 * k * k * lam * lam)
        s += term
        if abs(term) < 1e-14:
            break
    return min(1.0, max(0.0, s))


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("empty percentile")
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    w = pos - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def bootstrap_ratio_ci(
    standard: list[float],
    nfold: list[float],
    reps: int,
    seed: int,
) -> tuple[float, float]:
    rng = random.Random(seed)
    ratios: list[float] = []
    ns, nn = len(standard), len(nfold)
    for _ in range(reps):
        ms = sum(standard[rng.randrange(ns)] for _ in range(ns)) / ns
        mn = sum(nfold[rng.randrange(nn)] for _ in range(nn)) / nn
        if ms > 0.0:
            ratios.append(mn / ms)
    ratios.sort()
    return percentile(ratios, 0.025), percentile(ratios, 0.975)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("standard_csv", type=Path)
    ap.add_argument("nfold_csv", type=Path)
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument(
        "--equivalence-margin",
        type=float,
        default=0.20,
        help="practical relative margin around ratio 1 used by --assert-equivalent",
    )
    ap.add_argument("--ks-alpha", type=float, default=0.01)
    ap.add_argument("--assert-equivalent", action="store_true")
    args = ap.parse_args()

    s = read_times(args.standard_csv)
    n = read_times(args.nfold_csv)
    ss, sn = summary(s), summary(n)
    ratio = sn["mean"] / ss["mean"]
    d = ks_statistic(s, n)
    p = ks_pvalue_asymptotic(d, len(s), len(n))
    lo, hi = bootstrap_ratio_ci(s, n, args.bootstrap, args.seed)

    print("Lifetime comparison (MCSS)")
    print(f"standard: n={len(s)} mean={ss['mean']:.8g} median={ss['median']:.8g} sd={ss['stdev']:.8g}")
    print(f"n-fold:   n={len(n)} mean={sn['mean']:.8g} median={sn['median']:.8g} sd={sn['stdev']:.8g}")
    print(f"mean ratio nfold/standard = {ratio:.8g}")
    print(f"bootstrap 95% CI ratio    = [{lo:.8g}, {hi:.8g}]")
    print(f"two-sample KS D           = {d:.8g}")
    print(f"KS asymptotic p           = {p:.8g}")

    margin = args.equivalence_margin
    practical = lo >= 1.0 - margin and hi <= 1.0 + margin
    distribution_ok = p >= args.ks_alpha
    print(f"practical-equivalence CI within ±{100*margin:.1f}%: {'PASS' if practical else 'NOT ESTABLISHED'}")
    print(f"KS diagnostic p >= {args.ks_alpha:g}: {'PASS' if distribution_ok else 'FLAG'}")

    if args.assert_equivalent and not (practical and distribution_ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
