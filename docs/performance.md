# Computational performance

Performance is analysed only after the physical-equivalence stage.

## CPU speed-up

\[
S=\frac{t_{\rm CPU,standard}}{t_{\rm CPU,nfold}}.
\]

`S>1` means n-fold is faster; `S<1` means the Standard implementation is faster.

## Main result: regime dependence

There is no universal winner.

### Strong field: `H/J=-3`

Standard Monte Carlo is faster throughout the tested temperature interval `T/J=0.8..2.1` for both Glauber and Metropolis.

### Weak field: `H/J=-0.75`

At lower temperature, Standard acceptance becomes very small and n-fold gains strongly from rejection removal. The maximum measured speed-up is approximately

\[
S_{\max}\approx175.8.
\]

The strongest measured Standard advantage corresponds to `S≈0.364`, i.e. Standard is about `2.75×` faster at that point.

## Why the crossover occurs

The event-compression factor

\[
C=\frac{N_{\rm equiv}}{N_{\rm events}}
\]

reaches approximately `1066.7` in the most rejection-dominated regime. Across the temperature sweep it tracks the inverse Standard acceptance fraction closely:

\[
C\simeq\frac{1}{a_{\rm standard}}.
\]

An n-fold event is more expensive than a Standard attempted update because class bookkeeping must be maintained. The median measured elementary event-cost ratio is about `6.21`. n-fold therefore becomes advantageous only when its rejection compression is large enough to overcome that overhead.

## Empirical crossovers

A descriptive log-linear interpolation of the measured speed-up gives approximate `S=1` crossovers at weak field:

- Glauber: `T/J≈2.01`;
- Metropolis: `T/J≈1.66`.

These values are **implementation- and hardware-dependent benchmark crossovers**, not universal properties of the Ising model.

## Scaling with lattice size

At fixed `T/J=1.5`, measured CPU time per escape scales approximately as `L²` for both algorithms across `L=8..128`. The speed-up itself changes only weakly with `L`; the rejection regime is the dominant performance discriminator in the tested domain.
