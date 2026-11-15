# Prompt 8A.20 — Master experiment catalog

This block builds the controlled experimental inventory that will feed Prompt 8B.
It works at the **comparison-summary** level and preserves the distinction established in
8A.19 between raw runs, per-algorithm summaries, and paired Standard-vs-n-fold comparisons.

## Scientific rule

The physical identity of one experiment is

```text
(dynamics, L, N=L^2, T, J, H)
```

A deterministic `experiment_id` is generated from that canonical key. A separate
`comparison_id` identifies a concrete comparison record and includes its campaign and
provenance.

The same physical point may legitimately occur in several campaigns. For example,
`L=32, T=1.5` occurs in validation, the L-scaling campaign, and the temperature sweep.
This is labelled `cross_study_overlap`; it is **not** treated as a duplicate error.

A repeated physical point **inside the same campaign** is labelled
`duplicate_within_study` and is not marked `analysis_ready` until the ambiguity is
resolved.

## Versioned experiment design

`results/metadata/experiment_design.json` records the expected Prompt 6 campaign grids.
The code does not hard-code the grid. The current declared design contains:

- validation: 4 comparison points;
- L scalability: 20 comparison points;
- temperature sweep: 28 comparison points.

That is 52 campaign records but 44 unique physical points because four
`(dynamics, H)` combinations at `L=32, T=1.5, J=1` occur in all three campaigns.

The design schema is `8A20-design-v1`; the generated master schema is `8A20.1`.

## Main outputs

Running the catalog builder produces:

```text
results/processed/master_comparisons.csv
results/processed/master_experiment_catalog.csv

results/metadata/experiment_coverage.csv
results/metadata/experiment_coverage_summary.csv
results/metadata/missing_experiments.csv
results/metadata/duplicate_experiments.csv
results/metadata/unexpected_experiments.csv
```

### `master_comparisons.csv`

One row per actual Standard-vs-n-fold comparison. It retains all 8A.19 scientific
columns and adds:

- `comparison_id`;
- `experiment_id`;
- `physical_key`;
- `physical_context_complete`;
- `catalog_status`;
- `design_status`;
- `analysis_ready`;
- `duplicate_within_study`;
- `cross_study_overlap`;
- `within_study_count`;
- `cross_study_count`.

This is the controlled comparison-level input intended for Prompt 8B. It does **not**
automatically pool overlapping campaigns.

### `master_experiment_catalog.csv`

One row per unique physical point, independent of how many campaigns measured it. It
contains inventory/provenance information rather than averaged scientific results.

### Coverage diagnostics

`experiment_coverage.csv` compares each expected campaign point against observations.
Possible statuses are:

- `observed` — exactly one record exists;
- `missing` — the design declares the point but no record exists;
- `duplicate` — more than one record exists inside the same campaign.

`unexpected_experiments.csv` records observed points not declared by the design. They are
not deleted; they are surfaced for review.

## Usage

First normalize historical Prompt 6 summaries with 8A.19:

```powershell
python -m scripts.analysis.build_compatibility
```

Then build the master catalog:

```powershell
python -m scripts.analysis.build_catalog
```

Several comparison tables can be supplied explicitly:

```powershell
python -m scripts.analysis.build_catalog `
  --comparisons results/processed/prompt6_comparison_summary.csv `
                results/processed/future_comparison_summary.csv
```

Future Prompt 7D/7E results can therefore enter the catalog without changing its code,
provided they use the 8A.19 comparison contract.

## Data-integrity behaviour

The builder deliberately refuses to create a physical ID if the physical context is
incomplete. Such a record is retained as `partial_context`, receives no `experiment_id`,
and is excluded from coverage matching.

It also rejects inconsistent lattice metadata such as `N != L^2` and invalid temperatures.
No physical parameter is inferred from campaign names.

## Tests

```powershell
pytest -q
```

The 8A.20 test suite covers deterministic IDs, cross-study overlap, within-study duplicate
detection, missing/unexpected points, partial historical context, and the complete declared
Prompt 6 grid.
