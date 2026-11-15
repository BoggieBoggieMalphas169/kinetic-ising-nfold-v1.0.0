# Validation plan

This document defines the acceptance tests for the standard random-site dynamic Monte Carlo
and the discrete-time n-fold implementation.

## 1. Deterministic physics invariants

For the Hamiltonian

\[
\mathcal H=-J\sum_{\langle i,j\rangle}s_i s_j-H\sum_i s_i
\]

with a periodic square lattice and \(N=L^2\),

- all spins \(+1\): \(E=-2JN-HN,\; M=N\);
- all spins \(-1\): \(E=-2JN+HN,\; M=-N\);
- one flip: \(\Delta E_i=2s_i(J\sum_{j\in nn(i)}s_j+H)\);
- magnetization update: \(M' = M-2s_i\).

`test_physics` executes 20,000 random flips and verifies that the incremental energy
and magnetization remain equal to full recomputation.

## 2. Ten local spin classes

The zero-based class convention is

| class | spin | number of up neighbours |
|---:|:---:|---:|
| 0 | +1 | 4 |
| 1 | +1 | 3 |
| 2 | +1 | 2 |
| 3 | +1 | 1 |
| 4 | +1 | 0 |
| 5 | -1 | 4 |
| 6 | -1 | 3 |
| 7 | -1 | 2 |
| 8 | -1 | 1 |
| 9 | -1 | 0 |

The invariant is

\[
\sum_{k=0}^{9}n_k=N.
\]

`test_nfold` checks after every event that every site is in exactly one class, that
`class_of`, `position` and `members` are mutually consistent, and that a full
reclassification produces the same class counts.

## 3. Transition probabilities

Metropolis:

\[
p_M(\Delta E)=\min(1,e^{-\beta\Delta E}).
\]

Glauber / heat bath:

\[
p_G(\Delta E)=\frac{1}{1+e^{\beta\Delta E}}.
\]

The code uses numerically stable branches to avoid overflow for large \(|\beta\Delta E|\).

## 4. Discrete n-fold clock

For the current configuration,

\[
Q=\frac{1}{N}\sum_k n_kp_k.
\]

The number \(m\ge1\) of conventional attempted updates represented by one n-fold event is

\[
m=\left\lfloor\frac{\ln r}{\ln(1-Q)}\right\rfloor+1,\qquad r\in(0,1].
\]

Therefore,

\[
P(m=k)=(1-Q)^{k-1}Q,
\quad
E[m]=\frac1Q,
\quad
Var(m)=\frac{1-Q}{Q^2}.
\]

`test_nfold` samples 250,000 waiting times for each of
\(Q=0.8,0.25,0.05,0.005\) and compares empirical mean/variance with these values.

## 5. Event-class selection

Conditional on an accepted event,

\[
P(k\mid\text{event})=
\frac{n_kp_k}{\sum_j n_jp_j}.
\]

`test_nfold` performs a fixed-seed Monte Carlo regression test against a synthetic
10-class distribution.

## 6. End-to-end statistical equivalence

Standard and n-fold trajectories are **not expected to be identical for the same seed**.
They consume random numbers differently. The requirement is equality in distribution of
physical observables and escape times.

Use:

```bash
python scripts/run_validation.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --L 16 --T 1.5 --runs 1000
```

The full suite runs both Glauber and Metropolis at \(H=-3J\) and \(H=-0.75J\).

`compare_escape_times.py` reports:

- mean, median and standard deviation of \(\tau\) in MCSS;
- the n-fold/standard mean-lifetime ratio;
- a non-parametric bootstrap 95% confidence interval for that ratio;
- a two-sample Kolmogorov-Smirnov diagnostic.

The default `20%` practical-equivalence margin is intentionally a smoke-test threshold.
For final reported results, choose the margin *before* running the production ensemble and
increase the number of escapes enough to make the confidence interval informative.
A 10% margin with at least 1000 escapes per case is a reasonable stricter starting point,
but the required sample size depends on the variance of the measured lifetime.

## 7. Benchmarking

Use wall-clock benchmarking separately from physical validation:

```bash
python scripts/benchmark.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --L 32 --T 1.5 --H -0.75 --runs 200 --repeat 5
```

Report both:

\[
S_{\rm CPU}=t_{\rm standard}/t_{\rm nfold}
\]

and the algorithmic event compression

\[
S_{\rm events}=N_{\rm attempts}^{std}/N_{\rm events}^{nfold}.
\]

Do not assume n-fold is always faster: when rejection rates are low, its bookkeeping can
cost more than it saves.

## 8. Memory and undefined-behaviour checks

GCC/Clang:

```bash
cmake -S . -B build-sanitize \
  -DCMAKE_BUILD_TYPE=Debug \
  -DISING_ENABLE_SANITIZERS=ON
cmake --build build-sanitize
ctest --test-dir build-sanitize --output-on-failure
```

The sanitizer build enables AddressSanitizer and UndefinedBehaviorSanitizer together with
`-fno-omit-frame-pointer`.

## 9. Acceptance checklist

A release candidate passes this block when:

1. C unit tests pass.
2. CSV invariants pass.
3. Sanitizers report no memory/UB errors.
4. Incremental energy/magnetization equal full recomputation.
5. Incremental n-fold classes equal full reconstruction.
6. Waiting-time statistics agree with the geometric law.
7. Event-class frequencies agree with \(n_kp_k/\sum_jn_jp_j\).
8. Standard and n-fold escape-time ensembles are statistically compatible under a
   predeclared practical equivalence margin.
9. Benchmarks are reported independently of physics claims.

## 10. Production validation status

The validation was subsequently run at `L=32`, `T=1.5`, `J=1`, with 1000 independent
escapes per algorithm for all four combinations of Glauber/Metropolis and
`H=-3,-0.75`. A stricter `±5%` practical-equivalence band was used and all four cases
passed. See `docs/validation_results_production.md` and the raw data under
`results/validation_prod_L32/`.
