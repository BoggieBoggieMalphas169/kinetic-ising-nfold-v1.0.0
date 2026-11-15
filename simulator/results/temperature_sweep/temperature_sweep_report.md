# Prompt 6 — Temperature sweep

Fixed lattice: `L=32` (`N=1024`), `J=1.0`.

Temperatures: 0.8, 0.9, 1, 1.2, 1.5, 1.8, 2.1.

Adaptive production ensembles: 1000 escapes normally and 500 for strong-field T <= 0.8. For weak field, T=0.8 uses 150, T=0.9 uses 4000, and T=1.0 uses 10000 escapes. The exact n is recorded per row.

## Statistical equivalence

Bootstrap ±5% practical-equivalence criterion: **25 PASS, 3 INCONCLUSIVE, 0 FAIL** out of 28 points.

The exploratory two-sample KS diagnostics give **0 rejections after Holm family-wise correction at 5%**. KS non-rejection is not used as proof of equivalence.

| dynamics | H/J | T/J | runs | tau_std | tau_nfold | ratio | 95% CI | status | KS p | speed-up | attempts/event |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| glauber | -3 | 0.8 | 500 | 1.8639 | 1.86397 | 1.0000 | [0.9934, 1.0066] | PASS | 0.864 | 0.569 | 3.425 |
| glauber | -3 | 0.9 | 1000 | 1.73508 | 1.73214 | 0.9983 | [0.9939, 1.0028] | PASS | 0.433 | 0.613 | 3.135 |
| glauber | -3 | 1 | 1000 | 1.64034 | 1.6406 | 1.0002 | [0.9958, 1.0045] | PASS | 0.936 | 0.525 | 2.928 |
| glauber | -3 | 1.2 | 1000 | 1.52902 | 1.52744 | 0.9990 | [0.9950, 1.0028] | PASS | 0.573 | 0.555 | 2.660 |
| glauber | -3 | 1.5 | 1000 | 1.44663 | 1.44582 | 0.9994 | [0.9956, 1.0033] | PASS | 0.888 | 0.494 | 2.442 |
| glauber | -3 | 1.8 | 1000 | 1.41038 | 1.40754 | 0.9980 | [0.9942, 1.0017] | PASS | 0.61 | 0.460 | 2.312 |
| glauber | -3 | 2.1 | 1000 | 1.39834 | 1.39871 | 1.0003 | [0.9964, 1.0040] | PASS | 0.888 | 0.509 | 2.238 |
| glauber | -0.75 | 0.8 | 150 | 4417.26 | 3813.9 | 0.8634 | [0.7027, 1.0534] | INCONCLUSIVE | 0.0219 | 175.773 | 1066.725 |
| glauber | -0.75 | 0.9 | 4000 | 675.724 | 692.422 | 1.0247 | [0.9852, 1.0654] | INCONCLUSIVE | 0.704 | 42.638 | 314.450 |
| glauber | -0.75 | 1 | 10000 | 197.665 | 196.982 | 0.9965 | [0.9788, 1.0148] | PASS | 0.5 | 14.452 | 112.455 |
| glauber | -0.75 | 1.2 | 1000 | 60.6503 | 59.1588 | 0.9754 | [0.9539, 0.9970] | PASS | 0.2 | 4.375 | 33.349 |
| glauber | -0.75 | 1.5 | 1000 | 24.4334 | 24.3928 | 0.9983 | [0.9869, 1.0096] | PASS | 0.61 | 1.684 | 12.752 |
| glauber | -0.75 | 1.8 | 1000 | 13.9022 | 14.0148 | 1.0081 | [0.9994, 1.0170] | PASS | 0.314 | 1.318 | 7.537 |
| glauber | -0.75 | 2.1 | 1000 | 9.71084 | 9.70657 | 0.9996 | [0.9923, 1.0072] | PASS | 0.828 | 0.881 | 5.491 |
| metropolis | -3 | 0.8 | 500 | 1.74447 | 1.74807 | 1.0021 | [0.9957, 1.0085] | PASS | 0.978 | 0.516 | 3.205 |
| metropolis | -3 | 0.9 | 1000 | 1.59677 | 1.59697 | 1.0001 | [0.9959, 1.0044] | PASS | 1 | 0.481 | 2.880 |
| metropolis | -3 | 1 | 1000 | 1.48588 | 1.48569 | 0.9999 | [0.9957, 1.0040] | PASS | 0.501 | 0.438 | 2.636 |
| metropolis | -3 | 1.2 | 1000 | 1.3425 | 1.34186 | 0.9995 | [0.9957, 1.0033] | PASS | 0.685 | 0.365 | 2.312 |
| metropolis | -3 | 1.5 | 1000 | 1.21444 | 1.21367 | 0.9994 | [0.9956, 1.0031] | PASS | 0.828 | 0.462 | 2.016 |
| metropolis | -3 | 1.8 | 1000 | 1.14239 | 1.14511 | 1.0024 | [0.9988, 1.0058] | PASS | 0.288 | 0.368 | 1.838 |
| metropolis | -3 | 2.1 | 1000 | 1.10174 | 1.09893 | 0.9974 | [0.9939, 1.0011] | PASS | 0.219 | 0.364 | 1.713 |
| metropolis | -0.75 | 0.8 | 150 | 4384.52 | 3678.12 | 0.8389 | [0.6854, 1.0260] | INCONCLUSIVE | 0.532 | 166.496 | 1055.210 |
| metropolis | -0.75 | 0.9 | 4000 | 610.221 | 603.895 | 0.9896 | [0.9514, 1.0295] | PASS | 0.466 | 36.413 | 294.199 |
| metropolis | -0.75 | 1 | 10000 | 172.883 | 169.979 | 0.9832 | [0.9662, 1.0007] | PASS | 0.244 | 11.312 | 102.395 |
| metropolis | -0.75 | 1.2 | 1000 | 50.2538 | 50.2991 | 1.0009 | [0.9794, 1.0227] | PASS | 0.723 | 3.438 | 29.545 |
| metropolis | -0.75 | 1.5 | 1000 | 19.7762 | 19.896 | 1.0061 | [0.9957, 1.0167] | PASS | 0.37 | 1.348 | 10.846 |
| metropolis | -0.75 | 1.8 | 1000 | 11.1563 | 11.0902 | 0.9941 | [0.9856, 1.0030] | PASS | 0.466 | 0.757 | 6.196 |
| metropolis | -0.75 | 2.1 | 1000 | 7.60328 | 7.57255 | 0.9960 | [0.9884, 1.0032] | PASS | 0.573 | 0.571 | 4.378 |

