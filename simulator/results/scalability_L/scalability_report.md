# Lattice-size scalability — Prompt 6

This study varies **only lattice size L**. Temperature is fixed at `T=1.5`, coupling at `J=1`, and no temperature sweep is included. The baseline ensemble uses `1000` independent escapes per algorithm and point. For the statistically broader weak-field points at `L=8` and `L=16`, the ensemble was refined to `5000` escapes so that finite-sample noise is not confused with a size-scaling effect.

## Statistical equivalence while scaling L

| Dynamics | H/J | L | runs/alg. | tau std | tau n-fold | ratio n-fold/std | 95% bootstrap CI | ±5% pass |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| Glauber | -3 | 8 | 1000 | 1.43087 | 1.44858 | 1.01237 | [0.99701, 1.02751] | PASS |
| Glauber | -3 | 16 | 1000 | 1.44485 | 1.44434 | 0.99965 | [0.99190, 1.00719] | PASS |
| Glauber | -3 | 32 | 1000 | 1.44799 | 1.44663 | 0.99906 | [0.99521, 1.00297] | PASS |
| Glauber | -3 | 64 | 1000 | 1.44631 | 1.44466 | 0.99886 | [0.99694, 1.00080] | PASS |
| Glauber | -3 | 128 | 1000 | 1.44463 | 1.44536 | 1.00050 | [0.99953, 1.00147] | PASS |
| Glauber | -0.75 | 8 | 5000 | 34.3083 | 34.2888 | 0.99943 | [0.97494, 1.02447] | PASS |
| Glauber | -0.75 | 16 | 5000 | 25.3586 | 25.0786 | 0.98896 | [0.97839, 0.99987] | PASS |
| Glauber | -0.75 | 32 | 1000 | 24.579 | 24.5586 | 0.99917 | [0.98809, 1.01071] | PASS |
| Glauber | -0.75 | 64 | 1000 | 24.3191 | 24.3015 | 0.99928 | [0.99365, 1.00498] | PASS |
| Glauber | -0.75 | 128 | 1000 | 24.2644 | 24.233 | 0.99871 | [0.99586, 1.00156] | PASS |
| Metropolis | -3 | 8 | 1000 | 1.20437 | 1.20637 | 1.00166 | [0.98679, 1.01606] | PASS |
| Metropolis | -3 | 16 | 1000 | 1.21069 | 1.20909 | 0.99868 | [0.99141, 1.00614] | PASS |
| Metropolis | -3 | 32 | 1000 | 1.21702 | 1.21485 | 0.99821 | [0.99463, 1.00187] | PASS |
| Metropolis | -3 | 64 | 1000 | 1.21552 | 1.21531 | 0.99983 | [0.99807, 1.00173] | PASS |
| Metropolis | -3 | 128 | 1000 | 1.21665 | 1.21656 | 0.99993 | [0.99901, 1.00087] | PASS |
| Metropolis | -0.75 | 8 | 5000 | 27.9323 | 28.2297 | 1.01065 | [0.98567, 1.03634] | PASS |
| Metropolis | -0.75 | 16 | 5000 | 20.5035 | 20.4485 | 0.99732 | [0.98709, 1.00779] | PASS |
| Metropolis | -0.75 | 32 | 1000 | 19.7221 | 19.9138 | 1.00972 | [0.99822, 1.02115] | PASS |
| Metropolis | -0.75 | 64 | 1000 | 19.7337 | 19.6503 | 0.99578 | [0.98982, 1.00146] | PASS |
| Metropolis | -0.75 | 128 | 1000 | 19.7368 | 19.7734 | 1.00186 | [0.99902, 1.00470] | PASS |

## Computational scalability

CPU values below are the C program's accumulated `clock()` time inside each escape, so process-launch overhead is excluded. `speed-up > 1` means n-fold is faster.

