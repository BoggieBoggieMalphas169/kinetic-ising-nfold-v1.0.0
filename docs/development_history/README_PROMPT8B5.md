# Prompt 8B.5 — Lectura separada de Glauber y Metropolis

## Objetivo

Este subbloque comprueba la equivalencia Standard ↔ n-fold **por separado** para las
dinámicas de Glauber y Metropolis. No se las trata como si fueran la misma dinámica: cada
una define probabilidades de aceptación distintas y, por tanto, puede producir tiempos de
escape distintos aunque ambas describan el mismo Hamiltoniano.

El objetivo físico de n-fold es preservar la dinámica que acelera. Por ello, la comparación
primaria sigue siendo

\[
R_\tau = \frac{\langle\tau\rangle_{\rm nfold}}
               {\langle\tau\rangle_{\rm Standard}}
\]

dentro de cada dinámica.

No se usan tiempos de CPU, speed-up ni coste por evento; esas cantidades siguen reservadas
para 8C.

## Resultado separado por dinámica

Snapshot: `snap_0cc46433731097c4`.

| dinámica | registros | PASS | INCONCLUSIVE | FAIL | mediana de \|R_tau-1\| | máximo |
|---|---:|---:|---:|---:|---:|---:|
| Glauber | 26 | 24 | 2 | 0 | 0.122 % | 13.659 % |
| Metropolis | 26 | 25 | 1 | 0 | 0.222 % | 16.111 % |

Ambas quedan clasificadas como `NO_DISCREPANCY_WITH_PRECISION_LIMITS`: no aparece ningún
FAIL, pero cada una hereda los puntos fríos de campo débil que 8B.4 había dejado como
inconclusos.

Los máximos del 13.7 % y 16.1 % no deben interpretarse como discrepancias establecidas:
corresponden a los casos de baja temperatura con intervalos bootstrap demasiado anchos.

## Las dos dinámicas no deben confundirse

Para cada uno de los 26 puntos de campaña donde existen simultáneamente Glauber y
Metropolis se ha calculado, de forma descriptiva,

\[
C_{\rm Standard}=\frac{\tau_{\rm Glauber}^{\rm Standard}}
                        {\tau_{\rm Metropolis}^{\rm Standard}},
\qquad
C_{\rm nfold}=\frac{\tau_{\rm Glauber}^{\rm nfold}}
                     {\tau_{\rm Metropolis}^{\rm nfold}}.
\]

En los 26/26 pares medidos se obtiene `tau_Glauber > tau_Metropolis` tanto para Standard
como para n-fold. En Standard, el cociente Glauber/Metropolis recorre aproximadamente
`1.007–1.277`; en n-fold, `1.037–1.282`.

Esto no es un criterio de superioridad entre dinámicas. Es una comprobación de que las dos
reglas de aceptación producen dinámicas distintas y que n-fold no borra esa diferencia.

## Preservación del contraste entre dinámicas

Como diagnóstico secundario se define

\[
Q = \frac{C_{\rm nfold}}{C_{\rm Standard}}.
\]

Si n-fold preserva el contraste Glauber/Metropolis, se espera descriptivamente `Q≈1`.
En el snapshot actual:

- 26/26 pares tienen `Q` dentro de ±5 % de uno;
- la mediana de `100|Q-1|` es aproximadamente `0.333 %`;
- el máximo es aproximadamente `3.545 %`;
- 24 pares tienen ambas dinámicas clasificadas PASS;
- 2 pares contienen al menos una dinámica INCONCLUSIVE;
- 0 pares contienen un FAIL.

Los dos mayores desajustes de `Q` aparecen precisamente en los puntos fríos de campo débil
ya identificados como limitados por precisión. Este diagnóstico se mantiene deliberadamente
descriptivo: no se le asigna un test de equivalencia propio porque no disponemos aquí de la
distribución bootstrap conjunta necesaria para construir un intervalo de confianza correcto
de `Q`.

## Archivos añadidos

```text
scripts/analysis/dynamics_comparison.py
scripts/analysis/build_dynamics_comparison.py
results/processed/dynamics_records_8B5.csv
results/processed/dynamics_summary_8B5.csv
results/processed/dynamics_matched_pairs_8B5.csv
results/metadata/dynamics_diagnostics_8B5.csv
```

## Ejecución

```powershell
python -m scripts.analysis.build_dynamics_comparison `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

## Tests

La batería acumulada tras 8B.5 es `50 passed`.

## Conclusión

La evidencia disponible no muestra una discrepancia Standard ↔ n-fold específica de
Glauber ni de Metropolis. Las limitaciones se concentran en el mismo régimen frío de campo
débil detectado en 8B.4. Además, el contraste de tiempos de escape entre Glauber y
Metropolis observado con el algoritmo Standard se reproduce estrechamente con n-fold,
lo que constituye una comprobación adicional de que n-fold acelera la dinámica elegida sin
convertir ambas reglas de aceptación en una dinámica efectiva común.
