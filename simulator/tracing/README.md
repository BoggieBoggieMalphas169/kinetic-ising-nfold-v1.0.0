# Motor instrumentado de Ising — B3

Esta **no es una dinámica nueva**. Es una variante con instrumentación del simulador original `v1.0.0`. Mantiene la física de Ising, PCG, las dos reglas Glauber/Metropolis y el reloj geométrico n-fold, y registra las trayectorias aceptadas con sus intentos equivalentes.

## Compilar

Desde la raíz del repositorio:

```powershell
cmake -S simulator/tracing -B build/practica_b3 -DCMAKE_BUILD_TYPE=Release
cmake --build build/practica_b3 --config Release
ctest --test-dir build/practica_b3 --output-on-failure -C Release
```

En Windows los ejecutables suelen estar bajo `build/practica_b3/Release/`. En Linux con Makefiles suelen encontrarse directamente en `build/practica_b3/`.

## CLI

Ambos ejecutables aceptan sus argumentos anteriores (`--L`, `--T`, `--J`, `--H`, `--runs`, `--seed`, `--dynamics`, `--output` y los límites específicos). Se añaden:

- `--trace-prefix RUTA`: activa archivos `RUTA_frames.csv` y `RUTA_events.csv`.
- `--trace-run N`: índice de la realización trazada, **desde 0** (por defecto 0). Todas las realizaciones siguen apareciendo en el CSV de resumen.
- `--trace-every K`: cada cuántos *eventos aceptados* guardar una malla completa (por defecto 1). El archivo de eventos almacena **todos** los aceptados.

**Ejemplo** (ajusta la ruta al ejecutable compilado):

```powershell
& '.\build\practica_b3\Release\ising_standard_trace.exe' --L 16 --T 1.5 --J 1 --H -3 --runs 2 --seed 1234 --dynamics glauber --trace-prefix results/traj_std --trace-run 1 --trace-every 8 --output results/std.csv
```

El prefijo debe apuntar a un directorio existente y a archivos aún inexistentes. El escritor usa creación exclusiva; no sobrescribe trazas previas. Usa preferentemente el menú PowerShell, que crea directorios únicos en `results/practica_cierre/`.

## Formato de salida

Los frames guardan `spin_bits` de longitud `L²`; `1=+1`, `0=-1`, orden por filas. `M` y `E` corresponden a estados después de cada evento, salvo el inicial. Para n-fold, `wait_attempts` es la espera geométrica; en Standard, diferencia de intentos entre flips aceptados. `events` es el número acumulado de volteos reales. La transformación a tiempo de animación se hará en B5 y deberá respetar `time_mcss`, no solo el índice de frame.

### Restricciones

- El coste de E/S puede ser considerable, porque el CSV de eventos almacena cada flip aceptado. Se recomienda una sola realización a la vez y aplicar límites (`--max-attempts`, `--max-events`).
- Los límites temporales de n-fold mantienen la semántica preexistente: un salto geométrico puede rebasar el máximo antes de detenerse.
- No calcular factores de speed-up a partir de estos ejecutables trazados.
- Las reglas estocásticas existentes permanecen intactas y pueden probarse además con `python simulator/tracing/scripts/check_trace_integration.py --standard RUTA --nfold RUTA`.
