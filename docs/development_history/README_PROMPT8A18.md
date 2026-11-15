# Prompt 8A.18 — Scientific analysis layer

This patch implements the first executable part of Prompt 8: a reproducible
`raw -> processed` Python pipeline shared by standard Monte Carlo and n-fold.

## What is included

```text
scripts/
└── analysis/
    ├── load_results.py      # discovery, schema normalization, validation, provenance
    ├── statistics.py        # replicate statistics + blocking diagnostics
    ├── aggregate_runs.py    # grouped scientific summaries
    └── build_processed.py   # command-line entry point
results/
├── raw/
│   ├── standard/
│   └── nfold/
├── processed/
└── metadata/
tests/
└── test_analysis.py
requirements-analysis.txt
```

## Design decisions

### Raw data are immutable

The loader reads raw CSVs recursively and never writes into `results/raw/`.
Generated tables go to `processed/` or `metadata/`.

### Standard and n-fold share one canonical schema

The analysis keeps the physically different clocks explicit:

- `time_mcss`: represented Monte Carlo time;
- `attempts`: actual conventional attempted spin updates;
- `equivalent_attempts`: represented attempted-update count;
- `events`: n-fold rejection-free events;
- `cpu_seconds`: computational time.

For conventional Monte Carlo, `equivalent_attempts = attempts`.
For n-fold, `attempts` is left missing rather than falsely equating an event with an attempted update.

### Reproducibility/provenance

Every normalized row stores `source_file`. The build also generates
`results/metadata/raw_manifest.csv`.

### Statistical scope of 8A.18

`mean_ci()` is for independent replicate-level quantities (e.g. one escape lifetime per seed).
`blocking_table()` is provided for later correlated time-series analysis, but 8A.18 does not yet claim an automatic autocorrelation-time estimate.

## Install

From the repository root:

```powershell
python -m pip install -r requirements-analysis.txt
```

## Run tests

```powershell
python -m pytest -q
```

## Build processed datasets

Place simulator CSVs below:

```text
results/raw/standard/
results/raw/nfold/
```

Then run:

```powershell
python -m scripts.analysis.build_processed
```

Outputs:

```text
results/processed/run_level.csv
results/processed/summary.csv
results/metadata/raw_manifest.csv
```

## Compatibility with earlier project stages

The standard loader accepts the existing fields such as `run`, `L`, `N`, `T`,
`J`, `H`, `dynamics`, `seed`, `stream`, `attempts`, `time_mcss`, `accepted`,
`acceptance_rate`, `final_M`, `final_E`, and `reached_M0`.

The n-fold loader additionally recognizes aliases such as `equiv_attempts`,
`equivalent_attempts`, `events`, and `nfold_events`. The alias layer is intentionally
small and explicit so schema mistakes fail loudly rather than being silently guessed.

## What is deliberately left for the next subblock

8A.18 does **not** yet implement the final standard-vs-n-fold hypothesis tests,
speed-up joins, publication figures, or equilibrium observables such as `Cv` and `chi`.
Those belong to the next analysis subblocks once this ingestion/aggregation contract is stable.
