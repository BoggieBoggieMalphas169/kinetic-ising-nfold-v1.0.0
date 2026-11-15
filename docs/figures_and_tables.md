# Final figures and tables

All final visual artifacts are linked to analysis snapshot `snap_0cc46433731097c4`.

## Main figures

| File stem | Scientific role |
|---|---|
| `fig01_equivalence_vs_temperature` | Shows `R_tau` and bootstrap intervals across temperature; inconclusive points remain visible. |
| `fig02_equivalence_vs_size` | Checks physical-equivalence robustness for `L=8..128`. |
| `fig03_speedup_vs_temperature` | Shows the regime-dependent CPU speed-up on a logarithmic scale. |
| `fig04_event_compression_vs_temperature` | Shows how many conventional attempts are represented by one n-fold event. |
| `fig05_speedup_vs_size` | Shows weak dependence of speed-up on lattice size at fixed temperature. |
| `fig06_compression_vs_inverse_acceptance` | Mechanistic check that compression tracks inverse Standard acceptance. |

Each figure is stored as a 300-dpi PNG and vector PDF.

## Supplementary figures

- `figS01_campaign_consistency`: independent-campaign reproducibility.
- `figS02_dynamic_contrast_preservation`: preservation of the Glauber/Metropolis contrast.

## Final tables

Files are emitted in CSV, Markdown, and LaTeX:

- `table01_headline_summary`
- `table02_physical_validation_by_dynamics`
- `table03_temperature_field_summary`
- `table04_size_robustness_summary`
- `table05_temperature_performance_summary`
- `table06_size_performance_summary`
- `tableS01_campaign_reproducibility`

## Recommended compact selection

For a short written report, the most informative combination is:

1. equivalence versus temperature;
2. equivalence versus size;
3. speed-up versus temperature;
4. compression versus inverse acceptance;
5. headline-results table.
