# BLOQUE 7 — Informe de validación científica y computacional

## Datos de la campaña de precisión
- Fuente: ZIP B6 integrado, motor C sin cambios; snapshot de septiembre inmutable.
- Casos: Glauber T/J=0.8, Glauber T/J=0.9, Metropolis T/J=0.8; L=32, J=1, H/J=-0.75.
- Muestra fija de precisión: 3500/algoritmo para cada caso frío y 7000/algoritmo para Glauber T/J=0.9.
- **28.000 trayectorias nuevas** en la campaña de precisión, 6000 en la campaña intermedia y 240 en el piloto.
- Censura en campaña de precisión: **0**; horizonte = 100 millones de intentos equivalentes.
- 4500 réplicas bootstrap por contraste de precisión; margen de equivalencia [0.95, 1.05], IC 95%.
- El fichero B7_ESTADO.json con PASS acredita **la ejecución**, no la equivalencia de los motores.

## Razón de tiempos medios con intervalos de confianza

| Caso | Grupo | n/algoritmo | R_tau | IC 95% | Equivalencia |
|---|---|---:|---:|---|---|
| glauber_0p8 | HISTORICO | 150 | 0.8634 | [0.7011, 1.0573] | INCONCLUSIVE |
| glauber_0p8 | SOLO_NUEVOS | 3500 | 1.0001 | [0.9571, 1.0476] | PASS |
| glauber_0p8 | COMBINADO | 3650 | 0.9940 | [0.9509, 1.0396] | PASS |
| glauber_0p9 | HISTORICO | 4000 | 1.0247 | [0.9854, 1.0659] | INCONCLUSIVE |
| glauber_0p9 | SOLO_NUEVOS | 7000 | 1.0161 | [0.9866, 1.0463] | PASS |
| glauber_0p9 | COMBINADO | 11000 | 1.0193 | [0.9953, 1.0437] | PASS |
| metropolis_0p8 | HISTORICO | 150 | 0.8389 | [0.6845, 1.0318] | INCONCLUSIVE |
| metropolis_0p8 | SOLO_NUEVOS | 3500 | 0.9609 | [0.9175, 1.0038] | INCONCLUSIVE |
| metropolis_0p8 | COMBINADO | 3650 | 0.9553 | [0.9142, 0.9979] | INCONCLUSIVE |

## Contrastes KS de las muestras nuevas (secundarios)
KS no prueba equivalencia; se corrigen tres p-valores por Holm. Un rechazo exige discusión/replicación, no significa automáticamente un bug.

| Caso | KS D | p | p Holm |
|---|---:|---:|---:|
| glauber_0p8 | 0.0123 | 0.9514 | 0.9628 |
| glauber_0p9 | 0.0141 | 0.4814 | 0.9628 |
| metropolis_0p8 | 0.0343 | 0.0319 | 0.0958 |

## Campaña intermedia independiente (6000 trayectorias)
Se preserva como conjunto separado; NO se agrupa silenciosamente con la campaña de precisión.

| Caso | R_tau nuevo, n intermedio | R_tau combinado con histórico |
|---|---:|---:|
| glauber_0p8 | 0.9441 (500) | 0.9261 |
| glauber_0p9 | 1.0525 (2000) | 1.0338 |
| metropolis_0p8 | 1.0482 (500) | 0.9933 |

## Cobertura y límites del alcance
- Mantener fijados Hamiltoniano, regla de actualización, semilla/stream y reloj geométrico de C.
- La aproximación KS usada es asintótica, y el bootstrap independiente no modela una posible covarianza cruzada histórica de semillas comunes entre ambos motores.
- Si un IC no cabe íntegramente en el margen, **INCONCLUSIVE es científicamente válido**; no se debe ajustar retrospectivamente el criterio.
- Solo el reporte principal de cada campaña usa muestras nuevas; el resultado combinado es secundario.
- Compilación y pruebas efectuadas en Linux. La sintaxis/ejecución real de PowerShell en Windows aún requiere comprobación local.
- El Bloque 8 sigue pendiente: auditoría final y preparación de entrega, no nuevas dinámicas físicas.

## Ubicación de los datos
- Campaña de precisión: `results/practica_cierre/20261115T190914332062Z_inconclusos_b7_5e580c44`
- Campaña intermedia: `results/practica_cierre/20261115T190615659796Z_inconclusos_b7_49fff532`
- Los CSV tienen SHA-256 verificados por `B7_MANIFEST_DATOS.json` y salidas con `MANIFEST_B6_SALIDAS.csv`.
- La documentación técnica de la rama B7 está en `docs/BLOQUE7_INCONCLUSOS.md`.

## Pruebas de regresión e integridad del bloque

- **151/151 pruebas Python** (`pytest -q`), incluidos 10 tests nuevos B7. Las seis advertencias son de deprecación de Matplotlib/NumPy, no fallos físicos.
- **6/6 CTest** en una compilación Release de los motores originales, sin modificar `simulator/src`.
- `python scripts/release_check.py --verify-frozen`: **PASS**.
- `python -m scripts.analysis.build_quality_snapshot --verify ...`: **PASS**.
- **374 archivos de la release protegidos** por el manifiesto, más el propio manifiesto: hashes preservados.
- Los **710 archivos del ZIP del bloque 6** se conservan; solo cambia el menú maestro PowerShell.
- Regeneración B7 desde los CSV de la campaña de precisión realizada y verificada; nuevos gráficos en una carpeta distinta.
- Bootstrap de sensibilidad (10.000 réplicas con segunda semilla): las dos comparaciones nuevas Glauber siguen en PASS; Metropolis T/J=0,8 sigue INCONCLUSIVE. El resultado combinado Glauber T/J=0,8 está cercano al margen inferior, por lo que se comunica con cautela.
- **Límite de plataforma:** ejecutado en Linux. El funcionamiento de los `.ps1` en Windows debe probarse localmente.
