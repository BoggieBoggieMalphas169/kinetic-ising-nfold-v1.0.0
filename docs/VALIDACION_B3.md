# Validación del Bloque 3 — resultados ejecutados

**Fecha:** 15-11-2026. **Entorno:** Linux de integración (no es una prueba en Windows).

## Auditoría original

- El motor `v1.0.0` original compiló y pasó **6/6 CTest**.
- Las pruebas Python completas del repositorio pasaron **103/103** (96 previas más siete nuevas de B3).
- El overlay `simulator/tracing/` compiló como variante independiente y pasó **1/1 CTest**, que cubre cuatro combinaciones, la equivalencia traza activa/inactiva y los casos límite de corte.
- `python scripts/release_check.py --verify-frozen`: **PASS**.
- `python -m scripts.analysis.build_quality_snapshot --verify results/snapshots/snap_0cc46433731097c4`: **SNAPSHOT VERIFIED**.
- Ninguna ruta declarada en el manifiesto histórico `release/release_manifest.csv` sufrió cambios respecto a su SHA-256.

## Control sobre las cuatro combinaciones

Condiciones del ejemplo reproducible: `L=16, T=1.5, J=1, H=-3, seed=1234`, un run por combinación, `--trace-every 8`.

| Algoritmo | Dinámica | Eventos aceptados | Frames | Estado |
|---|---|---:|---:|---|
| Standard | Glauber | 148 | 20 | PASS |
| Standard | Metropolis | 158 | 21 | PASS |
| n-fold | Glauber | 148 | 20 | PASS |
| n-fold | Metropolis | 150 | 20 | PASS |

**No interpretar el mismo número de eventos Glauber (148) en ambos motores como identidad de trayectorias.** Los estados y tiempos exactos son diferentes entre motores; la comparación requerida es estadística. En cambio, para cada algoritmo, el mismo ejecutable con trazas activas e inactivas produjo campos físicos CSV idénticos excepto `cpu_seconds`.

Se comprobó además que el ejecutable instrumentado coincidía con la release original en **40 realizaciones adicionales** (10 por combinación), sin diferencias en ningún campo físico del CSV. El generador nuevo también hace esta comparación automáticamente mediante `resumen_original.csv`.

## Validación física independiente

El verificador Python reconstruye la trayectoria bit a bit aplicando los sitios de `trayectoria_events.csv` desde el estado inicial. Contrasta `M`, `E`, `time_mcss`, el sitio volteado, la espera desde el evento anterior, las instantáneas, el cierre del CSV de resumen y los metadatos de semillas. Los frames se comprueban mediante recomputación completa de energía y magnetización con condiciones periódicas.

Se validaron además: rechazo de sobrescritura de la traza, una trayectoria Standard detenida después de **un intento rechazado** (cero eventos) y una ejecución n-fold con **espera geométrica que supera el límite de intentos**.

## Restricciones / siguientes tareas

- No se puede certificar la ejecución de PowerShell en el ordenador del usuario desde Linux: queda una comprobación de integración local.
- Los tiempos `cpu_seconds` registrados con trazas están contaminados por E/S: no son benchmarks científicos.
- El resultado histórico de equivalencia entre distribuciones de escape no se recalculó aquí; B3 verifica conservación de resultados a nivel de corrida de cada motor.
- El nuevo formato es apto para mapas, `M(t)`, `E(t)` y GIF/MP4, pero esas visualizaciones son B4 y B5, no B3.
