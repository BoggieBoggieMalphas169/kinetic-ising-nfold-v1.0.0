# Prompt 8B.2 — Consistencia de los puntos repetidos entre campañas

## Objetivo

Los cuatro puntos físicos con `L=32`, `T/J=1.5`, `J=1` y las combinaciones

- Glauber, `H/J=-3`;
- Glauber, `H/J=-0.75`;
- Metropolis, `H/J=-3`;
- Metropolis, `H/J=-0.75`;

fueron medidos de forma independiente dentro de las campañas `validation`,
`scalability_L` y `temperature_sweep`.

8B.2 utiliza este solapamiento como comprobación interna de reproducibilidad. No considera
estas filas duplicados ni las promedia como si fueran muestras microscópicas adicionales.
Cada fila sigue representando una comparación agregada de una campaña distinta.

## Entrada inmutable

Se vuelve a verificar el snapshot 8A.21 y se reconstruye 8B.1 en memoria:

```powershell
python -m scripts.analysis.build_campaign_consistency `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

Snapshot utilizado en los resultados actuales:

```text
snap_0cc46433731097c4
```

## Criterios descriptivos

Para cada `experiment_id` repetido se comprueba:

1. número de campañas independientes;
2. estado de equivalencia de cada campaña;
3. solapamiento de los IC bootstrap de `R_tau` por pares;
4. intersección común de todos los IC bootstrap de `R_tau`;
5. si esa intersección contiene `R_tau=1`;
6. dispersión descriptiva entre campañas de `<tau>_standard` y `<tau>_nfold`.

El endpoint sigue siendo

```text
R_tau = <tau>_nfold / <tau>_standard.
```

El solapamiento de intervalos es un diagnóstico de reproducibilidad, no un test formal de
igualdad entre campañas. No se usa para sustituir los resultados bootstrap originales.

## Resultado

Se encuentran 12 registros de campaña correspondientes a 4 puntos físicos repetidos.
Cada punto aparece exactamente en las tres campañas.

```text
puntos físicos repetidos                 4
registros de campaña                    12
pares de campañas                       12
puntos consistentes                      4
puntos mixtos/inconclusos                0
puntos con discrepancia                   0
pares de IC de R_tau sin solapamiento     0
```

Para los cuatro puntos, los tres intervalos bootstrap comparten una intersección no vacía
y esa intersección contiene `R_tau=1`.

| Dinámica | H/J | R_tau min–max entre campañas | Intersección común IC95 | span tau Standard | span tau n-fold |
|---|---:|---:|---:|---:|---:|
| Glauber | -3.00 | 0.997493–0.999435 | [0.995554, 1.001212] | 0.152 % | 0.308 % |
| Glauber | -0.75 | 0.992180–0.999173 | [0.988088, 1.003739] | 0.633 % | 1.335 % |
| Metropolis | -3.00 | 0.998214–0.999365 | [0.995599, 1.001874] | 0.212 % | 0.097 % |
| Metropolis | -0.75 | 0.992362–1.009718 | [0.998218, 1.003514] | 0.933 % | 0.800 % |

El mayor intervalo entre estimaciones puntuales de `R_tau` de campañas diferentes es
aproximadamente 1.736 puntos porcentuales y aparece en Metropolis con `H/J=-0.75`.
Aun en ese caso, los tres IC bootstrap comparten la intersección
`[0.998218, 1.003514]`.

La mayor dispersión descriptiva de `<tau>_standard` entre campañas es aproximadamente
0.933 %, y la de `<tau>_nfold` aproximadamente 1.335 %.

## Clasificación 8B.2

Los cuatro puntos obtienen:

```text
CONSISTENT_ACROSS_CAMPAIGNS
```

Esta etiqueta requiere en la implementación actual que todas las campañas sean `PASS` en
el criterio 8B.1 y que sus IC de `R_tau` tengan solapamiento por pares y una intersección
común.

Si todas las campañas fueran `PASS` pero sus intervalos fueran incompatibles entre sí, el
sistema no ocultaría esa tensión: la marcaría explícitamente para revisión.

## Salidas

```text
results/processed/campaign_repeated_records_8B2.csv
results/processed/campaign_consistency_summary_8B2.csv
results/processed/campaign_pairwise_consistency_8B2.csv
results/metadata/campaign_consistency_diagnostics_8B2.csv
```

`campaign_repeated_records_8B2.csv` conserva los 12 registros originales de 8B.1.

`campaign_consistency_summary_8B2.csv` produce una fila por punto físico repetido.

`campaign_pairwise_consistency_8B2.csv` contiene las 12 comparaciones por pares entre
campañas y permite auditar de dónde sale la conclusión de reproducibilidad.

## Interpretación científica

8B.2 aporta una validación distinta de 8B.1. El resultado no solo se reproduce entre
Standard y n-fold dentro de una campaña, sino que los mismos cuatro puntos físicos fueron
obtenidos en tres campañas distintas sin aparecer una dependencia apreciable de la campaña
que los generó en las métricas estudiadas.

Esto reduce la posibilidad de que la equivalencia observada sea un artefacto específico de
un único script de campaña o de un único lote de simulaciones. No demuestra identidad
exacta de las distribuciones ni sustituye una replicación totalmente externa.

## Separación respecto a rendimiento

Ninguna métrica de CPU, speed-up o coste/evento participa en la clasificación de 8B.2.
La reproducibilidad física y la eficiencia computacional continúan tratándose por separado.
