# Prompt 8B.6 — Final physical synthesis

8B.6 closes the physical Standard-vs-n-fold comparison without adding a new hypothesis
test. It consolidates the validated outputs of 8B.1--8B.5 and preserves all limitations.

## Current snapshot

`snap_0cc46433731097c4`

## Main result

Across the 52 campaign-level comparisons, the predefined practical-equivalence criterion
for the escape-time mean gives:

- 49 `PASS`;
- 3 `INCONCLUSIVE`;
- 0 `FAIL`.

The three unresolved points occur only in the cold weak-field temperature sweep
(`H/J=-0.75`): Glauber at `T/J=0.8, 0.9` and Metropolis at `T/J=0.8`.
They are retained as precision limitations, not converted into discrepancies or successes.

The repeated `L=32, T/J=1.5` points are reproducible across the three campaigns; all four
size-scaling series remain robust over `L=8...128`; and the Glauber/Metropolis contrast is
preserved descriptively by n-fold at all 26 matched campaign points within 5%.

## Scientific conclusion

Within the tested domain, the evidence supports that the implemented n-fold algorithm
reproduces the escape-time statistics of the corresponding random-single-spin Standard
Monte Carlo dynamics. The conclusion is qualified by limited precision in three cold,
weak-field points; no tested point is classified as a discrepancy under the predefined
criterion.

This statement is deliberately limited to the observables and parameter ranges tested. It
does not establish exact trajectory-by-trajectory equality, equivalence for untested
parameters, or equilibrium thermodynamic-observable equivalence.

## Important methodological boundary

CPU time, speed-up and event compression are **not** used as evidence of physical
equivalence in 8B. They belong to 8C.

## Outputs

- `results/processed/physical_synthesis_8B6.csv`
- `results/metadata/physical_limitations_8B6.csv`
- `results/metadata/physical_synthesis_diagnostics_8B6.csv`

Run:

```bash
python -m scripts.analysis.build_physical_synthesis
```
