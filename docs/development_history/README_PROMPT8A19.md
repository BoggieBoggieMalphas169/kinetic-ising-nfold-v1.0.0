# Prompt 8A.19 — Definitive dataset contract and Prompt 6 compatibility

This block makes the analysis layer backwards-compatible with the already-generated
Prompt 6 validation campaign **without confusing aggregate summaries with raw runs**.

## The key contract decision

There are now three explicit record levels:

1. `run` — one independently simulated escape;
2. `run_summary` — statistics for one algorithm at one physical parameter point;
3. `comparison_summary` — one paired Standard-vs-n-fold experiment.

Prompt 6 files are imported only as `comparison_summary`. They are never appended to
`run_level.csv`, because their rows contain means, confidence intervals and benchmark
statistics rather than independent trajectories.

Contract version: `8A19.1`.

## Supported historical summaries

The adapter recognizes the schemas of:

- `validation_summary.csv`;
- `scalability_summary.csv`;
- `temperature_sweep_summary.csv`.

It normalizes naming differences such as:

- `mean_standard_mcss` -> `mean_tau_standard_mcss`;
- `ratio_nfold_standard` -> `lifetime_ratio_nfold_standard`;
- `ks_D` / `ks_p` -> `ks_statistic` / `ks_pvalue`;
- `mean_nfold_events` -> `mean_nfold_events_per_escape`.

The original file and row are retained through `source_file` and `source_row`.

## No hidden historical assumptions

The old `validation_summary.csv` did not store `L`, `T` or `J` in each row.  The
Prompt 6 production documentation states that this campaign used `L=32`, `T=1.5`,
`J=1`.  Rather than hard-code those values inside Python, 8A.19 stores them in an
explicit sidecar:

```text
results/metadata/prompt6_context.json
```

This makes the historical reconstruction inspectable and editable.  If the sidecar is
absent, the importer still works, but the corresponding source is marked
`contract_status=partial` instead of inventing metadata.

If sidecar metadata conflicts with a value already present in a CSV, the importer raises
`DataContractError`.

## Outputs

Place the three existing Prompt 6 CSVs under:

```text
results/legacy/prompt6/
```

Then run:

```bash
python -m scripts.analysis.build_compatibility
```

The command creates:

```text
results/processed/prompt6_comparison_summary.csv
results/metadata/prompt6_compatibility_report.csv
```

The compatibility report states, for every source file, whether its physical context is
`complete` or `partial`, which fields were missing, and which fields were supplied by the
explicit sidecar.

## Canonical comparison quantities

The normalized paired table keeps, when available:

- physical point: `dynamics, L, N, T, invT, J, H`;
- ensemble size: `runs, n_standard, n_nfold`;
- standard and n-fold lifetime mean/median/SD/CI;
- lifetime ratio and bootstrap CI;
- practical-equivalence margin/status;
- KS statistic/p-value and Holm decision;
- CPU seconds per escape and speed-up;
- standard attempted updates;
- n-fold represented attempted updates and actual rejection-free events;
- represented attempts per n-fold event;
- acceptance fraction and elementary-operation costs.

This means the future plotting and scientific-comparison layer can read one stable schema
across the original validation, L-scaling campaign, and temperature sweep.

## Important non-destructive rule

8A.19 derives only mathematically redundant missing fields, for example:

- `N = L^2`;
- `invT = 1/T`;
- lifetime ratio from the two means;
- speed-up from the two CPU times;
- n-fold represented-attempts/event from its numerator and denominator.

Recorded historical measurements are never overwritten by a recomputed value.

## Relation to 8A.18

8A.18 remains the producer of:

```text
results/processed/run_level.csv
results/processed/summary.csv
```

8A.19 adds the paired historical table:

```text
results/processed/prompt6_comparison_summary.csv
```

These files intentionally remain separate.  The next scientific-comparison block can use
the paired table directly and later regenerate an equivalent table from new raw campaigns.
