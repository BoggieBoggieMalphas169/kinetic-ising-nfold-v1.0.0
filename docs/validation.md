# Validation strategy

The validation chain is designed to answer physical correctness before discussing speed.

## 1. Data and contract checks

The analysis rejects or flags physically inconsistent records, including invalid temperature, inconsistent `N` and `L²`, impossible acceptance rates, incomplete physical context, or ambiguous duplicates within the same campaign.

Historical datasets are normalized through a versioned compatibility layer instead of being manually rewritten.

## 2. Experiment catalog and coverage

The declared campaign grids are stored in `results/metadata/experiment_design.json`. The catalog compares expected and observed points and records missing, duplicated, or unexpected experiments.

Cross-campaign repetition is preserved as provenance rather than treated as an error.

## 3. Quality gate and snapshot

A structural quality gate verifies completeness and consistency before the scientific comparison. Passing the gate creates an immutable, SHA-256-addressed analysis snapshot.

Current scientific snapshot:

```text
snap_0cc46433731097c4
```

## 4. Physical equivalence

The primary comparison is based on the bootstrap confidence interval of

\[
R_\tau=\langle\tau\rangle_{\rm nfold}/\langle\tau\rangle_{\rm standard}.
\]

Across the frozen dataset:

- 52 campaign comparison records;
- 44 unique physical points;
- 49 `PASS`;
- 3 `INCONCLUSIVE`;
- 0 `FAIL`.

The three inconclusive records occur in the low-temperature weak-field regime.

## 5. Reproducibility across campaigns

Four physical points are independently present in `validation`, `scalability_L`, and `temperature_sweep`. All four are consistent across the three campaigns; the bootstrap intervals overlap pairwise and share a common intersection containing `R_tau=1`.

## 6. Robustness with lattice size

For `L=8,16,32,64,128`, all 20 size-scaling comparison records pass the practical-equivalence criterion. The n-fold implementation reproduces the observed finite-size dependence of the escape time over the tested range.

## 7. Robustness with temperature and field

Of 28 temperature-sweep records, 25 pass and 3 remain inconclusive. No `FAIL` is observed. The inconclusive points are:

- Glauber, `H/J=-0.75`, `T/J=0.8`;
- Glauber, `H/J=-0.75`, `T/J=0.9`;
- Metropolis, `H/J=-0.75`, `T/J=0.8`.

These are reported as precision limits, not hidden or promoted to successful validation.
