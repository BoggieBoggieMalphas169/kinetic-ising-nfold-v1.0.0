# Prompt 6 — Barrido de temperatura

## Objetivo

Este bloque final mantiene fija la red en `L=32` (`N=1024`) y `J=1`, y estudia
cómo cambian la vida metaestable y el coste computacional al variar la temperatura.
El barrido se realiza para las dos dinámicas implementadas (Glauber/heat-bath y
Metropolis) y para los dos campos de referencia (`H/J=-3` y `H/J=-0.75`).

Temperaturas:

`T/J = 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.1`.

La comparación estándar ↔ n-fold se hace sobre ensembles independientes. No se exige
la misma trayectoria microscópica; se exige compatibilidad estadística de las vidas de
escape y, simultáneamente, se mide el ahorro computacional del algoritmo rejection-free.

## Tamaños de muestra

La distribución de la vida metaestable se vuelve muy ancha a baja temperatura y campo
débil. Por eso se usa un muestreo adaptativo y se conserva el número exacto de escapes
en los CSV:

- campo fuerte `H/J=-3`: 500 escapes en `T=0.8` y 1000 en el resto;
- campo débil `H/J=-0.75`: 150 escapes en `T=0.8`, 4000 en `T=0.9`, 10000 en
  `T=1.0` y 1000 en el resto.

El punto `T=0.8`, campo débil, se deja deliberadamente con menor precisión: es justamente
el régimen donde el Monte Carlo convencional se vuelve muy caro. No se truncan escapes
para forzar un resultado favorable.

## Equivalencia estadística

El criterio principal de equivalencia práctica es que el intervalo bootstrap del 95 %
para

`<tau>_nfold / <tau>_standard`

quede completamente dentro de `[0.95, 1.05]`.

Resultados globales del barrido:

- **25/28 PASS**;
- **3/28 INCONCLUSIVE**;
- **0/28 FAIL**.

`INCONCLUSIVE` significa que el intervalo es demasiado ancho para quedar completamente
contenido en ±5 %, pero todavía solapa la banda de equivalencia. Los tres casos son del
régimen frío y de campo débil: Glauber a `T=0.8` y `T=0.9`, y Metropolis a `T=0.8`.
No hay ningún punto cuyo intervalo quede enteramente fuera de la banda de equivalencia.

Como diagnóstico secundario se usa un test KS de dos muestras. Tras corrección de Holm
para controlar el error familiar al 5 %, hay **0 rechazos**. Esta ausencia de rechazo no
se interpreta como demostración de equivalencia; únicamente sirve como comprobación
adicional de que no aparece una discrepancia distributiva sistemática evidente.

## Dependencia del rendimiento con T

### Campo fuerte: H/J = -3

El n-fold no compensa su bookkeeping adicional en el intervalo estudiado. El speed-up
`CPU_standard / CPU_nfold` permanece por debajo de 1:

| T/J | Glauber | Metropolis |
|---:|---:|---:|
| 0.8 | 0.569 | 0.516 |
| 0.9 | 0.613 | 0.481 |
| 1.0 | 0.525 | 0.438 |
| 1.2 | 0.555 | 0.365 |
| 1.5 | 0.494 | 0.462 |
| 1.8 | 0.460 | 0.368 |
| 2.1 | 0.509 | 0.364 |

Cada evento n-fold representa solamente unas 1.7–3.4 tentativas convencionales según
la dinámica y la temperatura. Hay pocos rechazos que eliminar, de modo que mantener las
10 clases cuesta más que el ahorro obtenido.

### Campo débil: H/J = -0.75

Aquí aparece el régimen para el que n-fold resulta especialmente útil:

| T/J | Speed-up Glauber | Speed-up Metropolis | intentos/evento Glauber | intentos/evento Metropolis |
|---:|---:|---:|---:|---:|
| 0.8 | 175.8 | 166.5 | 1066.7 | 1055.2 |
| 0.9 | 42.6 | 36.4 | 314.5 | 294.2 |
| 1.0 | 14.5 | 11.3 | 112.5 | 102.4 |
| 1.2 | 4.38 | 3.44 | 33.35 | 29.55 |
| 1.5 | 1.68 | 1.35 | 12.75 | 10.85 |
| 1.8 | 1.32 | 0.757 | 7.54 | 6.20 |
| 2.1 | 0.881 | 0.571 | 5.49 | 4.38 |

El resultado clave es que el beneficio no procede de cambiar la dinámica física: procede
de comprimir secuencias de intentos rechazados. A `T=0.8`, un único evento n-fold
representa en promedio más de mil intentos del algoritmo convencional.

El cruce medido `speed-up = 1`, obtenido sólo mediante interpolación lineal entre puntos
adyacentes, aparece aproximadamente en:

- Glauber, `H/J=-0.75`: `T/J ≈ 2.02`;
- Metropolis, `H/J=-0.75`: `T/J ≈ 1.68`.

Son cruces de **rendimiento de esta implementación, compilación y máquina**; no son
transiciones de fase ni temperaturas físicas universales.

## Diagnóstico tipo Arrhenius

Como comprobación adicional se ajusta, sólo en `T<=1.2`,

`ln(<tau>) = a + Gamma_eff/T`.

El ajuste se usa como pendiente efectiva en un intervalo finito, no como afirmación de
una barrera universal. En campo débil se obtienen pendientes de orden 10 y estándar/n-fold
son cercanas:

- Glauber: `Gamma_eff ≈ 10.27` (standard) y `10.03` (n-fold);
- Metropolis: `Gamma_eff ≈ 10.69` (standard) y `10.31` (n-fold).

Esto aporta una comprobación adicional de que n-fold conserva la fuerte dependencia
térmica de la vida metaestable mientras reduce el coste de simular los rechazos.

## Archivos generados

- `results/temperature_sweep/temperature_sweep_summary.csv`: 28 puntos consolidados.
- `results/temperature_sweep/raw/`: datos por escape.
- `results/temperature_sweep/arrhenius_fits.csv`: ajustes en `1/T`.
- `results/temperature_sweep/speedup_crossovers.csv`: cruces de rendimiento.
- `results/temperature_sweep/equivalence_vs_temperature.png`.
- `results/temperature_sweep/speedup_vs_temperature.png` y versión logarítmica.
- `results/temperature_sweep/event_compression_vs_temperature.png` y versión logarítmica.
- `results/temperature_sweep/acceptance_vs_temperature.png`.
- curvas `lifetime_vs_invT_*` y `cpu_vs_invT_*` para cada dinámica/campo.

El script reproducible es `scripts/temperature_sweep.py`.
