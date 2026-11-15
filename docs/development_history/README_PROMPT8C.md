# Prompt 8C — Computational performance analysis

Prompt 8C starts only after Prompt 8B has assessed physical equivalence. Performance is therefore analyzed as a **separate computational question** and is never used as evidence that the two algorithms reproduce the same dynamics.

## 8C.1 — CPU speed-up

The primary performance observable is

\[
S=\frac{t_{\rm CPU,standard}}{t_{\rm CPU,nfold}}.
\]

`S>1` means n-fold is faster; `S<1` means Standard is faster. The temperature sweep is the designated source for conclusions versus `T,H`; the scalability campaign is the designated source for conclusions versus `L`. Repeated validation points are retained for provenance but are not pooled as independent measurements.

## 8C.2 — Event compression and rejection removal

The event-compression factor is

\[
C=\frac{N_{\rm equiv\ attempts}}{N_{\rm nfold\ events}}.
\]

In the temperature sweep it closely follows the inverse Standard acceptance fraction,

\[
C\simeq \frac{1}{a_{\rm standard}},
\]

which is the expected computational mechanism: one n-fold event replaces a geometrically distributed sequence of rejected/accepted conventional attempts.

## 8C.3 — Cost balance and break-even

An n-fold event is more expensive than one Standard attempt. Define

\[
r_c=\frac{c_{\rm nfold,event}}{c_{\rm standard,attempt}}.
\]

Using the measured attempt-count ratio, the break-even compression is

\[
C_{\rm break}=\frac{r_c}{N_{\rm standard\ attempts}/N_{\rm nfold\ equiv\ attempts}}.
\]

Thus n-fold wins when rejection removal is large enough to compensate for its bookkeeping overhead. The measured speed-up is independently reconstructed from these elementary costs as a consistency check.

## 8C.4 — Temperature, field and crossover

For `H/J=-3`, Standard is faster throughout the tested `T/J=0.8..2.1` range for both Glauber and Metropolis. For `H/J=-0.75`, n-fold becomes strongly advantageous at lower temperature as the Standard acceptance probability collapses. A descriptive log-linear interpolation of `S(T)` locates the measured crossover near `T/J≈2.01` for Glauber and `T/J≈1.66` for Metropolis. These are empirical crossover estimates for this implementation/hardware, not universal physical constants.

## 8C.5 — Scaling with L

At fixed `T/J=1.5`, both implementations have CPU time per escape approximately proportional to `L^2` over `L=8..128`; fitted log-log exponents are near 2. The speed-up itself varies only weakly with `L`, so the main performance discriminator in the tested domain is the rejection regime (`T,H,dynamics`), not lattice size.

## Reproduce

```powershell
python -m scripts.analysis.build_performance_analysis `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

Outputs:

- `results/processed/performance_records_8C.csv`
- `results/processed/performance_temperature_8C.csv`
- `results/processed/performance_size_8C.csv`
- `results/processed/performance_synthesis_8C.csv`
- `results/metadata/performance_diagnostics_8C.csv`

## Scientific interpretation

The project should not state simply that "n-fold is faster". The supported conclusion is regime-dependent: n-fold pays a larger bookkeeping cost per executed event, but becomes advantageous when the conventional acceptance fraction is sufficiently small that each rejection-free event replaces many attempted updates. At high acceptance or strong field in the tested range, that compression is insufficient and Standard Monte Carlo is cheaper.

## Results from the frozen analysis snapshot

Snapshot: `snap_0cc46433731097c4`.

- 52 performance records were audited; the designated temperature campaign contains 28 records and the size campaign 20.
- In the temperature sweep, n-fold is faster at 11 points and Standard at 17 points. This aggregate count is descriptive only because the performance regimes are strongly structured by field and dynamics.
- The maximum measured speed-up is `175.773x` for Glauber at `H/J=-0.75`, `T/J=0.8`.
- The strongest measured Standard advantage is `2.747x` for Metropolis at `H/J=-3`, `T/J=2.1` (`S=0.3641`).
- The largest event compression in the temperature sweep is `1066.7` equivalent attempts per n-fold event.
- The median n-fold event/Standard-attempt elementary cost ratio is about `6.21`, explaining why modest compression is insufficient to make n-fold faster.
- The mechanistic cost decomposition reconstructs the measured speed-up to floating-point precision for the aggregated benchmark data.
- Across the temperature sweep, `C/(1/a_standard)` differs from unity by at most about `3.92%`, supporting the rejection-removal interpretation.

Empirical crossover estimates (`S=1`) within the tested grid are approximately `T/J=2.006` for Glauber at `H/J=-0.75` and `T/J=1.655` for Metropolis at the same field. No crossover is observed for `H/J=-3`, where Standard remains faster throughout the tested range.

At `T/J=1.5`, fitted CPU-scaling exponents against `L` lie close to 2 for both algorithms. The speed-up exponent is small (`-0.033` to `-0.057`), showing that the speed-up changes weakly with lattice size compared with its dependence on the rejection regime.

The accumulated test suite reports `60 passed`.
