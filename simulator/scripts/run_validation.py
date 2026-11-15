#!/usr/bin/env python3
"""Run end-to-end standard vs n-fold validation cases."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--standard-exe", type=Path, required=True)
    ap.add_argument("--nfold-exe", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("results/validation"))
    ap.add_argument("--L", type=int, default=16)
    ap.add_argument("--T", type=float, default=1.5)
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--equivalence-margin", type=float, default=0.20)
    ap.add_argument("--quick", action="store_true",
                    help="only Glauber H=-3 with at most 200 runs")
    ap.add_argument("--strict", action="store_true",
                    help="return failure if the configured equivalence checks are not established")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    cases = [("glauber", -3.0)]
    if not args.quick:
        cases = [
            ("glauber", -3.0),
            ("glauber", -0.75),
            ("metropolis", -3.0),
            ("metropolis", -0.75),
        ]
    runs = min(args.runs, 200) if args.quick else args.runs

    here = Path(__file__).resolve().parent
    compare = here / "compare_escape_times.py"
    check = here / "check_csv_invariants.py"

    for dynamics, H in cases:
        tag = f"{dynamics}_Hm{str(abs(H)).replace('.', 'p')}"
        std = args.outdir / f"standard_{tag}.csv"
        nfd = args.outdir / f"nfold_{tag}.csv"
        common = [
            "--L", str(args.L), "--T", str(args.T), "--J", str(args.J),
            "--H", str(H), "--runs", str(runs), "--seed", str(args.seed),
            "--dynamics", dynamics,
        ]
        run([str(args.standard_exe), *common, "--output", str(std)])
        run([str(args.nfold_exe), *common, "--output", str(nfd)])
        run([sys.executable, str(check), str(std), "--require-complete"])
        run([sys.executable, str(check), str(nfd), "--require-complete"])
        compare_cmd = [
            sys.executable, str(compare), str(std), str(nfd),
            "--equivalence-margin", str(args.equivalence_margin),
        ]
        if args.strict:
            compare_cmd.append("--assert-equivalent")
        run(compare_cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
