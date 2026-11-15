# Prompt 6 — Validation snapshot for the Ising project

This archive is a self-contained validation snapshot containing both reference algorithms
and the Prompt 6 test harness. It can also be used as the source of the validation files
to merge into the previous Prompt 5 repository.

## What is validated

- 2D nearest-neighbour ferromagnetic Ising Hamiltonian with periodic boundaries.
- Incremental vs full energy and magnetization.
- The shared 10 local spin classes.
- Metropolis and Glauber probabilities.
- Random-site standard dynamic Monte Carlo.
- Discrete-time n-fold waiting clock.
- n-fold class selection and incremental class bookkeeping.
- Reproducibility for fixed seed/stream.
- CSV invariants.
- End-to-end standard vs n-fold lifetime distributions.
- Wall-time benchmarking.
- AddressSanitizer / UndefinedBehaviorSanitizer configuration.

The standard reference deliberately uses **random single-site updates**, not sequential
sweeps, so it represents the same underlying stochastic dynamics accelerated by n-fold.

## Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

On multi-config Windows generators, executables may be under `build/Release/`.
With MinGW, the paths are usually `build/ising_standard.exe` and `build/ising_nfold.exe`.

A plain Makefile is also provided:

```bash
make
make test
```

## Quick validation

Linux/macOS:

```bash
python3 scripts/run_validation.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --quick
```

PowerShell / Windows with MinGW-style CMake output:

```powershell
python scripts/run_validation.py `
  --standard-exe build/ising_standard.exe `
  --nfold-exe build/ising_nfold.exe `
  --quick
```

## Full four-case validation

```bash
python3 scripts/run_validation.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --L 16 --T 1.5 --J 1 --runs 1000 \
  --equivalence-margin 0.10
