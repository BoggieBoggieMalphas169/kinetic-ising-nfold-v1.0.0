# Kinetic Ising Monte Carlo: Standard vs n-fold way

[Versión en español](README_ES.md)

A reproducible computational-physics repository for metastable escape in the two-dimensional ferromagnetic Ising model. It contains both the validated **C simulation engine** and the **Python analysis/reproducibility layer** used to compare random single-spin Standard Monte Carlo with the rejection-free **n-fold way**.

**Release:** `v1.0.0` · **Date:** 2026-09-30 · **Analysis snapshot:** `snap_0cc46433731097c4`

## Scientific question

The project separates two questions that should not be conflated:

1. **Physical fidelity:** does n-fold reproduce the escape-time statistics of the corresponding Standard single-spin dynamics?
2. **Computational efficiency:** when does removing rejected attempts compensate for n-fold bookkeeping overhead?

The model is

\[
\mathcal H=-J\sum_{\langle i,j\rangle}s_i s_j-H\sum_i s_i,
\qquad s_i\in\{-1,+1\}.
\]

Runs start from all spins `+1`, use periodic boundaries on an `L×L` square lattice, and stop at the first configuration with total magnetization `M=0`. Glauber/heat-bath and Metropolis dynamics are treated separately.

## Headline results

Across the analysed campaigns there are **52 paired Standard–n-fold comparisons** representing **44 unique physical points**. With the predefined ±5% practical-equivalence criterion for

\[
R_\tau=\frac{\langle\tau\rangle_{\rm nfold}}{\langle\tau\rangle_{\rm standard}},
\]

the result is **49 PASS, 3 INCONCLUSIVE, 0 FAIL**. The three inconclusive cases are low-temperature weak-field points and are retained as precision limitations.

Performance is regime-dependent. In the tested strong-field regime (`H/J=-3`) Standard Monte Carlo is cheaper throughout the temperature sweep. At weak field (`H/J=-0.75`) n-fold becomes advantageous as the acceptance probability collapses; the largest measured speed-up is about **175.8×**, with a maximum compression of roughly **1066.7 equivalent Standard attempts per n-fold event**.

## Repository layout

```text
simulator/             validated C Standard + n-fold engine from Prompt 6
  src/                 C implementation
  include/             public headers
  tests/               C unit tests
  scripts/             simulation validation/benchmark scripts
  results/             Prompt-6 raw ensembles, summaries and figures
scripts/analysis/      Prompt-8 data contracts/statistical analysis
scripts/plotting/      final figure generation
scripts/tables/        final table generation
results/processed/     normalized and derived analysis datasets
results/metadata/      design, diagnostics and manifests
results/snapshots/     frozen quality-gated analysis snapshot
results/final_tables/  publication-ready tables
figures/               final and supplementary figures
docs/                  scientific/reproducibility documentation
tests/                 Python analysis/release tests
release/               integrity and GitHub-release metadata
```

The aggregate files in `results/legacy/prompt6/` are the immutable Prompt-8 compatibility copies of the corresponding Prompt-6 summaries. The original raw Prompt-6 ensembles and reports are preserved under `simulator/results/`.

## Quick start — build and test the C engine

### CMake

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

The executables are typically:

```text
build/simulator/ising_standard
build/simulator/ising_nfold
```

On multi-config Windows generators they may instead be under `build/simulator/Release/`.

A Makefile wrapper is also available:

```bash
make
make test
```

## Example simulation

```bash
./build/simulator/ising_standard \
  --L 32 --T 1.5 --J 1 --H -0.75 \
  --runs 1000 --seed 1234 --dynamics glauber \
  --output standard.csv

./build/simulator/ising_nfold \
  --L 32 --T 1.5 --J 1 --H -0.75 \
  --runs 1000 --seed 1234 --dynamics glauber \
  --output nfold.csv
```

For Windows/PowerShell, use the corresponding `.exe` paths.

## Quick validation of newly built executables

```bash
python simulator/scripts/run_validation.py \
  --standard-exe build/simulator/ising_standard \
  --nfold-exe build/simulator/ising_nfold \
  --quick
```

See [`simulator/README.md`](simulator/README.md) for the complete Prompt-6 validation workflow.

## Reproduce the Python analysis products

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -q
python -m scripts.reproduce_8D
```

To verify the frozen scientific snapshot and the release manifest:

```bash
python scripts/release_check.py --verify-frozen
python -m scripts.analysis.build_quality_snapshot --verify results/snapshots/snap_0cc46433731097c4
```

## Reproducibility layers

The repository deliberately preserves two levels of reproducibility:

- **Simulation level:** source code, C tests, validation scripts and the actual Prompt-6 raw ensembles are in `simulator/`.
- **Analysis level:** Prompt-8 transforms the frozen Prompt-6 summaries through explicit contracts, catalogues, quality gates and snapshot hashes before producing the final statistics, figures and tables.

The current analysis snapshot is `snap_0cc46433731097c4`.

## Final figures

The main publication figures are in `figures/final/` as PNG and vector PDF. They cover physical equivalence versus temperature and size, CPU speed-up, rejection compression, size scaling, and the relation between event compression and inverse Standard acceptance.

## Scientific interpretation

> Within the tested parameter domain, n-fold reproduces the metastable escape-time statistics of the corresponding random single-spin Standard dynamics within the predefined practical-equivalence framework, with three low-temperature weak-field points remaining statistically inconclusive. Its computational advantage is regime-dependent and becomes large when rejection removal outweighs event-bookkeeping overhead.

This does not claim trajectory-by-trajectory identity, nor does it infer equilibrium observables such as heat capacity or susceptibility from metastable first-passage data.

## Documentation

- [Scientific background](docs/scientific_background.md)
- [Methodology](docs/methodology.md)
- [Validation](docs/validation.md)
- [Performance](docs/performance.md)
- [Reproducibility](docs/reproducibility.md)
- [Results and limitations](docs/results_and_limitations.md)
- [Figures and tables](docs/figures_and_tables.md)
- [Repository layout](docs/repository_layout.md)
- [Simulator integration/provenance](docs/integration_with_simulator.md)
- [Prompt-6 simulator README](simulator/README.md)

## Release

- [Release notes](RELEASE_NOTES.md)
- [Changelog](CHANGELOG.md)
- [Citation metadata](CITATION.cff)
- [License](LICENSE)
- [GitHub publishing checklist](release/GITHUB_PUBLISHING_CHECKLIST.md)

The full `v1.0.0` release includes the simulator core; the earlier `v1.0.0-analysis` package was an intermediate analysis-only artifact and is superseded by this integrated release.
