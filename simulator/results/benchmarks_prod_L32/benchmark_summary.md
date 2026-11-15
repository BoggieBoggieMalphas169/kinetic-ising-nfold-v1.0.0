# Prompt 6 benchmark summary

Wall-clock timings are machine/compiler dependent and are kept separate from physical validation. A speed-up above 1 means n-fold is faster; below 1 means the standard algorithm is faster.

| Dynamics | H/J | standard median (s) | n-fold median (s) | standard/n-fold |
|---|---:|---:|---:|---:|
| Glauber | -3 | 0.0271474 | 0.0501548 | **0.541x** |
| Glauber | -0.75 | 0.232472 | 0.142682 | **1.629x** |
| Metropolis | -3 | 0.0208595 | 0.0505686 | **0.412x** |
| Metropolis | -0.75 | 0.169316 | 0.127508 | **1.328x** |
