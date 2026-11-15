# Prompt 6 — Validation run performed in this environment

This file records a **development/smoke validation**, not the final production study.

## Build and deterministic tests

Release build:

- `physics`: PASS
- `nfold`: PASS
- `smoke_standard`: PASS
- `smoke_nfold`: PASS
- `smoke_csv_standard`: PASS
- `smoke_csv_nfold`: PASS

Sanitizer build (`AddressSanitizer + UndefinedBehaviorSanitizer`):

- all 6 CTest tests: PASS
- no sanitizer failure was reported.

The deterministic tests include:

- exact all-up/all-down energies;
- 20,000 random flips with incremental-vs-full energy and magnetization checks;
- local-class / local-\(\Delta E\) consistency;
- exact class bookkeeping after n-fold events;
- geometric waiting-time regression at \(Q=0.8,0.25,0.05,0.005\);
- event-class selection frequencies;
- uniform bounded member-index sampling;
- fixed-seed reproducibility.

## End-to-end statistical smoke test

Parameters:

- `L = 8`
- `T = 1.5`
- `J = 1`
- `500` independent escapes per algorithm/case
- base seed `1234`
- stop at first `M = 0`
- practical-equivalence smoke margin: ±20%

| Dynamics | H/J | mean τ standard (MCSS) | mean τ n-fold (MCSS) | mean ratio | bootstrap 95% CI | KS D | KS p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Glauber | -3.00 | 1.4184063 | 1.4255937 | 1.0050673 | [0.98482795, 1.0257135] | 0.046 | 0.65555031 |
| Glauber | -0.75 | 33.147375 | 32.356406 | 0.97613782 | [0.90096473, 1.0607545] | 0.044 | 0.70909131 |
| Metropolis | -3.00 | 1.198125 | 1.196625 | 0.99874804 | [0.97850187, 1.0199527] | 0.040 | 0.81104102 |
| Metropolis | -0.75 | 26.678031 | 26.682437 | 1.0001652 | [0.92542908, 1.0840513] | 0.036 | 0.89698200 |

All four smoke cases passed the configured ±20% bootstrap-ratio criterion and the
`KS p >= 0.01` diagnostic.

These results do **not** replace a larger production ensemble. For the report, use a
predeclared tighter equivalence margin (for example 10%) and increase the number of
escapes until the confidence interval is sufficiently narrow.

## Development benchmark

One local benchmark was run for:

- Glauber
- `L = 16`
- `T = 1.5`
- `J = 1`
- `H = -0.75`
- `100` escapes per timing
- `5` repetitions

Median wall times:

- standard: `0.015099 s`
- n-fold: `0.00878001 s`
- observed speed-up: `1.71971x`

This timing is machine- and build-dependent and should be rerun on the machine used for
the final assignment.
