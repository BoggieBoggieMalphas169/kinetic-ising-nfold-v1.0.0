# Results data contract

`results/raw/` contains immutable simulator output. Never edit a raw CSV to make an analysis pass.
Fix the producer or the loader instead.

- `raw/standard/`: conventional random single-spin-update Monte Carlo.
- `raw/nfold/`: n-fold / rejection-free runs.
- `processed/run_level.csv`: normalized one-row-per-run table.
- `processed/summary.csv`: replicate-level aggregate statistics.
- `metadata/raw_manifest.csv`: provenance manifest generated from raw inputs.

The analysis keeps three distinct quantities separate:

1. `time_mcss`: represented Monte Carlo time per spin;
2. `events`: rejection-free n-fold events (when applicable);
3. `cpu_seconds`: computational timing (when recorded).

For n-fold, `equivalent_attempts` is the represented conventional attempted-update count; it is **not** renamed to `attempts`, because one n-fold event may represent many rejected conventional trials.

## Prompt 8A.19 legacy compatibility

- `legacy/prompt6/`: immutable copies of the aggregate CSV summaries produced in Prompt 6.
- `processed/prompt6_comparison_summary.csv`: versioned paired Standard-vs-n-fold table.
- `metadata/prompt6_context.json`: explicit metadata for historical files that omitted parameters.
- `metadata/prompt6_compatibility_report.csv`: provenance/completeness report.

Do not concatenate `prompt6_comparison_summary.csv` with `run_level.csv`: they have
different record levels by design.

## Prompt 8A.20 master catalog

- `metadata/experiment_design.json`: versioned declaration of expected campaign grids.
- `processed/master_comparisons.csv`: one row per observed paired comparison, with stable IDs and diagnostics.
- `processed/master_experiment_catalog.csv`: one row per unique physical point.
- `metadata/experiment_coverage.csv`: expected-vs-observed detail by campaign.
- `metadata/experiment_coverage_summary.csv`: coverage counts and fractions.
- `metadata/missing_experiments.csv`: expected points with no observation.
- `metadata/duplicate_experiments.csv`: repeated points inside the same campaign.
- `metadata/unexpected_experiments.csv`: observed points outside the declared design.

Cross-campaign repetition is intentional provenance (`cross_study_overlap`), not an error.
Do not average overlapping campaigns merely because they share an `experiment_id`.

## Prompt 8A.21 snapshots

Después de construir los datasets de 8A.19–8A.20, ejecute
`python -m scripts.analysis.build_quality_snapshot`. Un gate correcto crea un snapshot
bajo `results/snapshots/snap_<hash>/`; ese directorio es la entrada reproducible recomendada
para 8B. No edite los archivos dentro de un snapshot.

## Prompt 8B — physical validation outputs

- `processed/physical_equivalence_8B1.csv`: primary Standard-vs-n-fold equivalence records.
- `processed/campaign_consistency_summary_8B2.csv`: repeated-point reproducibility across campaigns.
- `processed/size_scaling_summary_8B3.csv`: robustness with lattice size.
- `processed/temperature_field_summary_8B4.csv`: robustness across temperature and field.
- `processed/dynamics_summary_8B5.csv`: separate Glauber/Metropolis summaries.
- `processed/physical_synthesis_8B6.csv`: final physical synthesis.

## Prompt 8C — performance outputs

- `processed/performance_records_8C.csv`: performance audit table.
- `processed/performance_temperature_8C.csv`: temperature/field performance regimes.
- `processed/performance_size_8C.csv`: size-scaling benchmarks.
- `processed/performance_synthesis_8C.csv`: performance synthesis.

## Prompt 8D — final artifacts

- `final_tables/`: CSV, Markdown, and LaTeX publication tables.
- `../figures/final/`: principal PNG/PDF figures.
- `../figures/supplementary/`: supporting figures.
- `metadata/final_artifacts_8D_manifest.csv`: SHA-256 manifest for final figures/tables.
