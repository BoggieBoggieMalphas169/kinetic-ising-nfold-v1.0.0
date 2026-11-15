#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file", type=Path)
    ap.add_argument("--require-complete", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    with args.csv_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        errors.append("CSV has no rows")

    for i, r in enumerate(rows, start=2):
        try:
            L = int(r["L"])
            N = int(r["N"])
            time_attempts = int(r["time_attempts"])
            time_mcss = float(r["time_mcss"])
            M = int(r["final_M"])
            E = float(r["final_E"])
            complete = r["reached_M0"] in {"1", "true", "True"}
            if N != L * L:
                errors.append(f"line {i}: N != L^2")
            expected = time_attempts / N
            if not math.isclose(time_mcss, expected, rel_tol=2e-13, abs_tol=2e-13):
                errors.append(f"line {i}: time_mcss != time_attempts/N")
            if not math.isfinite(E):
                errors.append(f"line {i}: non-finite final_E")
            if complete and M != 0:
                errors.append(f"line {i}: reached_M0=1 but final_M={M}")
            if args.require_complete and not complete:
                errors.append(f"line {i}: incomplete escape")
            algo = r.get("algorithm", "")
            if algo == "standard":
                attempts = int(r["attempts"])
                accepted = int(r["accepted"])
                if attempts != time_attempts:
                    errors.append(f"line {i}: attempts != time_attempts")
                if accepted > attempts:
                    errors.append(f"line {i}: accepted > attempts")
            elif algo == "nfold":
                eq = int(r["equivalent_attempts"])
                events = int(r["events"])
                if eq != time_attempts:
                    errors.append(f"line {i}: equivalent_attempts != time_attempts")
                if events > eq:
                    errors.append(f"line {i}: events > equivalent_attempts")
        except (KeyError, ValueError) as exc:
            errors.append(f"line {i}: malformed row ({exc})")

    if errors:
        print(f"{args.csv_file}: FAIL ({len(errors)} issue(s))")
        for e in errors[:50]:
            print(" -", e)
        return 1
    print(f"{args.csv_file}: PASS ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
