# Results and limitations

## Supported physical statement

Within the tested parameter domain, the evidence supports that the n-fold implementation reproduces the escape-time statistics of the corresponding random single-spin Standard dynamics under the project's predefined practical-equivalence framework.

Frozen result:

```text
PASS          49
INCONCLUSIVE   3
FAIL           0
```

The overall synthesis is therefore `SUPPORTED_WITH_PRECISION_LIMITS`.

## Where precision is limited

The three inconclusive temperature-sweep points are all at weak field:

| Dynamics | H/J | T/J | R_tau | Bootstrap 95% interval |
|---|---:|---:|---:|---:|
| Glauber | -0.75 | 0.8 | 0.8634 | [0.7027, 1.0534] |
| Glauber | -0.75 | 0.9 | 1.0247 | [0.9852, 1.0654] |
| Metropolis | -0.75 | 0.8 | 0.8389 | [0.6854, 1.0260] |

These intervals are too broad to establish the ±5% equivalence criterion. They are not treated as evidence of failure.

## What the project does not claim

The analysis does not establish:

- identical microscopic trajectories for matched seeds;
- equality outside the tested `L,T,H,J` domain;
- a universal performance crossover temperature;
- equilibrium heat capacity or susceptibility from first-passage summaries;
- a physical mapping from MCSS to laboratory seconds for a specific material;
- superiority of Glauber over Metropolis, or vice versa.

## Why equilibrium observables are not inferred here

The current campaigns are designed around first passage to `M=0`. A terminal value of energy or magnetization from such a stopped trajectory is not an equilibrium time series. Therefore quantities such as

\[
C_V=\frac{\langle E^2\rangle-\langle E\rangle^2}{NT^2}
\]

or

\[
\chi=\frac{\langle M^2\rangle-\langle M\rangle^2}{NT}
\]

would require a separate equilibrium-sampling protocol with proper treatment of autocorrelation.

## Natural extensions

1. Increase the number of escapes at the three inconclusive weak-field cold points.
2. Complete the deferred compiler/memory optimization and final performance regression stages.
3. Add an equilibrium-sampling branch if thermodynamic observables are desired.
4. Extend the event-driven framework to related lattice kinetic models.
