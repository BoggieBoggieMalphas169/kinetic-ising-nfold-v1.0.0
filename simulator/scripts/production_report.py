#!/usr/bin/env python3
"""Generate a reproducible production-validation summary and plots.

Uses only Python stdlib for statistics; matplotlib is used only for optional figures.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Sample:
    dynamics: str
    H: float
    algorithm: str
    times: list[float]
    cpu: list[float]
    attempts: list[int]
    events: list[int]


def read_sample(path: Path) -> Sample:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    ok = [r for r in rows if r.get("reached_M0", "1") in {"1", "true", "True"}]
    if len(ok) != len(rows):
        raise ValueError(f"{path}: {len(rows)-len(ok)} unfinished escapes")
    r0 = ok[0]
    algorithm = r0["algorithm"]
    if algorithm == "standard":
        attempts = [int(r["attempts"]) for r in ok]
        events = [int(r["events"]) for r in ok]
    elif algorithm == "nfold":
        attempts = [int(r["equivalent_attempts"]) for r in ok]
        events = [int(r["events"]) for r in ok]
    else:
        raise ValueError(f"{path}: unknown algorithm {algorithm}")
    return Sample(
        dynamics=r0["dynamics"],
        H=float(r0["H"]),
        algorithm=algorithm,
        times=[float(r["time_mcss"]) for r in ok],
        cpu=[float(r["cpu_seconds"]) for r in ok],
        attempts=attempts,
        events=events,
    )


def percentile(v: list[float], q: float) -> float:
    x = sorted(v)
    pos = q * (len(x) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return x[lo]
    w = pos - lo
    return x[lo] * (1 - w) + x[hi] * w


def mean_ci(x: list[float]) -> tuple[float, float]:
    m = statistics.fmean(x)
    if len(x) < 2:
        return m, m
    se = statistics.stdev(x) / math.sqrt(len(x))
    return m - 1.96 * se, m + 1.96 * se


def bootstrap_ratio_ci(a: list[float], b: list[float], reps: int, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    out = []
    na, nb = len(a), len(b)
    for _ in range(reps):
        ma = sum(a[rng.randrange(na)] for _ in range(na)) / na
        mb = sum(b[rng.randrange(nb)] for _ in range(nb)) / nb
        out.append(mb / ma)
    return percentile(out, 0.025), percentile(out, 0.975)


def ks_statistic(a: list[float], b: list[float]) -> float:
    a, b = sorted(a), sorted(b)
    i = j = 0
    d = 0.0
    while i < len(a) or j < len(b):
        if j >= len(b) or (i < len(a) and a[i] <= b[j]):
            x = a[i]
        else:
            x = b[j]
        while i < len(a) and a[i] <= x:
            i += 1
        while j < len(b) and b[j] <= x:
            j += 1
        d = max(d, abs(i / len(a) - j / len(b)))
    return d


def ks_pvalue(d: float, na: int, nb: int) -> float:
    if d <= 0:
        return 1.0
    en = math.sqrt(na * nb / (na + nb))
    lam = (en + 0.12 + 0.11 / en) * d
    s = 0.0
    for k in range(1, 101):
        term = 2.0 * (-1.0 if k % 2 == 0 else 1.0) * math.exp(-2.0 * k * k * lam * lam)
        s += term
        if abs(term) < 1e-14:
            break
    return min(1.0, max(0.0, s))


def survival_xy(x: list[float]) -> tuple[list[float], list[float]]:
    xs = sorted(x)
    n = len(xs)
    tx = [0.0]
    sy = [1.0]
    for i, t in enumerate(xs, start=1):
        tx.append(t)
        sy.append((n - i) / n)
    return tx, sy


def fmt(x: float) -> str:
    return f"{x:.6g}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("results/production_report"))
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--margin", type=float, default=0.05)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    cases = [
        ("glauber", "Hm3p0", -3.0),
        ("glauber", "Hm0p75", -0.75),
        ("metropolis", "Hm3p0", -3.0),
        ("metropolis", "Hm0p75", -0.75),
    ]
    summaries = []
    samples: dict[tuple[str, float, str], Sample] = {}

    for idx, (dyn, tag, H) in enumerate(cases):
        std = read_sample(args.results / f"standard_{dyn}_{tag}.csv")
        nfd = read_sample(args.results / f"nfold_{dyn}_{tag}.csv")
        samples[(dyn, H, "standard")] = std
        samples[(dyn, H, "nfold")] = nfd
        ms, mn = statistics.fmean(std.times), statistics.fmean(nfd.times)
        cis = mean_ci(std.times)
        cin = mean_ci(nfd.times)
        ratio = mn / ms
        rlo, rhi = bootstrap_ratio_ci(std.times, nfd.times, args.bootstrap, args.seed + idx)
        d = ks_statistic(std.times, nfd.times)
        p = ks_pvalue(d, len(std.times), len(nfd.times))
        weighted_wait = sum(nfd.attempts) / sum(nfd.events)
        cpu_ratio = statistics.fmean(std.cpu) / statistics.fmean(nfd.cpu)
        summaries.append({
            "dynamics": dyn,
            "H": H,
            "n_standard": len(std.times),
            "n_nfold": len(nfd.times),
            "mean_standard_mcss": ms,
            "mean_standard_ci95_lo": cis[0],
            "mean_standard_ci95_hi": cis[1],
            "median_standard_mcss": statistics.median(std.times),
            "sd_standard_mcss": statistics.stdev(std.times),
            "mean_nfold_mcss": mn,
            "mean_nfold_ci95_lo": cin[0],
            "mean_nfold_ci95_hi": cin[1],
            "median_nfold_mcss": statistics.median(nfd.times),
            "sd_nfold_mcss": statistics.stdev(nfd.times),
            "ratio_nfold_standard": ratio,
            "ratio_bootstrap_ci95_lo": rlo,
            "ratio_bootstrap_ci95_hi": rhi,
            "ks_D": d,
            "ks_p": p,
            "equivalence_margin": args.margin,
            "equivalence_pass": rlo >= 1-args.margin and rhi <= 1+args.margin,
            "ks_pass_alpha_0p01": p >= 0.01,
            "nfold_weighted_mean_wait": weighted_wait,
            "mean_standard_attempts": statistics.fmean(std.attempts),
            "mean_nfold_equiv_attempts": statistics.fmean(nfd.attempts),
            "mean_nfold_events": statistics.fmean(nfd.events),
            "mean_per_run_cpu_ratio_std_over_nfold": cpu_ratio,
        })

    fields = list(summaries[0].keys())
    with (args.outdir / "validation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(summaries)

    md = []
    md.append("# Production validation — Prompt 6\n")
    md.append("This report compares standard random-site dynamic Monte Carlo with the discrete-time n-fold implementation.\n")
    md.append(f"Predeclared practical-equivalence margin used here: **±{100*args.margin:.1f}%** on the bootstrap 95% CI of the mean-lifetime ratio. KS is reported as a distributional diagnostic at alpha=0.01.\n")
    md.append("| Dynamics | H/J | mean tau std (MCSS) | mean tau n-fold (MCSS) | n-fold/std | 95% bootstrap CI | KS p | mean wait/event | Verdict |\n")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for s in summaries:
        verdict = "PASS" if s["equivalence_pass"] and s["ks_pass_alpha_0p01"] else "CHECK"
        md.append(
            f"| {s['dynamics'].title()} | {s['H']:g} | {fmt(s['mean_standard_mcss'])} | "
            f"{fmt(s['mean_nfold_mcss'])} | {fmt(s['ratio_nfold_standard'])} | "
            f"[{fmt(s['ratio_bootstrap_ci95_lo'])}, {fmt(s['ratio_bootstrap_ci95_hi'])}] | "
            f"{fmt(s['ks_p'])} | {fmt(s['nfold_weighted_mean_wait'])} | **{verdict}** |\n"
        )
    md.append("\n## Interpretation\n")
    md.append("All four comparisons must be interpreted statistically rather than trajectory-by-trajectory: the two algorithms consume random variates differently. A PASS here means the observed mean-lifetime ratio is tightly contained inside the declared equivalence band and the KS diagnostic does not flag a distributional discrepancy at alpha=0.01.\n")
    md.append("\nThe n-fold mean wait/event quantifies rejection compression: it is the average number of conventional attempted updates represented by one accepted n-fold event. This is an algorithmic quantity and is distinct from measured wall-clock speed-up.\n")
    (args.outdir / "production_validation.md").write_text("".join(md), encoding="utf-8")

    # Optional figures. Separate figures (no subplots) for portability and easy inclusion in reports.
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable; skipping figures: {exc}")
        return 0

    labels = [f"{s['dynamics'][0].upper()} H={s['H']:g}" for s in summaries]
    ratios = [s["ratio_nfold_standard"] for s in summaries]
    yerr_lo = [s["ratio_nfold_standard"] - s["ratio_bootstrap_ci95_lo"] for s in summaries]
    yerr_hi = [s["ratio_bootstrap_ci95_hi"] - s["ratio_nfold_standard"] for s in summaries]
    fig, ax = plt.subplots()
    ax.errorbar(range(len(ratios)), ratios, yerr=[yerr_lo, yerr_hi], fmt="o", capsize=4)
    ax.axhline(1.0, linestyle="--")
    ax.axhline(1.0-args.margin, linestyle=":")
    ax.axhline(1.0+args.margin, linestyle=":")
    ax.set_xticks(range(len(labels)), labels, rotation=20)
    ax.set_ylabel("Mean lifetime ratio: n-fold / standard")
    ax.set_title("Standard vs n-fold lifetime equivalence")
    fig.tight_layout()
    fig.savefig(args.outdir / "lifetime_ratio_ci.png", dpi=180)
    plt.close(fig)

    for dyn, _, H in cases:
        std = samples[(dyn, H, "standard")]
        nfd = samples[(dyn, H, "nfold")]
        txs, sys = survival_xy(std.times)
        txn, syn = survival_xy(nfd.times)
        fig, ax = plt.subplots()
        ax.step(txs, sys, where="post", label="standard")
        ax.step(txn, syn, where="post", label="n-fold")
        ax.set_xlabel("Escape time tau (MCSS)")
        ax.set_ylabel("Survival S(t) = P(tau > t)")
        ax.set_title(f"{dyn.title()}, H/J={H:g}")
        ax.legend()
        fig.tight_layout()
        safe_h = str(abs(H)).replace('.', 'p')
        fig.savefig(args.outdir / f"survival_{dyn}_Hm{safe_h}.png", dpi=180)
        plt.close(fig)

    waits = [s["nfold_weighted_mean_wait"] for s in summaries]
    fig, ax = plt.subplots()
    ax.bar(range(len(waits)), waits)
    ax.set_xticks(range(len(labels)), labels, rotation=20)
    ax.set_ylabel("Equivalent attempted updates per n-fold event")
    ax.set_title("n-fold rejection compression")
    fig.tight_layout()
    fig.savefig(args.outdir / "nfold_event_compression.png", dpi=180)
    plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
