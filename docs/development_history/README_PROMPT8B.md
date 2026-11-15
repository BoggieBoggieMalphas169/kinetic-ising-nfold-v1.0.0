# Prompt 8B — Comparación física Standard ↔ n-fold

## Objetivo

8B usa exclusivamente datasets que han superado 8A.21. La pregunta ya no es si el
pipeline funciona, sino si el algoritmo n-fold reproduce la dinámica física del algoritmo
Standard que pretende acelerar.

Para este proyecto metaestable, el observable central es el tiempo de primer paso desde
la configuración inicial `M=L^2` hasta la primera configuración con `M=0`.

## Separación respecto a 8C

8B estudia equivalencia física. Tiempos de CPU, speed-up, coste por evento y compresión
de rechazos se reservan para 8C. Un algoritmo puede reproducir correctamente la dinámica
y, en cierto régimen, ser más lento computacionalmente; ambas preguntas son distintas.

## Subbloques previstos

- **8B.1 — Equivalencia primaria de tiempos de escape.** Implementado.
- **8B.2 — Consistencia de los puntos repetidos entre campañas.** Implementado.
- **8B.3 — Robustez con el tamaño de red L.** Implementado.
- **8B.4 — Robustez frente a temperatura y campo.** Implementado.
- **8B.5 — Lectura separada de Glauber y Metropolis.** Implementado.
- **8B.6 — Síntesis física, limitaciones y conclusión reproducible.** Implementado.

## Estado de 8B.1 sobre el snapshot actual

Snapshot analizado:

```text
snap_0cc46433731097c4
```

Se analizaron 52 registros de campaña que corresponden a 44 puntos físicos únicos.
Bajo el criterio bootstrap de equivalencia práctica ya predeclarado:

```text
PASS            49
INCONCLUSIVE     3
FAIL              0
```

Los 20 registros de la campaña de escalabilidad con L son PASS. En el barrido térmico,
25 de 28 son PASS. Los tres puntos inconclusos son:

```text
Glauber     H/J=-0.75  T/J=0.8
Glauber     H/J=-0.75  T/J=0.9
Metropolis  H/J=-0.75  T/J=0.8
```

No se interpretan como fallos de n-fold: sus intervalos no permiten concluir equivalencia
con el margen ±5 %, pero tampoco establecen una discrepancia bajo el criterio empleado.

De forma puramente descriptiva, la mediana de `|R_tau-1|` en los 52 registros es
aproximadamente 0.174 %. El máximo, aproximadamente 16.1 %, corresponde precisamente a
uno de los puntos fríos inconclusos, por lo que no debe resumirse el estudio solo con la
mediana global.

Hay 32 comparaciones con diagnóstico KS disponible. En el barrido térmico, donde existe
la corrección múltiple de Holm, no aparece ningún rechazo corregido. Esto es evidencia
complementaria, no una prueba matemática de identidad de distribuciones.

## Ejecución

```powershell
python -m scripts.analysis.build_physical_equivalence `
  --snapshot results/snapshots/snap_0cc46433731097c4
```

Salidas:

```text
results/processed/physical_equivalence_8B1.csv
results/processed/physical_equivalence_summary_8B1.csv
results/metadata/physical_equivalence_diagnostics_8B1.csv
```


## Estado de 8B.2 sobre el snapshot actual

Los cuatro puntos físicos repetidos entre `validation`, `scalability_L` y
`temperature_sweep` son consistentes entre campañas bajo los diagnósticos predefinidos.
Los 12 pares de intervalos bootstrap de `R_tau` se solapan; para cada uno de los cuatro
puntos existe además una intersección común de los tres intervalos que contiene `R_tau=1`.

La máxima separación entre estimaciones puntuales de `R_tau` de campañas distintas es
aproximadamente 1.736 puntos porcentuales. Los spans máximos de la media de `tau` entre
campañas son aproximadamente 0.933 % para Standard y 1.335 % para n-fold.

Los cuatro puntos quedan clasificados como `CONSISTENT_ACROSS_CAMPAIGNS`.
Véase `README_PROMPT8B2.md` para el detalle y las cautelas estadísticas.


## Estado de 8B.3 sobre el snapshot actual

La campaña `scalability_L` contiene 20 registros organizados en cuatro series
(Glauber/Metropolis × `H/J=-3,-0.75`) y cinco tamaños `L=8,16,32,64,128`.
Las cuatro series quedan clasificadas como `ROBUST_ACROSS_TESTED_L`: los 20 puntos son
PASS y los 20 intervalos bootstrap de `R_tau` están completamente dentro de la banda
práctica `[0.95,1.05]`. Diecinueve de los 20 IC contienen además exactamente `R_tau=1`.

La máxima desviación puntual de `R_tau` respecto de uno es aproximadamente 1.237 %, y la
mayor deriva lineal descriptiva frente a una duplicación de L es aproximadamente 0.245
puntos porcentuales por duplicación. Standard y n-fold muestran además una dependencia
finita con L muy similar. Véase `README_PROMPT8B3.md`.

## Estado tras 8B.4

- 8B.1: equivalencia primaria — completado.
- 8B.2: consistencia entre campañas — completado.
- 8B.3: robustez con L — completado.
- 8B.4: dependencia con T y H — completado.

En el barrido térmico hay 25 PASS, 3 INCONCLUSIVE y 0 FAIL. Los tres inconclusos se
concentran en `H/J=-0.75` y `T/J=0.8-0.9`; no se reinterpretan como discrepancias.


## Estado tras 8B.5

Glauber y Metropolis se analizan por separado y no se tratan como dinámicas
intercambiables. En los 26 registros de Glauber hay 24 PASS, 2 INCONCLUSIVE y 0 FAIL;
en los 26 de Metropolis hay 25 PASS, 1 INCONCLUSIVE y 0 FAIL.

Los 26 puntos de campaña emparejados muestran además que el contraste de tiempos de
escape Glauber/Metropolis se conserva estrechamente entre Standard y n-fold: la mediana
de la diferencia relativa del contraste es aproximadamente 0.333 % y el máximo 3.545 %.
Los 26/26 valores del diagnóstico descriptivo `Q=C_nfold/C_standard` quedan dentro de
±5 % de uno. Véase `README_PROMPT8B5.md`.

## Cierre de 8B.6

El bloque 8B queda cerrado sobre el snapshot `snap_0cc46433731097c4`.
La síntesis acumulada es `49 PASS`, `3 INCONCLUSIVE`, `0 FAIL` en 52 registros de
campaña. Los cuatro puntos repetidos entre campañas son reproducibles; las cuatro series
de tamaño son robustas en `L=8...128`; y no aparece ninguna discrepancia bajo el criterio
predefinido.

La conclusión reproducible se clasifica como `SUPPORTED_WITH_PRECISION_LIMITS` porque
los tres puntos fríos de campo débil permanecen inconclusos. El rendimiento computacional
no forma parte de esta decisión y se estudia a partir de 8C.

Véase `README_PROMPT8B6.md` y:

```text
results/processed/physical_synthesis_8B6.csv
results/metadata/physical_limitations_8B6.csv
results/metadata/physical_synthesis_diagnostics_8B6.csv
```