| Dynamics | H/J | L | std CPU/escape (ms) | n-fold CPU/escape (ms) | speed-up | attempts/event n-fold |
|---|---:|---:|---:|---:|---:|---:|
| Glauber | -3 | 8 | 0.003762 | 0.006475 | 0.581x | 2.436 |
| Glauber | -3 | 16 | 0.013507 | 0.02461 | 0.549x | 2.430 |
| Glauber | -3 | 32 | 0.049384 | 0.093935 | 0.526x | 2.439 |
| Glauber | -3 | 64 | 0.202572 | 0.391676 | 0.517x | 2.439 |
| Glauber | -3 | 128 | 0.85108 | 1.63305 | 0.521x | 2.440 |
| Glauber | -0.75 | 8 | 0.0396756 | 0.0196832 | 2.016x | 13.565 |
| Glauber | -0.75 | 16 | 0.126921 | 0.0692272 | 1.833x | 12.649 |
| Glauber | -0.75 | 32 | 0.503699 | 0.262033 | 1.922x | 12.819 |
| Glauber | -0.75 | 64 | 1.95947 | 1.07071 | 1.830x | 12.779 |
| Glauber | -0.75 | 128 | 8.06059 | 4.48317 | 1.798x | 12.782 |
| Metropolis | -3 | 8 | 0.002824 | 0.006124 | 0.461x | 2.002 |
| Metropolis | -3 | 16 | 0.01057 | 0.024006 | 0.440x | 2.011 |
| Metropolis | -3 | 32 | 0.040413 | 0.102958 | 0.393x | 2.016 |
| Metropolis | -3 | 64 | 0.164306 | 0.409854 | 0.401x | 2.016 |
| Metropolis | -3 | 128 | 0.650368 | 1.63713 | 0.397x | 2.018 |
| Metropolis | -0.75 | 8 | 0.0290274 | 0.0197822 | 1.467x | 11.716 |
| Metropolis | -0.75 | 16 | 0.0851676 | 0.0668412 | 1.274x | 10.758 |
| Metropolis | -0.75 | 32 | 0.323371 | 0.266389 | 1.214x | 10.856 |
| Metropolis | -0.75 | 64 | 1.3768 | 1.07474 | 1.281x | 10.829 |
| Metropolis | -0.75 | 128 | 5.75913 | 4.42522 | 1.301x | 10.860 |

## Memory scaling

For the current 64-bit build, the dominant explicitly allocated arrays require approximately `33 N` bytes for the standard engine and `122 N` bytes for n-fold. These estimates exclude allocator metadata and small fixed-size structs.

| L | N | standard approx. | n-fold approx. | n-fold/standard |
|---:|---:|---:|---:|---:|
| 8 | 64 | 2.062 KiB | 7.625 KiB | 3.697x |
| 16 | 256 | 8.250 KiB | 30.500 KiB | 3.697x |
| 32 | 1024 | 33.000 KiB | 122.000 KiB | 3.697x |
| 64 | 4096 | 132.000 KiB | 488.000 KiB | 3.697x |
| 128 | 16384 | 528.000 KiB | 1952.000 KiB | 3.697x |

The larger n-fold memory footprint comes mainly from `members[10*N]`, plus `position[N]` and `class_of[N]`. This is a deliberate simple/fast bookkeeping layout, not a physical requirement of the n-fold algorithm; it can be reduced in a later optimization if very large L is targeted.

## Empirical scaling exponents

A log-log fit `CPU/escape = C L^a` over `L=8..128` gives:

| Dynamics | H/J | a standard | a n-fold |
|---|---:|---:|---:|
| Glauber | -3 | 1.955 | 1.995 |
| Glauber | -0.75 | 1.928 | 1.961 |
| Metropolis | -3 | 1.965 | 2.022 |
| Metropolis | -0.75 | 1.928 | 1.962 |

Thus, in this measured regime the complete computational cost is very close to `L^2`, i.e. approximately `O(N)`. This is reinforced by the fitted exponents of the per-operation cost, which lie close to zero: from about `-0.05` to `+0.05`. The local standard attempt and local n-fold event therefore remain essentially constant-cost as the lattice grows; the dominant growth comes from processing a number of sites/events proportional to system size.

The result should be described as an **empirical implementation-scaling result over this L range**, not as a universal critical exponent.

## Main scalability conclusion

The physics and the computational behaviour remain stable as the lattice grows from 64 to 16384 spins. All 20 lifetime-equivalence checks pass. The n-fold speed advantage is controlled much more strongly by the rejection rate than by L itself: for `H=-3` it remains slower than standard MC, whereas for `H=-0.75` it remains faster across the full measured size range. In the weak-field Glauber case the measured speed-up is roughly `1.8–2.0x`; for weak-field Metropolis it is roughly `1.2–1.5x`.

At the same time, the n-fold implementation pays a memory premium of about `3.70x` in its current bookkeeping layout. That trade-off is visible and documented rather than hidden.

## Interpretation rule

Do not interpret the empirical CPU-vs-L power-law fits as universal physical exponents. The time to reach `M=0` itself changes with finite system size, and initialization is O(N). The most implementation-specific scalability diagnostics are therefore CPU per conventional attempt, CPU per n-fold event, memory O(N), and the measured end-to-end speed-up.

The file `scaling_fits.csv` records log-log fits only as compact numerical summaries of this measured range.
