# Bloque 3 — Instrumentación física para trazas temporales

**Estado:** implementado y probado en Linux el 15-11-2026. La ejecución de los PS1 en Windows queda por comprobar en el equipo del estudiante.

## Objetivo científico

Registrar la evolución real de las cuatro cadenas cinéticas sin cambiar el modelo de Ising, sus probabilidades ni el reloj. Se necesita tanto el estado `spin(x,y,t)` como las marcas de tiempo, `M(t)`, `E(t)` y los saltos entre eventos para preparar los gráficos de series temporales (B4) y las animaciones (B5).

## Decisión de arquitectura: overlay instrumentado

Las fuentes de la release `v1.0.0` declaradas en `release/release_manifest.csv` **no se modifican**. Los nuevos ejecutables se compilan desde `simulator/tracing/`: reutilizan `simulator/src/ising.c`, `rng.c` y `dynamics.c` exactamente como estaban, y aportan versiones instrumentadas de `standard_mc.c`, `nfold.c` y sus `main_*.c` en `simulator/tracing/src/`. Así `scripts/release_check.py --verify-frozen` sigue pasando y no se cambian los benchmarks históricos.

La API pública de simulación sigue disponible: `standard_run()` y `nfold_run()` son wrappers sin trazas; `standard_run_traced()` y `nfold_run_traced()` aceptan el escritor opcional. La instrumentación no hace llamadas al RNG y actúa **después** de cada flip aceptado.

## Reloj físico y datos

- **Standard:** cada intento, incluidos rechazos, incrementa `attempts`. Un evento registrado es un flip **aceptado**; su espera `wait_attempts` es la diferencia entre números de intento sucesivos aceptados.
- **n-fold:** el evento seleccionado es necesariamente aceptado; `wait_attempts` se obtiene del reloj geométrico original, sin sustitución por una exponencial continua.
- **Ambos:** `time_mcss = attempts / (L*L)`, usando intentos equivalentes en n-fold. `events` cuenta flips, **no** fotogramas.
- **Instantáneas:** se guarda la configuración inicial, una instantánea cada `--trace-every K` eventos aceptados, y el estado final siempre. Si el límite de intentos termina una carrera Standard tras rechazos, el último frame puede tener los mismos espines y un tiempo mayor.

Los bits de configuración se escriben por filas, índice `site=y*L+x`, `1` equivale a espín `+1` y `0` a `-1`. Los estados son realmente simulados: no hay interpolación inventada ni fotogramas ficticios.

## Nuevos archivos físicos

| Archivo | Papel |
|---|---|
| `simulator/tracing/CMakeLists.txt` | Compilación independiente del overlay |
| `simulator/tracing/include/trace.h` | Contrato del escritor de trazas |
| `simulator/tracing/src/trace.c` | Escritura exclusiva de CSV, estado inicial, eventos y frames |
| `simulator/tracing/src/standard_mc.c` | Hook no estocástico después de flips Standard |
| `simulator/tracing/src/nfold.c` | Hook tras eventos n-fold, conservando espera geométrica |
| `simulator/tracing/src/main_standard.c` | Nuevas opciones CLI Standard |
| `simulator/tracing/src/main_nfold.c` | Nuevas opciones CLI n-fold |
| `simulator/tracing/include/{standard_mc,nfold}.h` | Interfaz trazada sin alterar headers originales |
| `simulator/tracing/scripts/check_trace_integration.py` | Reproducción por eventos y regresión on/off |
| `scripts/practica_cierre/trazas_b3.py` | Orquestador, auditoría, manifiestos, verificador independiente |
| `powershell/04_generar_trazas.ps1` | Crear cuatro ensembles/realizaciones trazadas |
| `powershell/05_validar_trazas.ps1` | Revalidar resultados B3 existentes |
| `powershell/Ising_Practica_Master.ps1` | Nuevas opciones 7 y 8 (conserva 1–6) |
| `tests/test_bloque3_trazas.py` | Tests Python independientes de formato, energía y límites |

## Contratos CSV

`trayectoria_frames.csv`:

`frame,run,algorithm,dynamics,L,T,J,H,seed,stream,attempts,time_mcss,events,M,E,spin_bits`

`trayectoria_events.csv`:

`event,run,attempts,wait_attempts,time_mcss,site,spin_after,M,E`

`resumen_trazado.csv`, `resumen_control.csv` y `resumen_original.csv` usan **el mismo esquema histórico** de salida del correspondiente motor (los `cpu_seconds` varían). Los eventos pueden reconstruir todos los flips desde la configuración inicial; los frames son instantáneas seleccionadas para reducir el tamaño de salida.

## Criterios de validez

1. Eventos consecutivos, sitios válidos, espera positiva e intentos estrictamente crecientes.
2. Magnetización y energía reconstruidas independientemente de cada evento y desde las redes guardadas; condiciones periódicas y enlaces contados una vez.
3. Consistencia de `time_mcss`, espines, metadatos, semilla/stream y estado final.
4. Resultados **idénticos** en todos los campos físicos, excluido `cpu_seconds`, entre (a) ejecutable trazado on/off y (b) ejecutable trazado y ejecutable original `v1.0.0`.
5. Archivos nuevos con nombres exclusivos y manifest SHA-256 verificable.
6. `release_check --verify-frozen` y verificación de snapshot deben seguir pasando.

**No confundir:** las marcas de tiempo no son segundos físicos; son MCSS. No utilizar los tiempos CPU de las ejecuciones trazadas como benchmarks, porque incluyen E/S de archivos. La falta de `M=0` por límites de simulación significa censura y no debe tratarse como escape completado.

## Estado del cierre

B1: validación y automatización inicial; B2: figuras con resultados históricos; B3: trazas físicas implementadas. B4: generar series temporales/instantáneas a partir de estas trazas (pendiente). B5: animaciones GIF/MP4 (pendiente). B6–B8: ampliación estadística/campo y auditoría/entrega según alcance de la práctica.