## Empirical Arrhenius-style fit

For descriptive purposes only, `ln(<tau>) = a + Gamma_eff/T` is fitted on points with T <= 1.2. The slope is an effective finite-range slope, not asserted to be a universal barrier.

| dynamics | H/J | algorithm | Gamma_eff | R^2 | n |
|---|---:|---|---:|---:|---:|
| glauber | -3 | standard | 0.47621 | 0.99724 | 4 |
| glauber | -3 | nfold | 0.47746 | 0.99727 | 4 |
| glauber | -0.75 | standard | 10.269 | 0.97571 | 4 |
| glauber | -0.75 | nfold | 10.028 | 0.98289 | 4 |
| metropolis | -3 | standard | 0.62953 | 0.99981 | 4 |
| metropolis | -3 | nfold | 0.63524 | 0.99971 | 4 |
| metropolis | -0.75 | standard | 10.689 | 0.97528 | 4 |
| metropolis | -0.75 | nfold | 10.309 | 0.98029 | 4 |

## Speed-up crossover

- glauber, H/J=-3: no speed-up=1 crossing is bracketed in the sampled range.
- glauber, H/J=-0.75: measured speed-up crosses 1 near T/J ≈ 2.018 by linear interpolation between adjacent sampled points.
- metropolis, H/J=-3: no speed-up=1 crossing is bracketed in the sampled range.
- metropolis, H/J=-0.75: measured speed-up crosses 1 near T/J ≈ 1.677 by linear interpolation between adjacent sampled points.

The crossover values are implementation/hardware dependent and should not be interpreted as physical transition temperatures.
