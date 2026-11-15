# Monte Carlo cinético de Ising: Standard frente a n-fold way

[English version](README.md)

Repositorio reproducible de física computacional para estudiar el escape metaestable del modelo de Ising ferromagnético bidimensional. Esta release integra tanto el **motor C validado** como la **capa Python de análisis y reproducibilidad** usada para comparar Monte Carlo Standard de actualización aleatoria de un solo espín con el algoritmo **n-fold way** libre de rechazos.

**Release:** `v1.0.0` · **Fecha:** 2026-09-30 · **Snapshot de análisis:** `snap_0cc46433731097c4`

## Pregunta científica

Separamos deliberadamente dos cuestiones:

1. **Fidelidad física:** ¿reproduce n-fold las estadísticas del tiempo de escape de la dinámica Standard correspondiente?
2. **Eficiencia computacional:** ¿en qué regímenes eliminar rechazos compensa el coste adicional de bookkeeping de n-fold?

El Hamiltoniano es

\[
\mathcal H=-J\sum_{\langle i,j\rangle}s_i s_j-H\sum_i s_i,
\qquad s_i\in\{-1,+1\}.
\]

Las simulaciones parten de todos los espines `+1`, usan condiciones periódicas en una red cuadrada `L×L` y terminan al alcanzar por primera vez `M=0`. Se estudian por separado las dinámicas Glauber/heat-bath y Metropolis.

## Resultado principal

Hay **52 comparaciones Standard–n-fold** correspondientes a **44 puntos físicos únicos**. Con el criterio predefinido de equivalencia práctica de ±5 % para

\[
R_\tau=\frac{\langle\tau\rangle_{\rm nfold}}{\langle\tau\rangle_{\rm standard}},
\]

obtenemos **49 PASS, 3 INCONCLUSIVE y 0 FAIL**. Los tres casos inconclusos se concentran en baja temperatura y campo débil y se conservan como limitaciones de precisión.

El rendimiento depende del régimen. Para `H/J=-3`, Standard es más barato en todo el barrido térmico probado. Para `H/J=-0.75`, n-fold se vuelve ventajoso al caer la aceptación; el máximo speed-up medido es de aproximadamente **175.8×**, con una compresión máxima de unas **1066.7 tentativas Standard equivalentes por evento n-fold**.

## Estructura

```text
simulator/             motor C Standard + n-fold validado en Prompt 6
  src/                 implementación C
  include/             cabeceras
  tests/               tests C
  scripts/             validación y benchmarks del simulador
  results/             ensembles brutos, resúmenes y figuras de Prompt 6
scripts/analysis/      análisis estadístico y contratos de Prompt 8
scripts/plotting/      generación de figuras finales
scripts/tables/        generación de tablas
results/processed/     datos normalizados y derivados
results/metadata/      diseño, diagnósticos y manifiestos
results/snapshots/     snapshot científico congelado
figures/               figuras finales y suplementarias
docs/                  documentación científica
tests/                 tests Python de análisis/release
release/               metadatos e integridad de la release
```

## Compilar y probar el motor C

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

Los ejecutables suelen quedar en:

```text
build/simulator/ising_standard
build/simulator/ising_nfold
```

En Windows con generadores multi-config pueden quedar en `build/simulator/Release/`.

También puede usarse:

```bash
make
make test
```

## Simulación rápida

```bash
./build/simulator/ising_standard \
  --L 32 --T 1.5 --J 1 --H -0.75 \
  --runs 1000 --seed 1234 --dynamics glauber \
  --output standard.csv

./build/simulator/ising_nfold \
  --L 32 --T 1.5 --J 1 --H -0.75 \
  --runs 1000 --seed 1234 --dynamics glauber \
  --output nfold.csv
```

## Reproducir el análisis

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -q
python -m scripts.reproduce_8D
```

Verificación criptográfica:

```bash
python scripts/release_check.py --verify-frozen
python -m scripts.analysis.build_quality_snapshot --verify results/snapshots/snap_0cc46433731097c4
```

## Dos capas de reproducibilidad

- `simulator/` conserva código C, tests, scripts y los datos brutos reales del Prompt 6.
- Prompt 8 conserva contratos de datos, análisis, quality gate, snapshot, figuras y tablas finales.

Los resúmenes de `results/legacy/prompt6/` son las copias de compatibilidad usadas por Prompt 8; los datasets originales completos permanecen en `simulator/results/`.

## Interpretación

> Dentro del dominio de parámetros estudiado, n-fold reproduce las estadísticas del tiempo de escape de la dinámica Standard aleatoria de un solo espín dentro del criterio de equivalencia práctica predefinido, con tres puntos fríos de campo débil todavía inconclusos por precisión estadística. Su ventaja computacional depende del régimen y crece cuando la eliminación de rechazos supera el coste de bookkeeping.

No se afirma identidad trayectoria a trayectoria ni se deducen observables termodinámicos de equilibrio a partir de datos de primer paso metaestable.

Consulta [`simulator/README.md`](simulator/README.md) para la validación original y [`docs/reproducibility.md`](docs/reproducibility.md) para el flujo completo.
