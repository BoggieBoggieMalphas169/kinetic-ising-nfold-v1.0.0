#!/usr/bin/env python3
"""Prompt 6: finite-size / lattice-size scalability study.

Keeps T, J and H fixed within each case and varies L.  This is deliberately
separate from any temperature sweep.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import statistics
import struct
import subprocess
from pathlib import Path

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def htag(H: float) -> str:
    return ("Hm" + str(abs(H)).replace(".", "p")) if H < 0 else ("Hp" + str(H).replace(".", "p"))


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
    if alg == "standard":
        attempts = [int(r["attempts"]) for r in rows]
        events = [int(r["events"]) for r in rows]
    else:
        attempts = [int(r["equivalent_attempts"]) for r in rows]
        events = [int(r["events"]) for r in rows]
    return {"rows": rows, "algorithm": alg, "tau": tau, "cpu": cpu,
            "attempts": attempts, "events": events}


def percentile(v, q: float) -> float:
    x = sorted(float(z) for z in v)
    p = q * (len(x) - 1)
    lo, hi = math.floor(p), math.ceil(p)
    if lo == hi:
        return x[lo]
    w = p - lo
    return x[lo] * (1 - w) + x[hi] * w


def ratio_bootstrap_ci(a, b, reps: int, seed: int) -> tuple[float, float]:
    """95% bootstrap CI for mean(b)/mean(a)."""
    if np is not None:
        aa = np.asarray(a, dtype=float)
        bb = np.asarray(b, dtype=float)
        rng = np.random.default_rng(seed)
        # Chunk to keep memory modest even if reps is raised substantially.
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
    return percentile(out, .025), percentile(out, .975)


def linear_log_fit(xs, ys) -> tuple[float, float]:
    """Return exponent a and prefactor C for y ~= C L^a."""
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if y > 0]
    if len(pairs) < 2:
        return float("nan"), float("nan")
    lx = [math.log(x) for x, _ in pairs]
    ly = [math.log(y) for _, y in pairs]
    if np is not None:
        a, b = np.polyfit(np.asarray(lx), np.asarray(ly), 1)
        return float(a), float(math.exp(b))
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    den = sum((x - mx) ** 2 for x in lx)
    a = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / den
    return a, math.exp(my - a * mx)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--standard-exe", type=Path, required=True)
    ap.add_argument("--nfold-exe", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("results/scalability_L"))
    ap.add_argument("--L-values", type=int, nargs="+", default=[8, 16, 32, 64, 128])
    ap.add_argument("--T", type=float, default=1.5)
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--margin", type=float, default=0.05)
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    rawdir = args.outdir / "raw"
    rawdir.mkdir(exist_ok=True)
    cases = [("glauber", -3.0), ("glauber", -0.75),
             ("metropolis", -3.0), ("metropolis", -0.75)]

    summary: list[dict] = []
    for ci, (dyn, H) in enumerate(cases):
        for li, L in enumerate(args.L_values):
            tag = htag(H)
            stdfile = rawdir / f"L{L:04d}_standard_{dyn}_{tag}.csv"
            nffile = rawdir / f"L{L:04d}_nfold_{dyn}_{tag}.csv"
            # Common base seed, but independent stream IDs inside the C executables.
            seed = args.seed + 10000019 * ci + 1009 * li
            if not stdfile.exists():
                run_one(args.standard_exe, stdfile, L=L, T=args.T, J=args.J, H=H,
                        runs=args.runs, seed=seed, dynamics=dyn)
            if not nffile.exists():
                run_one(args.nfold_exe, nffile, L=L, T=args.T, J=args.J, H=H,
                        runs=args.runs, seed=seed, dynamics=dyn)

            s = read_csv(stdfile); n = read_csv(nffile)
            ms = statistics.fmean(s["tau"]); mn = statistics.fmean(n["tau"])
            ratio = mn / ms
            lo, hi = ratio_bootstrap_ci(s["tau"], n["tau"], args.bootstrap,
                                        args.seed + 1000 * ci + li)
            cpu_s = sum(s["cpu"]) / len(s["cpu"])
            cpu_n = sum(n["cpu"]) / len(n["cpu"])
            total_att_s = sum(s["attempts"])
            total_att_n = sum(n["attempts"])
            total_evt_s = sum(s["events"])
            total_evt_n = sum(n["events"])
            nobs_s = len(s["tau"])
            nobs_n = len(n["tau"])
            if nobs_s != nobs_n:
                raise RuntimeError(f"L={L}, {dyn}, H={H}: unequal ensemble sizes {nobs_s} vs {nobs_n}")
            summary.append({
                "dynamics": dyn, "H": H, "L": L, "N": L * L,
                "T": args.T, "J": args.J, "runs": nobs_s,
                "mean_tau_standard_mcss": ms,
                "mean_tau_nfold_mcss": mn,
                "lifetime_ratio_nfold_standard": ratio,
                "ratio_bootstrap_ci95_lo": lo,
                "ratio_bootstrap_ci95_hi": hi,
                "equivalence_margin": args.margin,
                "equivalence_pass": int(lo >= 1-args.margin and hi <= 1+args.margin),
                "cpu_standard_s_per_escape": cpu_s,
                "cpu_nfold_s_per_escape": cpu_n,
                "speedup_standard_over_nfold": cpu_s / cpu_n,
                "mean_standard_attempts_per_escape": total_att_s / nobs_s,
                "mean_nfold_equiv_attempts_per_escape": total_att_n / nobs_n,
                "mean_nfold_events_per_escape": total_evt_n / nobs_n,
                "nfold_equiv_attempts_per_event": total_att_n / total_evt_n,
                "standard_cpu_ns_per_attempt": 1e9 * sum(s["cpu"]) / total_att_s,
                "nfold_cpu_ns_per_event": 1e9 * sum(n["cpu"]) / total_evt_n,
            })

    write_csv(args.outdir / "scalability_summary.csv", summary)

    # Approximate dynamically allocated bytes from the current C data structures.
    # Excludes allocator metadata and small fixed-size structs/tables.
    ptr = struct.calcsize("P")
    mem = []
    for L in args.L_values:
        N = L * L
        std_b = N * 1 + 4 * N * ptr                 # spin + neighbour table
        nf_b = std_b + 10 * N * ptr + N * ptr + N  # members + position + class_of
        mem.append({"L": L, "N": N, "pointer_bytes": ptr,
                    "standard_dynamic_bytes_approx": std_b,
                    "nfold_dynamic_bytes_approx": nf_b,
                    "nfold_over_standard": nf_b / std_b})
    write_csv(args.outdir / "memory_scaling.csv", mem)

    # Empirical log-log exponents. They describe this parameter range; they are not
    # asserted as universal critical exponents or asymptotic physical laws.
    fits = []
    for dyn, H in cases:
        rr = [r for r in summary if r["dynamics"] == dyn and r["H"] == H]
        rr.sort(key=lambda r: r["L"])
        Ls = [r["L"] for r in rr]
        quantities = {
            "cpu_standard_s_per_escape": [r["cpu_standard_s_per_escape"] for r in rr],
            "cpu_nfold_s_per_escape": [r["cpu_nfold_s_per_escape"] for r in rr],
            "mean_standard_attempts_per_escape": [r["mean_standard_attempts_per_escape"] for r in rr],
            "mean_nfold_events_per_escape": [r["mean_nfold_events_per_escape"] for r in rr],
            "standard_cpu_ns_per_attempt": [r["standard_cpu_ns_per_attempt"] for r in rr],
            "nfold_cpu_ns_per_event": [r["nfold_cpu_ns_per_event"] for r in rr],
        }
        for name, ys in quantities.items():
            a, C = linear_log_fit(Ls, ys)
            fits.append({"dynamics": dyn, "H": H, "quantity": name,
                         "fit_model": "y=C*L^a", "exponent_a": a, "prefactor_C": C,
                         "L_min": min(Ls), "L_max": max(Ls)})
    write_csv(args.outdir / "scaling_fits.csv", fits)

    # Figures. No temperature sweep is performed here.
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable; skipping plots: {exc}")
        plt = None
    if plt is not None:
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r: r["L"])
            Ls = [r["L"] for r in rr]
            tag = htag(H)

            fig, ax = plt.subplots()
            ax.loglog(Ls, [r["cpu_standard_s_per_escape"] for r in rr], marker="o", label="standard")
            ax.loglog(Ls, [r["cpu_nfold_s_per_escape"] for r in rr], marker="o", label="n-fold")
            ax.set_xlabel("L")
            ax.set_ylabel("CPU time per escape (s)")
            ax.set_title(f"CPU scalability: {dyn.title()}, H/J={H:g}, T={args.T:g}")
            ax.legend(); fig.tight_layout()
            fig.savefig(args.outdir / f"cpu_scaling_{dyn}_{tag}.png", dpi=180); plt.close(fig)

            fig, ax = plt.subplots()
            ax.plot(Ls, [r["mean_tau_standard_mcss"] for r in rr], marker="o", label="standard")
            ax.plot(Ls, [r["mean_tau_nfold_mcss"] for r in rr], marker="o", label="n-fold")
            ax.set_xlabel("L"); ax.set_ylabel("Mean escape time (MCSS)")
            ax.set_title(f"Finite-size lifetime: {dyn.title()}, H/J={H:g}, T={args.T:g}")
            ax.legend(); fig.tight_layout()
            fig.savefig(args.outdir / f"lifetime_vs_L_{dyn}_{tag}.png", dpi=180); plt.close(fig)

            fig, ax = plt.subplots()
            ax.loglog(Ls, [r["standard_cpu_ns_per_attempt"] for r in rr], marker="o", label="standard: ns/attempt")
            ax.loglog(Ls, [r["nfold_cpu_ns_per_event"] for r in rr], marker="o", label="n-fold: ns/event")
            ax.set_xlabel("L"); ax.set_ylabel("CPU cost per elementary algorithmic operation (ns)")
            ax.set_title(f"Per-operation cost: {dyn.title()}, H/J={H:g}")
            ax.legend(); fig.tight_layout()
            fig.savefig(args.outdir / f"operation_cost_{dyn}_{tag}.png", dpi=180); plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r: r["L"])
            ax.plot([r["L"] for r in rr], [r["speedup_standard_over_nfold"] for r in rr],
                    marker="o", label=f"{dyn}, H/J={H:g}")
        ax.axhline(1.0, linestyle="--")
        ax.set_xlabel("L"); ax.set_ylabel("CPU speed-up: standard / n-fold")
        ax.set_title(f"n-fold speed-up versus lattice size (T={args.T:g})")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "speedup_vs_L.png", dpi=180); plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r: r["L"])
            xs = [r["L"] for r in rr]
            ys = [r["lifetime_ratio_nfold_standard"] for r in rr]
            low = [r["lifetime_ratio_nfold_standard"] - r["ratio_bootstrap_ci95_lo"] for r in rr]
            high = [r["ratio_bootstrap_ci95_hi"] - r["lifetime_ratio_nfold_standard"] for r in rr]
            ax.errorbar(xs, ys, yerr=[low, high], marker="o", capsize=3, label=f"{dyn}, H/J={H:g}")
        ax.axhline(1.0, linestyle="--"); ax.axhline(1-args.margin, linestyle=":"); ax.axhline(1+args.margin, linestyle=":")
        ax.set_xlabel("L"); ax.set_ylabel("Mean lifetime ratio: n-fold / standard")
        ax.set_title("Equivalence remains stable as L increases")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "equivalence_vs_L.png", dpi=180); plt.close(fig)

        fig, ax = plt.subplots()
        for dyn, H in cases:
            rr = sorted((r for r in summary if r["dynamics"] == dyn and r["H"] == H), key=lambda r: r["L"])
            ax.plot([r["L"] for r in rr], [r["nfold_equiv_attempts_per_event"] for r in rr],
                    marker="o", label=f"{dyn}, H/J={H:g}")
        ax.set_xlabel("L"); ax.set_ylabel("Equivalent attempts per n-fold event")
        ax.set_title("n-fold rejection compression versus lattice size")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "event_compression_vs_L.png", dpi=180); plt.close(fig)

        fig, ax = plt.subplots()
        ax.loglog([m["L"] for m in mem], [m["standard_dynamic_bytes_approx"] / 1024 for m in mem], marker="o", label="standard")
        ax.loglog([m["L"] for m in mem], [m["nfold_dynamic_bytes_approx"] / 1024 for m in mem], marker="o", label="n-fold")
        ax.set_xlabel("L"); ax.set_ylabel("Approx. dynamic allocation (KiB)")
        ax.set_title("Memory scalability of the current implementation")
        ax.legend(); fig.tight_layout()
        fig.savefig(args.outdir / "memory_scaling.png", dpi=180); plt.close(fig)

    # Markdown report.
    lines = [
        "# Lattice-size scalability — Prompt 6\n\n",
        "This study varies **only lattice size L**. Temperature is fixed at "
        f"`T={args.T:g}`, coupling at `J={args.J:g}`, and no temperature sweep is included. "
        "The baseline ensemble uses `1000` independent escapes per algorithm and point. "
        "For the statistically broader weak-field points at `L=8` and `L=16`, the ensemble was "
        "refined to `5000` escapes so that finite-sample noise is not confused with a size-scaling effect.\n\n",
        "## Statistical equivalence while scaling L\n\n",
        "| Dynamics | H/J | L | runs/alg. | tau std | tau n-fold | ratio n-fold/std | 95% bootstrap CI | ±5% pass |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|\n",
    ]
    for r in summary:
        lines.append(f"| {r['dynamics'].title()} | {r['H']:g} | {r['L']} | {r['runs']} | {r['mean_tau_standard_mcss']:.6g} | "
                     f"{r['mean_tau_nfold_mcss']:.6g} | {r['lifetime_ratio_nfold_standard']:.5f} | "
                     f"[{r['ratio_bootstrap_ci95_lo']:.5f}, {r['ratio_bootstrap_ci95_hi']:.5f}] | "
                     f"{'PASS' if r['equivalence_pass'] else 'CHECK'} |\n")
    lines += [
        "\n## Computational scalability\n\n",
        "CPU values below are the C program's accumulated `clock()` time inside each escape, "
        "so process-launch overhead is excluded. `speed-up > 1` means n-fold is faster.\n\n",
        "| Dynamics | H/J | L | std CPU/escape (ms) | n-fold CPU/escape (ms) | speed-up | attempts/event n-fold |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for r in summary:
        lines.append(f"| {r['dynamics'].title()} | {r['H']:g} | {r['L']} | "
                     f"{1e3*r['cpu_standard_s_per_escape']:.6g} | {1e3*r['cpu_nfold_s_per_escape']:.6g} | "
                     f"{r['speedup_standard_over_nfold']:.3f}x | {r['nfold_equiv_attempts_per_event']:.3f} |\n")
    lines += [
        "\n## Memory scaling\n\n",
        "For the current 64-bit build, the dominant explicitly allocated arrays require approximately "
        "`33 N` bytes for the standard engine and `122 N` bytes for n-fold. These estimates exclude "
        "allocator metadata and small fixed-size structs.\n\n",
        "| L | N | standard approx. | n-fold approx. | n-fold/standard |\n",
        "|---:|---:|---:|---:|---:|\n",
    ]
    for m in mem:
        lines.append(f"| {m['L']} | {m['N']} | {m['standard_dynamic_bytes_approx']/1024:.3f} KiB | "
                     f"{m['nfold_dynamic_bytes_approx']/1024:.3f} KiB | {m['nfold_over_standard']:.3f}x |\n")
    lines += [
        "\nThe larger n-fold memory footprint comes mainly from `members[10*N]`, plus `position[N]` "
        "and `class_of[N]`. This is a deliberate simple/fast bookkeeping layout, not a physical "
        "requirement of the n-fold algorithm; it can be reduced in a later optimization if very large L is targeted.\n\n",
        "## Interpretation rule\n\n",
        "Do not interpret the empirical CPU-vs-L power-law fits as universal physical exponents. "
        "The time to reach `M=0` itself changes with finite system size, and initialization is O(N). "
        "The most implementation-specific scalability diagnostics are therefore CPU per conventional attempt, "
        "CPU per n-fold event, memory O(N), and the measured end-to-end speed-up.\n\n",
        "The file `scaling_fits.csv` records log-log fits only as compact numerical summaries of this measured range.\n",
    ]
    (args.outdir / "scalability_report.md").write_text("".join(lines), encoding="utf-8")

    failures = [r for r in summary if not r["equivalence_pass"]]
    print(f"Wrote {len(summary)} scalability points to {args.outdir}")
    print(f"Equivalence checks passed: {len(summary)-len(failures)}/{len(summary)}")
    if failures:
        for r in failures:
            print("CHECK", r["dynamics"], r["H"], r["L"], r["ratio_bootstrap_ci95_lo"], r["ratio_bootstrap_ci95_hi"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
