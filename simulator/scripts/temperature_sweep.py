#!/usr/bin/env python3
"""Prompt 6 final stage: temperature sweep at fixed lattice size.

Purpose
-------
1. Verify that standard random-site dynamic Monte Carlo and the discrete-time
   n-fold way remain statistically equivalent over a temperature range.
2. Quantify how rejection removal changes the computational cost as T varies.
3. Produce reproducible CSV summaries and figures suitable for the report.

The default grid stays below the zero-field 2D Ising critical temperature and
uses L=32, matching the production validation. The two lowest temperatures use
smaller ensembles because weak-field standard Monte Carlo becomes much more
expensive there; the ensemble size is recorded in every output row.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import subprocess
from pathlib import Path

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from scipy.stats import ks_2samp
except Exception:  # pragma: no cover
    ks_2samp = None


def ftag(x: float) -> str:
    sign = "m" if x < 0 else "p"
    return sign + (f"{abs(x):g}".replace(".", "p"))


def run_count(T: float, H: float, default_runs: int, cold_runs: int, cold_threshold: float,
              weak_T08_runs: int, weak_T09_runs: int, weak_T10_runs: int) -> int:
    # Adaptive production ensemble.  Weak-field low-T lifetimes have very broad
    # tails, so T=0.9 and 1.0 receive much larger ensembles while T=0.8 remains
    # deliberately precision-limited because conventional MC is extremely costly.
    if abs(H) < 2.0:
        if T <= 0.80 + 1e-12:
            return weak_T08_runs
        if T <= 0.90 + 1e-12:
            return weak_T09_runs
        if T <= 1.00 + 1e-12:
            return weak_T10_runs
    return cold_runs if T <= cold_threshold + 1e-12 else default_runs


def run_one(exe: Path, out: Path, *, L: int, T: float, J: float, H: float,
            runs: int, seed: int, dynamics: str) -> None:
    cmd = [str(exe), "--L", str(L), "--T", str(T), "--J", str(J),
           "--H", str(H), "--runs", str(runs), "--seed", str(seed),
           "--dynamics", dynamics, "--output", str(out)]
    subprocess.run(cmd, check=True)


def read_csv(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"{path}: empty CSV")
    if any(r.get("reached_M0") not in {"1", "true", "True"} for r in rows):
        raise RuntimeError(f"{path}: unfinished escape detected")
    alg = rows[0]["algorithm"]
    tau = [float(r["time_mcss"]) for r in rows]
    cpu = [float(r["cpu_seconds"]) for r in rows]
    accepted = [int(r["accepted"]) for r in rows]
    if alg == "standard":
        attempts = [int(r["attempts"]) for r in rows]
        events = [int(r["events"]) for r in rows]
    else:
        attempts = [int(r["equivalent_attempts"]) for r in rows]
        events = [int(r["events"]) for r in rows]
    return {
        "rows": rows, "algorithm": alg, "tau": tau, "cpu": cpu,
        "attempts": attempts, "events": events, "accepted": accepted,
    }


def percentile(v, q: float) -> float:
    x = sorted(float(z) for z in v)
    p = q * (len(x) - 1)
    lo, hi = math.floor(p), math.ceil(p)
    if lo == hi:
        return x[lo]
    w = p - lo
    return x[lo] * (1 - w) + x[hi] * w


def ratio_bootstrap_ci(a, b, reps: int, seed: int) -> tuple[float, float]:
    """Percentile bootstrap CI for mean(b)/mean(a)."""
    if np is not None:
        aa = np.asarray(a, dtype=float)
        bb = np.asarray(b, dtype=float)
        rng = np.random.default_rng(seed)
        vals = []
        left = reps
        chunk = min(1000, reps)
        while left:
            m = min(chunk, left)
            ia = rng.integers(0, len(aa), size=(m, len(aa)))
            ib = rng.integers(0, len(bb), size=(m, len(bb)))
            vals.append(bb[ib].mean(axis=1) / aa[ia].mean(axis=1))
            left -= m
        rr = np.concatenate(vals)
        return float(np.quantile(rr, 0.025)), float(np.quantile(rr, 0.975))
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        ma = sum(a[rng.randrange(len(a))] for _ in a) / len(a)
        mb = sum(b[rng.randrange(len(b))] for _ in b) / len(b)
        out.append(mb / ma)
    return percentile(out, 0.025), percentile(out, 0.975)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def arrhenius_fit(rows: list[dict], *, algorithm_key: str, Tmax: float) -> dict:
    """Empirical ln(<tau>) = intercept + Gamma_eff/T fit over T <= Tmax."""
    pts = [r for r in rows if r["T"] <= Tmax and r[algorithm_key] > 0]
    x = [1.0 / r["T"] for r in pts]
    y = [math.log(r[algorithm_key]) for r in pts]
    if len(x) < 3:
        return {"slope_Gamma_eff": float("nan"), "intercept": float("nan"),
                "r2": float("nan"), "npoints": len(x)}
    if np is not None:
        xx = np.asarray(x); yy = np.asarray(y)
        slope, intercept = np.polyfit(xx, yy, 1)
        pred = slope * xx + intercept
        ss_res = float(np.sum((yy - pred) ** 2))
        ss_tot = float(np.sum((yy - yy.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        return {"slope_Gamma_eff": float(slope), "intercept": float(intercept),
                "r2": r2, "npoints": len(x)}
    mx, my = statistics.fmean(x), statistics.fmean(y)
    den = sum((z - mx) ** 2 for z in x)
    slope = sum((z - mx) * (w - my) for z, w in zip(x, y)) / den
    intercept = my - slope * mx
    pred = [slope * z + intercept for z in x]
    ss_res = sum((w - p) ** 2 for w, p in zip(y, pred))
    ss_tot = sum((w - my) ** 2 for w in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"slope_Gamma_eff": slope, "intercept": intercept, "r2": r2, "npoints": len(x)}


def crossover_estimate(rr: list[dict]) -> float | None:
    """Linear-in-T interpolation where measured speedup crosses 1, if bracketed."""
    rr = sorted(rr, key=lambda r: r["T"])
    for a, b in zip(rr[:-1], rr[1:]):
        ya = a["speedup_standard_over_nfold"] - 1.0
        yb = b["speedup_standard_over_nfold"] - 1.0
        if ya == 0:
            return a["T"]
        if ya * yb < 0:
            return a["T"] + (b["T"] - a["T"]) * (-ya) / (yb - ya)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--standard-exe", type=Path, required=True)
    ap.add_argument("--nfold-exe", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("results/temperature_sweep"))
    ap.add_argument("--L", type=int, default=32)
    ap.add_argument("--T-values", type=float, nargs="+",
                    default=[0.80, 0.90, 1.00, 1.20, 1.50, 1.80, 2.10])
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--runs", type=int, default=1000,
                    help="runs for T above cold-threshold")
    ap.add_argument("--cold-runs", type=int, default=500,
                    help="runs for T <= cold-threshold")
    ap.add_argument("--cold-threshold", type=float, default=0.80)
    ap.add_argument("--weak-T08-runs", type=int, default=150)
    ap.add_argument("--weak-T09-runs", type=int, default=4000)
    ap.add_argument("--weak-T10-runs", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--margin", type=float, default=0.05)
    ap.add_argument("--arrhenius-Tmax", type=float, default=1.20)
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    rawdir = args.outdir / "raw"
    rawdir.mkdir(exist_ok=True)
    cases = [("glauber", -3.0), ("glauber", -0.75),
             ("metropolis", -3.0), ("metropolis", -0.75)]

    summary: list[dict] = []
    for ci, (dyn, H) in enumerate(cases):
        for ti, T in enumerate(args.T_values):
            nruns = run_count(T, H, args.runs, args.cold_runs, args.cold_threshold,
                              args.weak_T08_runs, args.weak_T09_runs, args.weak_T10_runs)
            tagH, tagT = ftag(H), ftag(T)
            stdfile = rawdir / f"T{tagT}_standard_{dyn}_H{tagH}.csv"
            nffile = rawdir / f"T{tagT}_nfold_{dyn}_H{tagH}.csv"
            seed = args.seed + 10000019 * ci + 1009 * ti
            if not stdfile.exists():
                run_one(args.standard_exe, stdfile, L=args.L, T=T, J=args.J, H=H,
                        runs=nruns, seed=seed, dynamics=dyn)
            if not nffile.exists():
                run_one(args.nfold_exe, nffile, L=args.L, T=T, J=args.J, H=H,
                        runs=nruns, seed=seed, dynamics=dyn)

            s, n = read_csv(stdfile), read_csv(nffile)
            if len(s["tau"]) != len(n["tau"]):
                raise RuntimeError(f"{dyn}, H={H}, T={T}: unequal ensemble sizes")
            ms, mn = statistics.fmean(s["tau"]), statistics.fmean(n["tau"])
            med_s, med_n = statistics.median(s["tau"]), statistics.median(n["tau"])
            sd_s = statistics.stdev(s["tau"]) if len(s["tau"]) > 1 else 0.0
            sd_n = statistics.stdev(n["tau"]) if len(n["tau"]) > 1 else 0.0
            lo, hi = ratio_bootstrap_ci(s["tau"], n["tau"], args.bootstrap,
                                        args.seed + 1000 * ci + ti)
            ratio = mn / ms
            cpu_s, cpu_n = statistics.fmean(s["cpu"]), statistics.fmean(n["cpu"])
            att_s, att_n = sum(s["attempts"]), sum(n["attempts"])
            evt_s, evt_n = sum(s["events"]), sum(n["events"])
            ks_stat = ks_p = float("nan")
            if ks_2samp is not None:
                kres = ks_2samp(s["tau"], n["tau"], alternative="two-sided", method="auto")
                ks_stat, ks_p = float(kres.statistic), float(kres.pvalue)
            band_lo, band_hi = 1.0 - args.margin, 1.0 + args.margin
            if lo >= band_lo and hi <= band_hi:
                eq_status = "PASS"
            elif hi < band_lo or lo > band_hi:
                eq_status = "FAIL"
            else:
                eq_status = "INCONCLUSIVE"
            summary.append({
                "dynamics": dyn, "H": H, "L": args.L, "N": args.L * args.L,
                "T": T, "invT": 1.0 / T, "J": args.J, "runs": len(s["tau"]),
                "mean_tau_standard_mcss": ms,
                "mean_tau_nfold_mcss": mn,
                "median_tau_standard_mcss": med_s,
                "median_tau_nfold_mcss": med_n,
                "sd_tau_standard_mcss": sd_s,
                "sd_tau_nfold_mcss": sd_n,
                "lifetime_ratio_nfold_standard": ratio,
                "ratio_bootstrap_ci95_lo": lo,
                "ratio_bootstrap_ci95_hi": hi,
                "equivalence_margin": args.margin,
                "equivalence_pass": int(eq_status == "PASS"),
                "equivalence_status": eq_status,
                "ratio_ci_contains_one": int(lo <= 1.0 <= hi),
                "ks_statistic": ks_stat,
                "ks_pvalue": ks_p,
                "cpu_standard_s_per_escape": cpu_s,
                "cpu_nfold_s_per_escape": cpu_n,
                "speedup_standard_over_nfold": cpu_s / cpu_n,
                "mean_standard_attempts_per_escape": att_s / len(s["tau"]),
                "mean_nfold_equiv_attempts_per_escape": att_n / len(n["tau"]),
                "mean_nfold_events_per_escape": evt_n / len(n["tau"]),
                "nfold_equiv_attempts_per_event": att_n / evt_n,
                "standard_acceptance_fraction": sum(s["accepted"]) / att_s,
                "standard_cpu_ns_per_attempt": 1e9 * sum(s["cpu"]) / att_s,
                "nfold_cpu_ns_per_event": 1e9 * sum(n["cpu"]) / evt_n,
            })

    # Family-wise Holm correction for the exploratory KS diagnostics.  This is
    # not an equivalence test; it only guards against over-interpreting one small
    # p-value among many temperature points.
    finite = [(i, r["ks_pvalue"]) for i, r in enumerate(summary) if math.isfinite(r["ks_pvalue"])]
    ordered = sorted(finite, key=lambda z: z[1])
    reject = {i: 0 for i, _ in finite}
    still_rejecting = True
    mtests = len(ordered)
    for rank, (idx, pval) in enumerate(ordered, start=1):
        threshold = 0.05 / (mtests - rank + 1)
        if still_rejecting and pval <= threshold:
            reject[idx] = 1
        else:
            still_rejecting = False
    for i, r in enumerate(summary):
        r["ks_holm_reject_fwer_0p05"] = reject.get(i, 0)

    write_csv(args.outdir / "temperature_sweep_summary.csv", summary)

    fits: list[dict] = []
    cross: list[dict] = []
    for dyn, H in cases:
        rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H),
                    key=lambda r: r["T"])
        for label, key in [("standard", "mean_tau_standard_mcss"),
                           ("nfold", "mean_tau_nfold_mcss")]:
            f = arrhenius_fit(rr, algorithm_key=key, Tmax=args.arrhenius_Tmax)
            fits.append({"dynamics": dyn, "H": H, "algorithm": label,
                         "Tmax_fit": args.arrhenius_Tmax, **f})
        tc = crossover_estimate(rr)
        cross.append({"dynamics": dyn, "H": H,
                      "speedup_crossover_T_linear_interpolation": "" if tc is None else tc,
                      "crossover_bracketed_in_sweep": int(tc is not None),
                      "T_min": min(r["T"] for r in rr), "T_max": max(r["T"] for r in rr)})
    write_csv(args.outdir / "arrhenius_fits.csv", fits)
    write_csv(args.outdir / "speedup_crossovers.csv", cross)

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        print(f"matplotlib unavailable; skipping plots: {exc}")
        plt = None

    if plt is not None:
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H),
                        key=lambda r: r["invT"])
            tagH = ftag(H)
            fig, ax = plt.subplots()
            ax.semilogy([r["invT"] for r in rr], [r["mean_tau_standard_mcss"] for r in rr],
                        marker="o", label="standard")
            ax.semilogy([r["invT"] for r in rr], [r["mean_tau_nfold_mcss"] for r in rr],
                        marker="o", label="n-fold")
            ax.set_xlabel("1/T")
            ax.set_ylabel("Mean escape time (MCSS)")
            ax.set_title(f"Temperature dependence: {dyn.title()}, H/J={H:g}, L={args.L}")
            ax.legend(); fig.tight_layout()
            fig.savefig(args.outdir / f"lifetime_vs_invT_{dyn}_H{tagH}.png", dpi=180)
            plt.close(fig)

            fig, ax = plt.subplots()
            ax.semilogy([r["invT"] for r in rr], [r["cpu_standard_s_per_escape"] for r in rr],
                        marker="o", label="standard")
            ax.semilogy([r["invT"] for r in rr], [r["cpu_nfold_s_per_escape"] for r in rr],
                        marker="o", label="n-fold")
            ax.set_xlabel("1/T")
            ax.set_ylabel("CPU time per escape (s)")
            ax.set_title(f"CPU vs inverse temperature: {dyn.title()}, H/J={H:g}")
            ax.legend(); fig.tight_layout()
            fig.savefig(args.outdir / f"cpu_vs_invT_{dyn}_H{tagH}.png", dpi=180)
            plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            ax.plot([r["T"] for r in rr], [r["speedup_standard_over_nfold"] for r in rr],
                    marker="o", label=f"{dyn}, H/J={H:g}")
        ax.axhline(1.0, linestyle="--", linewidth=1)
        ax.set_xlabel("T/J")
        ax.set_ylabel("Speed-up = CPU standard / CPU n-fold")
        ax.set_title(f"n-fold speed-up across temperature, L={args.L}")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "speedup_vs_temperature.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            ax.semilogy([r["T"] for r in rr], [r["speedup_standard_over_nfold"] for r in rr],
                        marker="o", label=f"{dyn}, H/J={H:g}")
        ax.axhline(1.0, linestyle="--", linewidth=1)
        ax.set_xlabel("T/J")
        ax.set_ylabel("Speed-up = CPU standard / CPU n-fold")
        ax.set_title(f"n-fold speed-up across temperature (log scale), L={args.L}")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "speedup_vs_temperature_log.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            ax.plot([r["T"] for r in rr], [r["nfold_equiv_attempts_per_event"] for r in rr],
                    marker="o", label=f"{dyn}, H/J={H:g}")
        ax.set_xlabel("T/J")
        ax.set_ylabel("Equivalent attempts per n-fold event")
        ax.set_title(f"Rejection compression across temperature, L={args.L}")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "event_compression_vs_temperature.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            ax.semilogy([r["T"] for r in rr], [r["nfold_equiv_attempts_per_event"] for r in rr],
                        marker="o", label=f"{dyn}, H/J={H:g}")
        ax.set_xlabel("T/J")
        ax.set_ylabel("Equivalent attempts per n-fold event")
        ax.set_title(f"Rejection compression across temperature (log scale), L={args.L}")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "event_compression_vs_temperature_log.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            T = [r["T"] for r in rr]
            y = [r["lifetime_ratio_nfold_standard"] for r in rr]
            ylo = [r["lifetime_ratio_nfold_standard"] - r["ratio_bootstrap_ci95_lo"] for r in rr]
            yhi = [r["ratio_bootstrap_ci95_hi"] - r["lifetime_ratio_nfold_standard"] for r in rr]
            ax.errorbar(T, y, yerr=[ylo, yhi], marker="o", capsize=2,
                        label=f"{dyn}, H/J={H:g}")
        ax.axhline(1.0, linestyle="--", linewidth=1)
        ax.axhline(1.0 + args.margin, linestyle=":", linewidth=1)
        ax.axhline(1.0 - args.margin, linestyle=":", linewidth=1)
        ax.set_xlabel("T/J")
        ax.set_ylabel("Mean lifetime ratio n-fold / standard")
        ax.set_title("Temperature-sweep equivalence with bootstrap 95% CI")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "equivalence_vs_temperature.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r:r["T"])
            ax.semilogy([r["T"] for r in rr], [r["standard_acceptance_fraction"] for r in rr],
                        marker="o", label=f"{dyn}, H/J={H:g}")
        ax.set_xlabel("T/J")
        ax.set_ylabel("Standard-MC acceptance fraction")
        ax.set_title(f"Acceptance fraction across temperature, L={args.L}")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "acceptance_vs_temperature.png", dpi=180)
        plt.close(fig)

    # Markdown report
    report = args.outdir / "temperature_sweep_report.md"
    with report.open("w", encoding="utf-8") as f:
        f.write("# Prompt 6 — Temperature sweep\n\n")
        f.write(f"Fixed lattice: `L={args.L}` (`N={args.L*args.L}`), `J={args.J}`.\n\n")
        f.write("Temperatures: " + ", ".join(f"{T:g}" for T in args.T_values) + ".\n\n")
        f.write(f"Adaptive production ensembles: {args.runs} escapes normally and {args.cold_runs} for strong-field T <= {args.cold_threshold:g}. "
                f"For weak field, T=0.8 uses {args.weak_T08_runs}, T=0.9 uses {args.weak_T09_runs}, and T=1.0 uses {args.weak_T10_runs} escapes. "
                "The exact n is recorded per row.\n\n")
        f.write("## Statistical equivalence\n\n")
        passes = sum(r["equivalence_status"] == "PASS" for r in summary)
        inconclusive = sum(r["equivalence_status"] == "INCONCLUSIVE" for r in summary)
        fails = sum(r["equivalence_status"] == "FAIL" for r in summary)
        holm_rejects = sum(int(r["ks_holm_reject_fwer_0p05"]) for r in summary)
        f.write(f"Bootstrap ±{100*args.margin:.0f}% practical-equivalence criterion: **{passes} PASS, {inconclusive} INCONCLUSIVE, {fails} FAIL** out of {len(summary)} points.\n\n")
        f.write(f"The exploratory two-sample KS diagnostics give **{holm_rejects} rejections after Holm family-wise correction at 5%**. KS non-rejection is not used as proof of equivalence.\n\n")
        f.write("| dynamics | H/J | T/J | runs | tau_std | tau_nfold | ratio | 95% CI | status | KS p | speed-up | attempts/event |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|\n")
        for r in sorted(summary, key=lambda z:(z["dynamics"], z["H"], z["T"])):
            f.write(f"| {r['dynamics']} | {r['H']:g} | {r['T']:g} | {r['runs']} | "
                    f"{r['mean_tau_standard_mcss']:.6g} | {r['mean_tau_nfold_mcss']:.6g} | "
                    f"{r['lifetime_ratio_nfold_standard']:.4f} | "
                    f"[{r['ratio_bootstrap_ci95_lo']:.4f}, {r['ratio_bootstrap_ci95_hi']:.4f}] | "
                    f"{r['equivalence_status']} | {r['ks_pvalue']:.3g} | {r['speedup_standard_over_nfold']:.3f} | "
                    f"{r['nfold_equiv_attempts_per_event']:.3f} |\n")
        f.write("\n## Empirical Arrhenius-style fit\n\n")
        f.write(f"For descriptive purposes only, `ln(<tau>) = a + Gamma_eff/T` is fitted on points with T <= {args.arrhenius_Tmax:g}. "
                "The slope is an effective finite-range slope, not asserted to be a universal barrier.\n\n")
        f.write("| dynamics | H/J | algorithm | Gamma_eff | R^2 | n |\n")
        f.write("|---|---:|---|---:|---:|---:|\n")
        for q in fits:
            f.write(f"| {q['dynamics']} | {q['H']:g} | {q['algorithm']} | {q['slope_Gamma_eff']:.5g} | {q['r2']:.5f} | {q['npoints']} |\n")
        f.write("\n## Speed-up crossover\n\n")
        for q in cross:
            if q["crossover_bracketed_in_sweep"]:
                f.write(f"- {q['dynamics']}, H/J={q['H']:g}: measured speed-up crosses 1 near T/J ≈ {float(q['speedup_crossover_T_linear_interpolation']):.3f} by linear interpolation between adjacent sampled points.\n")
            else:
                f.write(f"- {q['dynamics']}, H/J={q['H']:g}: no speed-up=1 crossing is bracketed in the sampled range.\n")
        f.write("\nThe crossover values are implementation/hardware dependent and should not be interpreted as physical transition temperatures.\n")

    print(f"Wrote {args.outdir / 'temperature_sweep_summary.csv'}")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
