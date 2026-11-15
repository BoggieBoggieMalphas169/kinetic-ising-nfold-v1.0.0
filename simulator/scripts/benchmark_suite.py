#!/usr/bin/env python3
"""Benchmark all four Prompt-6 reference cases and save reproducible CSV/Markdown results."""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def timed_run(exe: Path, *, L: int, T: float, J: float, H: float, runs: int, seed: int, dynamics: str) -> float:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.csv"
        cmd = [str(exe), "--L", str(L), "--T", str(T), "--J", str(J), "--H", str(H),
               "--runs", str(runs), "--seed", str(seed), "--dynamics", dynamics,
               "--output", str(out)]
        t0 = time.perf_counter()
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--standard-exe", type=Path, required=True)
    ap.add_argument("--nfold-exe", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("results/benchmarks"))
    ap.add_argument("--L", type=int, default=32)
    ap.add_argument("--T", type=float, default=1.5)
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--runs", type=int, default=500)
    ap.add_argument("--seed", type=int, default=314159)
    ap.add_argument("--repeat", type=int, default=5)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    cases = [("glauber", -3.0), ("glauber", -0.75), ("metropolis", -3.0), ("metropolis", -0.75)]
    raw = []
    summary = []
    for dyn, H in cases:
        ts, tn = [], []
        for rep in range(args.repeat):
            seed = args.seed + rep * 1000003
            s = timed_run(args.standard_exe, L=args.L, T=args.T, J=args.J, H=H,
                          runs=args.runs, seed=seed, dynamics=dyn)
            n = timed_run(args.nfold_exe, L=args.L, T=args.T, J=args.J, H=H,
                          runs=args.runs, seed=seed, dynamics=dyn)
            ts.append(s); tn.append(n)
            raw.append({"dynamics": dyn, "H": H, "repeat": rep, "seed": seed,
                        "standard_seconds": s, "nfold_seconds": n, "speedup_std_over_nfold": s/n})
        ms, mn = statistics.median(ts), statistics.median(tn)
        summary.append({"dynamics": dyn, "H": H, "L": args.L, "T": args.T,
                        "runs_per_repeat": args.runs, "repeats": args.repeat,
                        "standard_median_seconds": ms, "nfold_median_seconds": mn,
                        "speedup_std_over_nfold": ms/mn})

    with (args.outdir / "benchmark_raw.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw[0].keys())); w.writeheader(); w.writerows(raw)
    with (args.outdir / "benchmark_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)

    md = ["# Prompt 6 benchmark summary\n\n",
          "Wall-clock timings are machine/compiler dependent and are kept separate from physical validation. "
          "A speed-up above 1 means n-fold is faster; below 1 means the standard algorithm is faster.\n\n",
          "| Dynamics | H/J | standard median (s) | n-fold median (s) | standard/n-fold |\n",
          "|---|---:|---:|---:|---:|\n"]
    for s in summary:
        md.append(f"| {s['dynamics'].title()} | {s['H']:g} | {s['standard_median_seconds']:.6g} | "
                  f"{s['nfold_median_seconds']:.6g} | **{s['speedup_std_over_nfold']:.3f}x** |\n")
    (args.outdir / "benchmark_summary.md").write_text("".join(md), encoding="utf-8")
    print("".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
