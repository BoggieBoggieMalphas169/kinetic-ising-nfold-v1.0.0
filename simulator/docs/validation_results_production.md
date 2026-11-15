# Production validation results — Prompt 6

Configuration used for the production check:

- lattice: `L=32` (`N=1024` spins);
- temperature: `T=1.5`;
- coupling: `J=1`;
- fields: `H=-3` and `H=-0.75`;
- dynamics: Glauber/heat-bath and Metropolis;
- independent escapes: `1000` per algorithm and per case;
- seed: `20260929` with one independent RNG stream per escape;
- stopping rule: first configuration with total magnetization `M=0`;
- practical equivalence band: `±5%` for the bootstrap 95% CI of the mean-lifetime ratio;
- KS diagnostic threshold: `alpha=0.01`.

## Standard versus n-fold lifetimes

| Dynamics | H/J | mean tau standard (MCSS) | mean tau n-fold (MCSS) | ratio n-fold/std | bootstrap 95% CI | KS p | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Glauber | -3 | 1.44580 | 1.44217 | 0.99749 | [0.99379, 1.00121] | 0.3072 | PASS |
| Glauber | -0.75 | 24.4240 | 24.2330 | 0.99218 | [0.98068, 1.00374] | 0.5288 | PASS |
| Metropolis | -3 | 1.21573 | 1.21413 | 0.99868 | [0.99510, 1.00231] | 0.7530 | PASS |
| Metropolis | -0.75 | 19.9069 | 19.7549 | 0.99236 | [0.98112, 1.00351] | 0.8228 | PASS |

All four cases pass the stricter `±5%` equivalence criterion. The intervals are substantially narrower than the declared margin.

The KS p-value is used here only as a distributional diagnostic; it is not treated as proof of equality. The principal equivalence criterion is the predeclared confidence interval for the physically central quantity, the mean metastable lifetime.

## n-fold event compression

The weighted average number of conventional spin-flip attempts represented by one n-fold event was:

| Dynamics | H/J | equivalent attempts / n-fold event |
|---|---:|---:|
| Glauber | -3 | 2.438 |
| Glauber | -0.75 | 12.713 |
| Metropolis | -3 | 2.017 |
| Metropolis | -0.75 | 10.796 |

This cleanly demonstrates why n-fold is especially useful in the weak-field case: the rejection-free event advances the conventional clock by roughly 11–13 attempted updates per accepted event at these parameters, compared with only about 2–2.4 in the strong-field case.

## Wall-clock benchmark on the validation machine

Benchmark setup: `L=32`, `T=1.5`, 500 escapes per timing, five repeats, median wall time reported.

| Dynamics | H/J | standard median (s) | n-fold median (s) | standard/n-fold |
|---|---:|---:|---:|---:|
| Glauber | -3 | 0.02715 | 0.05015 | 0.541x |
| Glauber | -0.75 | 0.23247 | 0.14268 | 1.629x |
| Metropolis | -3 | 0.02086 | 0.05057 | 0.412x |
| Metropolis | -0.75 | 0.16932 | 0.12751 | 1.328x |

Therefore n-fold is not universally faster. At `H=-3`, rejection is modest and class bookkeeping costs more than it saves on this machine. At `H=-0.75`, the larger rejection compression produces a real wall-clock speed-up.

These timing values are not universal physical results: they depend on CPU, compiler, optimization flags, operating system and implementation details.

## Memory and undefined behaviour

The complete CTest suite was rebuilt in Debug mode with AddressSanitizer and UndefinedBehaviorSanitizer enabled. Result:

```text
100% tests passed, 0 tests failed out of 6
```

No AddressSanitizer, leak-sanitizer or UBSan diagnostic was produced during the suite.

## Reproduction

Release tests:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

Production statistical validation:

```bash
python3 scripts/run_validation.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --outdir results/validation_prod_L32 \
  --L 32 --T 1.5 --J 1 --runs 1000 \
  --seed 20260929 \
  --equivalence-margin 0.05 \
  --strict
```

Generate the consolidated report and figures:

```bash
python3 scripts/production_report.py \
  --results results/validation_prod_L32 \
  --outdir results/production_report_L32 \
  --bootstrap 10000 \
  --margin 0.05
```

Benchmark all four cases:

```bash
python3 scripts/benchmark_suite.py \
  --standard-exe build/ising_standard \
  --nfold-exe build/ising_nfold \
  --outdir results/benchmarks_prod_L32 \
  --L 32 --T 1.5 --J 1 \
  --runs 500 --repeat 5 --seed 314159
```