```

This runs:

- Glauber, `H=-3`;
- Glauber, `H=-0.75`;
- Metropolis, `H=-3`;
- Metropolis, `H=-0.75`.

For slow low-temperature weak-field cases, first test at smaller `L` and then scale the
production ensemble.

## Important interpretation

The same seed is useful for reproducibility, but standard and n-fold should not be
expected to generate the same microscopic trajectory. The validation target is the same
probability law for the physical dynamics, particularly the distribution of the escape
time to the first state with `M=0`.

See `docs/validation.md` for the full acceptance criteria.

## Production validation completed

A stricter production validation has now also been executed at `L=32`, `T=1.5`, with
1000 independent escapes for every combination of Glauber/Metropolis and
`H=-3,-0.75`. All four standard-vs-n-fold comparisons pass a `±5%` practical-equivalence
criterion for the bootstrap 95% confidence interval of the mean-lifetime ratio.

See:

- `docs/validation_results_production.md` for the numerical results and interpretation;
- `results/validation_prod_L32/` for the raw ensemble CSV files;
- `results/production_report_L32/` for the consolidated summary and figures;
- `results/benchmarks_prod_L32/` for raw and summarized timing measurements.

The main physical conclusion of Prompt 6 is now supported directly by the simulations:
standard and n-fold reproduce statistically compatible metastable lifetimes, while n-fold
compresses many rejected attempts into one accepted event. The measured wall-clock benefit
appears in the weak-field case but not necessarily in the strong-field case, where bookkeeping
can dominate.

## Lattice-size scalability completed

The finite-size scalability study has now been run at fixed `T=1.5`, `J=1` for
`L = 8, 16, 32, 64, 128`, keeping the temperature fixed throughout.  Both fields
(`H=-3`, `H=-0.75`) and both dynamics (Glauber and Metropolis) are included.

The baseline ensemble is 1000 escapes per algorithm and point.  The broader weak-field
points at `L=8` and `L=16` were refined to 5000 escapes so finite-sample noise would not
be mistaken for a lattice-size effect.  All 20 standard-vs-n-fold comparisons pass the
predeclared ±5% practical-equivalence band for the bootstrap 95% CI of the mean-lifetime
ratio.

Over the measured range, CPU time per complete escape scales approximately as `L^2`
for both algorithms (equivalently, approximately linearly in `N=L^2`).  In contrast,
CPU cost per standard attempted update and per n-fold event is approximately independent
of L, as expected for local updates with precomputed neighbours and local class
bookkeeping.

The current memory layout is also linear in N.  On the 64-bit validation build, dominant
dynamic arrays use about `33 N` bytes in the standard engine and `122 N` bytes in n-fold.
The latter is mainly due to the deliberately simple `members[10*N]` class-storage layout.

See:

- `docs/scalability_L.md` for interpretation and the principal numerical results;
- `results/scalability_L/scalability_summary.csv` for all 20 measured points;
- `results/scalability_L/scaling_fits.csv` for empirical log-log fits;
- `results/scalability_L/memory_scaling.csv` for the memory model;
- `results/scalability_L/raw/` for the complete per-escape CSV data;
- the PNG files in `results/scalability_L/` for the generated figures.


## Temperature sweep completed — Prompt 6 closure

The final validation stage keeps `L=32`, `N=1024`, `J=1` fixed and sweeps

`T/J = 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.1`

for Glauber and Metropolis at `H/J=-3` and `H/J=-0.75`.  Standard and n-fold are
run as independent ensembles and compared through the mean metastable lifetime,
bootstrap confidence intervals, an exploratory two-sample KS diagnostic, CPU cost,
and the number of conventional attempts represented by one n-fold event.

Because the weak-field low-temperature lifetime has a broad tail, the production
sample size is adaptive: 150 escapes at `T=0.8`, 4000 at `T=0.9`, 10000 at `T=1.0`,
and 1000 at the warmer weak-field points.  Strong-field points use 500 escapes at
`T=0.8` and 1000 otherwise.  The exact ensemble size is recorded in every summary row.

Using the predeclared ±5% practical-equivalence band for the bootstrap 95% CI of the
mean-lifetime ratio, 25 of 28 temperature points are `PASS`, three cold weak-field
points are `INCONCLUSIVE`, and none are `FAIL`.  The inconclusive cases have confidence
intervals that overlap the equivalence region but are too broad to fit wholly inside it;
this is kept as a statistical-precision limitation rather than being relabelled as a pass.
The exploratory KS comparisons produce zero rejections after Holm family-wise correction
at 5%; this diagnostic is not treated as proof of equivalence.

The efficiency trend is much stronger than at the original single temperature.  At
`H/J=-0.75`, the measured n-fold speed-up rises sharply as temperature is lowered,
reaching roughly two orders of magnitude at the coldest point, because one n-fold event
represents hundreds to more than a thousand rejected/accepted conventional attempts.
At `H/J=-3`, rejection is modest and n-fold remains slower than the simple standard
algorithm over the sampled range because class bookkeeping dominates.

Linear interpolation of the measured speed-up through one gives implementation-specific
crossovers near `T/J≈2.02` for Glauber and `T/J≈1.68` for Metropolis at `H/J=-0.75`.
These are performance crossovers for this code/build/machine, not physical transition
temperatures.

An empirical Arrhenius-style diagnostic `ln(<tau>) = a + Gamma_eff/T` is also included
for `T<=1.2`.  It is reported only as a finite-range consistency diagnostic, not as a
universal nucleation barrier.

Run the sweep with:

```bash
python3 scripts/temperature_sweep.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold
```

See:

- `docs/temperature_sweep.md` for interpretation;
- `docs/prompt6_closure.md` for the final Prompt 6 validation summary;
- `results/temperature_sweep/temperature_sweep_summary.csv` for all 28 points;
- `results/temperature_sweep/arrhenius_fits.csv` for the empirical inverse-temperature fits;
- `results/temperature_sweep/speedup_crossovers.csv` for the measured performance crossovers;
- `results/temperature_sweep/raw/` for the per-escape data;
- the PNG figures in `results/temperature_sweep/` for lifetime, equivalence, acceptance,
  event-compression and CPU trends.
