# Methodology and observables

## Experimental protocol

Each campaign is indexed by the physical parameters

\[
(L,N,T,J,H,\text{dynamics}),\qquad N=L^2.
\]

The two algorithms are compared at the same physical point. A run starts with all spins up and stops on first reaching `M=0`.

The principal dynamical observable is the escape time in Monte Carlo steps per spin (MCSS):

\[
\tau=\frac{\text{represented attempted updates}}{N}.
\]

## Primary physical-equivalence statistic

For paired Standard and n-fold ensembles,

\[
R_\tau=\frac{\langle\tau\rangle_{\rm nfold}}{\langle\tau\rangle_{\rm standard}}.
\]

The project predefines a practical-equivalence band

\[
0.95\le R_\tau\le1.05.
\]

The primary decision uses the 95% bootstrap confidence interval for \(R_\tau\):

- `PASS`: the interval lies completely inside `[0.95, 1.05]`;
- `INCONCLUSIVE`: the available precision is insufficient to establish practical equivalence;
- `FAIL`: a discrepancy is supported under the project criterion.

An interval need not contain exactly `1` to support practical equivalence. Statistical equality and practical equivalence are distinct questions.

## Distributional diagnostic

Where available, a two-sample Kolmogorov–Smirnov diagnostic is retained as a complementary check. Failure to reject is **not** interpreted as proof that the distributions are identical. Multiple-comparison corrections are preserved where they were part of the original campaign analysis.

## Replicates and uncertainty

Independent seeds are treated as independent replicate runs. The analysis layer includes conventional sample summaries and bootstrap intervals. For time-series observables, the infrastructure also contains blocking/binning support so that future equilibrium analyses do not silently assume independent samples.

## Performance observables

After physical validation, computational performance is studied through

\[
S=\frac{t_{\rm CPU,standard}}{t_{\rm CPU,nfold}},
\]

where `S>1` favours n-fold, and through the event-compression factor

\[
C=\frac{N_{\rm equiv\ attempts}}{N_{\rm nfold\ events}}.
\]

The elementary event-cost ratio is

\[
r_c=\frac{c_{\rm nfold,event}}{c_{\rm standard,attempt}}.
\]

This decomposition separates the cost of n-fold bookkeeping from the benefit of rejection removal.

## Dataset levels

The analysis contract distinguishes:

1. `run`: one individual simulation;
2. `run_summary`: an aggregate for one algorithm;
3. `comparison_summary`: a Standard–n-fold comparison.

Historical aggregate summaries are never concatenated with individual-run data as if they were new replicates.
