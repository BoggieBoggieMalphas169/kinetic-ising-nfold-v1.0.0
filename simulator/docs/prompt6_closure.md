# Cierre del Prompt 6 — Validación completa

El Prompt 6 queda cerrado con cuatro niveles de validación complementarios.

## 1. Correctitud física y algorítmica

Se comprueban la Hamiltoniana, la magnetización incremental, `Delta E`, las probabilidades
Metropolis/Glauber, las 10 clases locales, la actualización incremental de clases, la
selección ponderada de clase y el reloj geométrico discreto del n-fold.

Los tests unitarios y de integración se ejecutan mediante CTest. La compilación normal y
la compilación con AddressSanitizer + UndefinedBehaviorSanitizer superan 6/6 tests.

## 2. Validación de producción a L=32, T=1.5

Con 1000 escapes por algoritmo y caso, las cuatro combinaciones
Glauber/Metropolis × `H/J=-3,-0.75` muestran compatibilidad estándar ↔ n-fold bajo el
criterio de equivalencia práctica del proyecto. Esto valida el punto de referencia antes
de estudiar escalabilidad o temperatura.

## 3. Escalabilidad con L

Para `L = 8,16,32,64,128` a `T=1.5` se verificó que la equivalencia estadística se mantiene
al crecer la red. En el intervalo medido, el tiempo por escape escala aproximadamente como
`L^2`, es decir, aproximadamente lineal con `N=L^2`, y el coste por operación elemental
permanece aproximadamente constante. La memoria de ambas implementaciones es `O(N)`;
el n-fold actual usa más memoria por su almacenamiento simple `members[10*N]`.

## 4. Barrido de temperatura

A `L=32` se estudia `T/J = 0.8,0.9,1.0,1.2,1.5,1.8,2.1` para las dos dinámicas y los dos
campos. De 28 comparaciones, 25 satisfacen directamente el criterio bootstrap ±5 %, tres
son estadísticamente inconclusas por precisión limitada en el régimen frío de campo débil,
y ninguna queda clasificada como discrepancia (`FAIL`). Tras corrección de Holm, los
diagnósticos KS producen 0 rechazos al 5 %.

El resultado computacional central aparece con claridad: para `H/J=-3` el n-fold no es
más rápido en el rango estudiado, mientras que para `H/J=-0.75` el beneficio crece
rápidamente al disminuir T. A `T/J=0.8` se observan speed-ups de aproximadamente 176×
(Glauber) y 166× (Metropolis), junto con más de mil intentos convencionales equivalentes
por evento n-fold. A temperaturas altas el bookkeeping vuelve a dominar y el speed-up cae
por debajo de 1.

## Conclusión técnica

La evidencia reunida permite sostener una conclusión más precisa que "n-fold es más
rápido":

> La implementación n-fold reproduce la dinámica de single-spin-flip definida por
> Metropolis o Glauber a nivel estadístico, sustituyendo secuencias de rechazos por un
> tiempo de espera geométrico. Su ventaja depende del régimen: puede ser peor que el
> Monte Carlo convencional cuando la aceptación es alta, pero se vuelve muy grande en
> el régimen metaestable de baja aceptación.

Esta conclusión está respaldada por tests deterministas, validación estadística,
escalabilidad en tamaño, barrido térmico, benchmark de CPU y sanitizers. Las tres
comparaciones frías marcadas `INCONCLUSIVE` se conservan explícitamente como limitación
de precisión del algoritmo de referencia, no se ocultan ni se convierten artificialmente
en resultados positivos.

## Material principal

- `docs/validation.md`
- `docs/validation_results_production.md`
- `docs/scalability_L.md`
- `docs/temperature_sweep.md`
- `results/production_report_L32/`
- `results/scalability_L/`
- `results/temperature_sweep/`
- `scripts/temperature_sweep.py`

Con esto, el bloque 6 se considera terminado y preparado para usarse como sección de
validación/metodología de la memoria y como evidencia reproducible dentro del repositorio.
