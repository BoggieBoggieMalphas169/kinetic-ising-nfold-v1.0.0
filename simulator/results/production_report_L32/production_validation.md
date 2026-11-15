# Production validation — Prompt 6
This report compares standard random-site dynamic Monte Carlo with the discrete-time n-fold implementation.
Predeclared practical-equivalence margin used here: **±5.0%** on the bootstrap 95% CI of the mean-lifetime ratio. KS is reported as a distributional diagnostic at alpha=0.01.
| Dynamics | H/J | mean tau std (MCSS) | mean tau n-fold (MCSS) | n-fold/std | 95% bootstrap CI | KS p | mean wait/event | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Glauber | -3 | 1.4458 | 1.44217 | 0.997493 | [0.993792, 1.00121] | 0.307205 | 2.43842 | **PASS** |
| Glauber | -0.75 | 24.424 | 24.233 | 0.99218 | [0.980681, 1.00374] | 0.528796 | 12.7133 | **PASS** |
| Metropolis | -3 | 1.21573 | 1.21413 | 0.998681 | [0.995104, 1.00231] | 0.753047 | 2.01737 | **PASS** |
| Metropolis | -0.75 | 19.9069 | 19.7549 | 0.992362 | [0.98112, 1.00351] | 0.822841 | 10.7961 | **PASS** |

## Interpretation
All four comparisons must be interpreted statistically rather than trajectory-by-trajectory: the two algorithms consume random variates differently. A PASS here means the observed mean-lifetime ratio is tightly contained inside the declared equivalence band and the KS diagnostic does not flag a distributional discrepancy at alpha=0.01.

The n-fold mean wait/event quantifies rejection compression: it is the average number of conventional attempted updates represented by one accepted n-fold event. This is an algorithmic quantity and is distinct from measured wall-clock speed-up.
