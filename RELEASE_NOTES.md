# Release notes — v1.0.0

This is the first **fully integrated** release of the project. It supersedes the intermediate `v1.0.0-analysis` package by adding the validated Prompt-6 C simulator and its original raw validation datasets to the Prompt-8 reproducibility/analysis layer.

## Included

- Standard random single-spin kinetic Ising Monte Carlo in C.
- n-fold way / rejection-free kinetic Monte Carlo in C.
- Glauber and Metropolis dynamics.
- C unit tests and end-to-end CSV smoke tests.
- Prompt-6 raw validation, scalability and temperature-sweep ensembles.
- Prompt-8 data contracts, snapshot, physical-equivalence analysis and performance analysis.
- Final figures/tables, documentation, citation metadata, CI and deterministic release tooling.

## Frozen scientific result

The published Prompt-8 analysis remains tied to `snap_0cc46433731097c4`: 49 PASS, 3 INCONCLUSIVE, 0 FAIL across 52 campaign comparisons (44 unique physical points).

## Reproducibility

The release is validated at two levels: the C simulator is compiled/tested with CMake/CTest, and the Python layer is tested with pytest and release/snapshot hash checks.

## Validation status

The integrated release passes 6 C/CTest checks and 86 Python tests before manifest freezing.
