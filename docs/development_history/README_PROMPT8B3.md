# Prompt 8B.3 — Robustez de la equivalencia con el tamaño de red L

## Objetivo

Este subbloque estudia exclusivamente la campaña `scalability_L` del snapshot verificado
`snap_0cc46433731097c4`. La pregunta física es si la equivalencia Standard ↔ n-fold para
el tiempo de escape metaestable se conserva al aumentar el tamaño de la red.

No se usan tiempos de CPU, speed-up ni coste por evento; esas magnitudes pertenecen a 8C.

## Diseño analizado

Se usan 20 comparaciones:

- dinámicas: Glauber y Metropolis;
- campos: `H/J=-3` y `H/J=-0.75`;
- `T/J=1.5`, `J=1`;
- `L=8,16,32,64,128`, es decir `N=64,...,16384`.

Cada una de las cuatro series contiene cinco tamaños de red.

## Criterio de robustez

Una serie se clasifica como `ROBUST_ACROSS_TESTED_L` cuando:

1. todos sus puntos conservan `equivalence_status_8b = PASS`;
2. todos los IC bootstrap de `R_tau` están completamente dentro de la banda de
   equivalencia práctica predeclarada `[0.95,1.05]`;
3. no existen registros duplicados para un mismo tamaño dentro de la serie.

La pendiente de `R_tau` frente a `log2(L)` se conserva solamente como diagnóstico
descriptivo de deriva por duplicación de L. No se interpreta como exponente crítico ni
como test formal de tendencia.

## Resultado

Las cuatro series son robustas:

```text
size series                         4
ROBUST_ACROSS_TESTED_L              4
INCONCLUSIVE_AT_SOME_L              0
DISCREPANCY_AT_SOME_L               0

scalability records                20
PASS                               20
INCONCLUSIVE                        0
FAIL                                0
IC completamente en ±5 %          20
IC que contienen exactamente 1     19
```

Por tanto, dentro del rango ensayado `8 <= L <= 128`, no aparece pérdida de equivalencia
práctica al aumentar la red.

## Resumen por serie

| Dinámica | H/J | max |R_tau-1| | span R_tau | deriva por duplicación de L | estado |
|---|---:|---:|---:|---:|---|
| Glauber | -3.00 | 1.237 % | 1.351 pp | -0.245 pp/doubling | ROBUST_ACROSS_TESTED_L |
| Glauber | -0.75 | 1.104 % | 1.048 pp | +0.089 pp/doubling | ROBUST_ACROSS_TESTED_L |
| Metropolis | -3.00 | 0.179 % | 0.345 pp | -0.023 pp/doubling | ROBUST_ACROSS_TESTED_L |
| Metropolis | -0.75 | 1.065 % | 1.487 pp | -0.191 pp/doubling | ROBUST_ACROSS_TESTED_L |

`pp` significa puntos porcentuales del cociente `R_tau`.

La mayor desviación puntual respecto de `R_tau=1` es aproximadamente 1.237 %, muy por
debajo del margen práctico ±5 % usado en el proyecto.

## Igualdad exacta no es el criterio

19 de los 20 intervalos contienen `R_tau=1`. El único que no lo contiene es
Glauber, `H/J=-0.75`, `L=16`, con aproximadamente:

```text
R_tau = 0.988958
IC95 = [0.978387, 0.999870]
```

Este intervalo queda completamente dentro de `[0.95,1.05]`, por lo que sostiene
**equivalencia práctica** aunque la estimación resuelva una pequeña diferencia respecto de
la igualdad exacta. Esto mantiene la distinción metodológica fijada en 8B.1.

## Dependencia física con L

El objetivo principal de 8B.3 no es inferir una ley de escala para `tau`, pero el dataset
permite comprobar que Standard y n-fold responden de forma muy parecida al cambio de L.

Para `H/J=-3`, el tiempo medio de escape en MCSS es casi plano en el intervalo probado.
Para `H/J=-0.75` aparece una dependencia de tamaño mucho más visible: al pasar de L=8 a
L=128, el cociente `tau(L=128)/tau(L=8)` es aproximadamente:

```text
Glauber:
    Standard  0.70725
    n-fold    0.70673

Metropolis:
    Standard  0.70659
    n-fold    0.70045
```

Lo relevante para este bloque es que ambos algoritmos siguen prácticamente la misma
respuesta de tamaño. Como diagnóstico descriptivo, la máxima diferencia entre sus
pendientes de `log(tau)` frente a `log2(L)` es aproximadamente 0.00244.

No se interpreta esta pendiente como exponente termodinámico; simplemente comprueba que
la dependencia finita con L no se deforma apreciablemente al reemplazar Standard por
n-fold.

## Archivos añadidos

```text
scripts/analysis/size_scaling_robustness.py
scripts/analysis/build_size_scaling.py

results/processed/size_scaling_records_8B3.csv
results/processed/size_scaling_summary_8B3.csv
results/metadata/size_scaling_diagnostics_8B3.csv
```

## Ejecución

```powershell
python -m scripts.analysis.build_size_scaling `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

## Tests

La batería acumulada tras 8B.3 es:

```text
39 passed
```

Los nuevos tests verifican que una serie completamente equivalente se clasifica como
robusta, que un punto inconcluso se conserva como tal, que un FAIL produce discrepancia,
que los duplicados de tamaño se rechazan y que no se pueden mezclar snapshots.

## Conclusión de 8B.3

Con los datos actuales, la equivalencia física Standard ↔ n-fold es robusta frente al
tamaño en las cuatro series estudiadas y en todo el rango `L=8...128`. Esta conclusión
está limitada al observable y protocolo del proyecto (tiempo de primer paso hasta M=0) y
al rango de parámetros ensayado; no afirma equivalencia universal para cualquier L o
cualquier observable.
