# Prompt 8B.1 — Equivalencia física Standard ↔ n-fold

## Pregunta científica

El n-fold no se valida porque ejecute menos operaciones, sino porque debe reproducir la
misma dinámica estocástica de single-spin-flip que acelera. Para el protocolo metaestable
del proyecto, la magnitud primaria es el tiempo de primer paso hasta `M=0`, `tau`.

La hipótesis operativa es:

- Standard y n-fold comparten la misma dinámica microscópica (Glauber o Metropolis);
- n-fold elimina explícitamente secuencias de rechazos mediante su reloj geométrico;
- por tanto deben reproducir la misma ley de tiempos de escape dentro de la precisión
  estadística del experimento.

## Endpoint primario

Se estudia

```text
R_tau = <tau>_nfold / <tau>_standard
```

con el intervalo bootstrap al 95 % ya calculado en la campaña original. El margen de
equivalencia práctica predeclarado es, en los datasets actuales, ±5 % alrededor de 1.

No se exige que el intervalo contenga exactamente `R_tau = 1`: equivalencia práctica y
igualdad puntual son preguntas distintas. Un intervalo estrecho completamente dentro de
la banda `[0.95, 1.05]` respalda equivalencia aunque no contenga exactamente 1.

## Diagnóstico de distribución

Cuando existe un test KS, se conserva como comprobación complementaria de la distribución
completa. La ausencia de rechazo KS **no se interpreta como prueba de igualdad**. Cuando la
campaña proporciona la corrección múltiple de Holm, se conserva esa decisión corregida.

## Entrada inmutable

8B.1 exige un snapshot 8A.21 verificado:

```powershell
python -m scripts.analysis.build_physical_equivalence `
  --snapshot results/snapshots/snap_XXXXXXXXXXXXXXX
```

Antes de analizarlo se vuelven a comprobar los SHA-256 del snapshot.

## Salidas

```text
results/processed/physical_equivalence_8B1.csv
results/processed/physical_equivalence_summary_8B1.csv
results/metadata/physical_equivalence_diagnostics_8B1.csv
```

Cada fila conserva `analysis_snapshot`, de modo que cualquier tabla o conclusión posterior
puede rastrearse hasta los bytes exactos congelados por 8A.21.

## Qué no analiza 8B.1

No usa `speedup`, tiempo CPU ni coste/evento para decidir equivalencia física. Esas métricas
se reservan para 8C. Tampoco combina ingenuamente las campañas que comparten un mismo
punto físico; la reproducibilidad de esos solapamientos se estudia separadamente en 8B.2.
