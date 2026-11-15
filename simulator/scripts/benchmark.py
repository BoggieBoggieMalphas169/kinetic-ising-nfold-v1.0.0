#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def timed_run(exe: Path, algorithm: str, *, L: int, T: float, J: float, H: float,
              runs: int, seed: int, dynamics: str) -> float:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"{algorithm}.csv"
        cmd = [
            str(exe), "--L", str(L), "--T", str(T), "--J", str(J), "--H", str(H),
            "--runs", str(runs), "--seed", str(seed), "--dynamics", dynamics,
            "--output", str(out),
        ]
        t0 = time.perf_counter()
        subprocess.run(cmd, check=True)
        return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--standard-exe", type=Path, required=True)
    ap.add_argument("--nfold-exe", type=Path, required=True)
    ap.add_argument("--L", type=int, default=32)
    ap.add_argument("--T", type=float, default=1.5)
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--H", type=float, default=-3.0)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--dynamics", choices=["glauber", "metropolis"], default="glauber")
    ap.add_argument("--repeat", type=int, default=5)
    args = ap.parse_args()

    ts, tn = [], []
    for r in range(args.repeat):
        seed = args.seed + r * 1000003
        ts.append(timed_run(args.standard_exe, "standard", L=args.L, T=args.T,
                            J=args.J, H=args.H, runs=args.runs, seed=seed,
                            dynamics=args.dynamics))
        tn.append(timed_run(args.nfold_exe, "nfold", L=args.L, T=args.T,
                            J=args.J, H=args.H, runs=args.runs, seed=seed,
                            dynamics=args.dynamics))

    ms, mn = statistics.median(ts), statistics.median(tn)
    print(f"standard median wall time: {ms:.6g} s")
    print(f"n-fold   median wall time: {mn:.6g} s")
    print(f"CPU/wall speed-up standard/n-fold: {ms/mn:.6g}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
