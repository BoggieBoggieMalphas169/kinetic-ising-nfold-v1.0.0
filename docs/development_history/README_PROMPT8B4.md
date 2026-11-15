# Prompt 8B.4 — Dependencia con temperatura y campo

## Objetivo

Este subbloque estudia la campaña `temperature_sweep` del snapshot verificado
`snap_0cc46433731097c4`. La pregunta es si la equivalencia práctica Standard ↔ n-fold del
tiempo de escape metaestable se mantiene al variar `T/J` y si el resultado cambia entre
campo fuerte (`H/J=-3`) y campo débil (`H/J=-0.75`).

No se usan tiempos de CPU, speed-up ni coste por evento; esas magnitudes quedan para 8C.

## Diseño

Se analizan 28 comparaciones: Glauber/Metropolis × dos campos × siete temperaturas
`T/J = 0.8,0.9,1.0,1.2,1.5,1.8,2.1`, siempre con `L=32` y `J=1`.

## Resultado principal

```text
temperature records             28
PASS                            25
INCONCLUSIVE                     3
FAIL                             0

series robustas                  2
series con algún inconcluso      2
series con discrepancia          0
```

Las dos series de `H/J=-3` son `ROBUST_ACROSS_TESTED_T`: 14/14 puntos PASS.
Las dos series de `H/J=-0.75` contienen los únicos tres puntos inconclusos y ningún FAIL.

## Localización de la pérdida de precisión

Los tres puntos inconclusos son:

| dinámica | H/J | T/J | runs | R_tau | IC95 |
|---|---:|---:|---:|---:|---:|
| Glauber | -0.75 | 0.8 | 150 | 0.863408 | [0.702664, 1.053404] |
| Glauber | -0.75 | 0.9 | 4000 | 1.024712 | [0.985232, 1.065409] |
| Metropolis | -0.75 | 0.8 | 150 | 0.838888 | [0.685431, 1.025992] |

Por tanto, con el margen práctico ±5 %, el primer T completamente PASS es `T/J=1.0`
para Glauber de campo débil y `T/J=0.9` para Metropolis de campo débil.

## Interpretación

El patrón es compatible con una pérdida de precisión estadística en el régimen frío de
campo débil, donde los tiempos de escape son enormes: a `T/J=0.8` las medias Standard
son del orden de `4.4e3 MCSS`, frente a aproximadamente `1.8 MCSS` en campo fuerte.
Además, esos puntos fríos sólo tienen 150 escapes. El ancho del IC de `R_tau` llega a
0.3507 (Glauber) y 0.3406 (Metropolis), mientras que a `T/J=2.1` en campo débil es sólo
aproximadamente 0.0149 en ambos casos.

Esto NO se interpreta como evidencia de discrepancia física. Ningún punto es `FAIL`; los
intervalos fríos son simplemente demasiado anchos para quedar contenidos por completo
en `[0.95,1.05]`.

## Archivos añadidos

```text
scripts/analysis/temperature_field_robustness.py
scripts/analysis/build_temperature_field.py
results/processed/temperature_field_records_8B4.csv
results/processed/temperature_field_summary_8B4.csv
results/metadata/temperature_field_diagnostics_8B4.csv
```

## Ejecución

```powershell
python -m scripts.analysis.build_temperature_field `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

## Tests

La batería acumulada tras 8B.4 es `44 passed`.

## Conclusión

Dentro del rango estudiado no aparece ninguna discrepancia Standard ↔ n-fold asociada a
T o H. La equivalencia es robusta en campo fuerte para las siete temperaturas. En campo
débil, el régimen más frío queda limitado por precisión estadística y requiere más datos
si se desea cerrar específicamente esos puntos al margen ±5 %.
