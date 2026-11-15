# Ising cinético — Nivel 2, automatización PowerShell

**Extensión del ZIP v1.0.0 de septiembre de 2026**, basada en la sección 10.3 de la memoria de recuperación del 14/11/2026. No sustituye el baseline histórico: preserva los 375 archivos originales que no son `simulator/CMakeLists.txt`. El único archivo previo editado incorpora el objetivo `ising_trace` a CMake. Los dos motores de producción `ising_standard` y `ising_nfold` están **intactos**.

## Arranque rápido — PowerShell (Windows)

Extraer el ZIP en una carpeta independiente. Abrir PowerShell **en la raíz del repositorio**, donde están `CMakeLists.txt` y `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
.\nivel2\ps1\Nivel2_master.ps1
```

Primero seleccionar **1 (Compilar)**; después **2 (Históricas)** para regenerar desde CSV sin simulaciones. Si se desea realizar todos los estudios del Nivel 2, seleccionar **3 (Campo)** y **4 (Trazas)**, y finalmente **5 (Gráficas)**. Las opciones **8 (Temperatura)** y **9 (Tamaño L)** permiten medir de nuevo estas dos campañas, sin tocar los barridos históricos. La opción **6 (Pruebas)** ejecuta CTest, chequeo SHA-256 de los originales y el test de equivalencia del nuevo trazador con el motor de producción. El modo 7 es una demostración corta, *no* una campaña física definitiva.

Si `python` no corresponde al entorno deseado, agregar `-Python '.\.venv\Scripts\python.exe'` a la invocación de los PS1, tras crear el entorno. Para Windows, instalar CMake y un compilador C compatible; en general `cmake -S . -B build` debe poder configurar el proyecto.

### PS1 separados para usar sin menú

```powershell
.\nivel2\ps1\Nivel2_compilar.ps1
.\nivel2\ps1\Nivel2_graficas.ps1
.\nivel2\ps1\Nivel2_medidas.ps1 -L 32 -T 1.5 -Runs 500 -HValues @(-0.75,-1.0,-1.5,-2.0,-3.0)
.\nivel2\ps1\Nivel2_temperatura.ps1 -L 32 -TValues @(1.0,1.2,1.5,1.8,2.1) -HValues @(-0.75,-3) -Runs 200
.\nivel2\ps1\Nivel2_tamano.ps1 -LValues @(8,16,32,64,128) -T 1.5 -HValues @(-0.75,-3) -Runs 200
.\nivel2\ps1\Nivel2_trayectorias.ps1 -L 32 -T 1.5 -H -0.75 -Dynamics glauber -TraceEvery 10 -SnapshotEvery 200
.\nivel2\ps1\Nivel2_pruebas.ps1
```

Los PS1 utilizan la cultura invariante para que `1.5` y `-0.75` se transmitan correctamente a Python/C incluso con configuración regional española. También pueden invocarse desde cualquier directorio. La instalación de Python, CMake y un compilador compatible es responsabilidad del entorno local.

### Opciones del menú y scripts

- **Compilar**: configura y compila `build/` en modo Release, lanza CTest. No edita CSV ni snapshots.
- **Históricas**: crea gráficos desde los CSV de `simulator/results/temperature_sweep/raw` y `simulator/results/scalability_L/raw`, sin lanzar nuevas simulaciones. Incluye cualquier campaña de campo o trazas nuevas ya presente, si existe.
- **Campo**: ejecuta cada combinación de `-HValues`, `-Dynamics`, Standard y n-fold, con `-Runs` vidas por combinación. Usa semilla distinta por punto físico y registra un manifiesto; almacena todo en carpeta única.
- **Temperatura**: registra vidas independientes en una nueva cuadrícula de `-TValues` y `-HValues` y habilita el recálculo de ECDF/supervivencia/Arrhenius de esa campaña.
- **Tamaño L**: registra nuevos conjuntos de `-LValues` para actualizar velocidad por operación, aceptación y cruce de eficiencia, con figuras separadas por campaña.
- **Trazas**: genera **una realización por algoritmo** con mismo punto físico; se registran tiempos MCSS y estados de los espines a intervalos de *eventos aceptados*, no de intentos. La semilla inicial es reproducible, pero las dos trayectorias no deben coincidir punto a punto.
- **Gráficas**: lee todas las campañas completas disponibles y genera nuevo lote de PNG/PDF, tablas auxiliares y manifiesto de hashes. No sobrescribe lotes anteriores.
- **Pruebas**: valida integridad de datos históricos y compara el final exacto del trazador con cada ejecutable de producción usando el mismo stream.
- **Demo**: compila y ejecuta una campaña reducida en L<=16; su salida es solo diagnóstica.

## Qué corresponde a las nueve familias de la sección 10.3

| Nº | Figura física | Datos y procedimiento |
|---|---|---|
| 01 | Supervivencia `S(t)=P(τ>t)` | CSV crudos del barrido térmico; escalones empíricos sin parametrización. |
| 02 | ECDF Standard y n-fold, y diferencia `F_nfold−F_std` | Mismas vidas individuales, sin perder la información de colas. |
| 03 | Histograma de `log10 τ` | Bins compartidos y densidad normalizada respecto al logaritmo. |
| 04 | Instantáneas de nucleación `s(x,y,t)` | Requiere `ising_trace`: espines reales guardados como matrices CSV + índice de tiempos. |
| 05 | `M(t)/N` y `E(t)/N` | Requiere `ising_trace`: datos exactos por evento trazado. |
| 06 | `ln <τ>` vs `1/T` con IC al 95 % | Barrido térmico histórico, bootstrap independiente por dinámica y algoritmo; **sin imponer linealidad**. |
| 07 | `<τ>` vs `|H|/J` con IC al 95 % | Nueva campaña de campo. Se omiten los conjuntos censurados. |
| 08 | Coste `ns/intento` vs `L` y `ns/evento` vs `L` | CSV crudos de escalabilidad; se divide CPU total agregado entre trabajo total agregado. |
| 09 | `S_CPU` vs aceptación Standard, color por `L` | CSV crudos de escalabilidad, distinguiendo `H` y dinámica. |

Las distribuciones de la familia 01–03 se producen, si están presentes, para los tres puntos históricamente inconclusos (Glauber 0.8 y 0.9; Metropolis 0.8, todos a H=-0.75, L=32) y una referencia Glauber T=1.5. Se obtiene una figura PNG y una PDF **por caso y familia**. Las familias 06, 08 y 09 abarcan más condiciones.

## Dónde quedan los resultados y cómo se protegen

```text
results/nivel2/
  medidas/
    campo/campo_<ID>/
      config.json, manifest.json, raw/*.csv
    temperatura/temperatura_<ID>/config.json, manifest.json, raw/*.csv
    tamano/tamano_<ID>/config.json, manifest.json, raw/*.csv
    trazas/traza_<ID>/
      config.json, manifest.json
      standard_trace.csv, nfold_trace.csv
      standard_frame_index.csv, nfold_frame_index.csv
      standard_frame_*.csv, nfold_frame_*.csv
  graficas/figuras_<ID>/
      01_*.png/.pdf ... 09_*.png/.pdf
      tabla_campo_bootstrap.csv
      tabla_activacion_bootstrap.csv
      tabla_costes_y_aceptacion.csv
      diagnostico_distribuciones.csv
      manifest_figuras.json
```

La carpeta de cada ejecución utiliza ID único (fecha UTC con microsegundos más código aleatorio), sin sobreescritura; al regenerar una figura se crea una nueva carpeta. Las trazas y matrices usan además creación exclusiva de ficheros. La salida histórica bajo `simulator/results/`, `results/processed/`, `results/snapshots/`, `figures/final/` y `release/` **no se modifica**. Un error conserva los datos parciales y registra `ERROR.json`.

## Convenciones físicas y advertencias

- Ising 2D, condiciones periódicas, `N=L²`, estado inicial de todos los espines `+1`, campo negativo y parada en el primer `M<=0`. Valores de `L` pares.
- Tiempo: `τ = attempts/L²` para Standard y `τ = equivalent_attempts/L²` para n-fold; **no son segundos**. La selección de sitio es aleatoria y las probabilidades microscópicas corresponden a Glauber o Metropolis.
- La comparación de equivalencia física es **Standard vs n-fold de la misma dinámica**. No hay igualdad de trayectorias individuales entre algoritmos.
- El histograma de `log10 τ` usa una **densidad**: su integral respecto a `log10 τ` vale 1, no es la densidad de `τ`.
- La supervivencia y ECDF implementadas son estimadores empíricos **para muestras completas**. Si un proceso queda truncado, **no se descartan silenciosamente los no escapados**: se rechazan las figuras de media y distribución para ese punto. Se necesitaría Kaplan–Meier e inferencia de censura para analizar esos datos sin sesgo.
- Las bandas y barras de media resultan de bootstrap percentil al 95 %, con una semilla numérica fija del análisis. No deben confundirse con prueba concluyente de equivalencia o con intervalos corregidos por multiplicidad.
- La gráfica tipo Arrhenius es *diagnóstica*. No se presupone barrera térmica fija ni exponentes críticos.
- `ns/intento` y `ns/evento` son **operaciones distintas**. La aceleración total se presenta por separado. El CPU de C se recoge con `clock()`; depende de máquina y compilador.
- Un tracer con `--max-steps` finaliza sin necesariamente escapar: la interpretación y los límites son distintos (intentos en Standard y eventos en n-fold). Dejar límite 0 para análisis de primer paso completos.
- La generación de gráficas de campañas térmicas y de escalabilidad nuevas se distingue mediante su ID, para no mezclar muestras nuevas e históricas. Las cifras de campañas con pocas realizaciones son solo diagnósticas.
- El valor `--max-frames` limita las instantáneas intermedias; la instantánea final se conserva. El espaciado es por eventos, pero el índice almacena el tiempo estocástico exacto.

## Reproducibilidad y release original

`nivel2/baseline_original.json` guarda el SHA-256 de los **375 archivos originales que no se han modificado**. Solo cambia `simulator/CMakeLists.txt` porque incluye un nuevo ejecutable observacional. Por ello, las herramientas de verificación de **release congelada v1.0.0** pueden denunciar justamente la modificación de CMake o la aparición de archivos nuevos: **no** se han reescrito sus firmas para ocultarlo. La comprobación propia es:

```powershell
python -m nivel2.scripts.check_baseline
python -m nivel2.scripts.validate_level2
```

La segunda requiere compilar primero. Demuestra equivalencia del resultado exacto por stream del trazador y el ejecutable de producción, además de recomputar energía con enlaces periódicos para **cada snapshot**. Las pruebas de CTest y Python preexistentes deben mantenerse.

**Estado de las campañas incluidas en este paquete:** los gráficos de las familias 01–03, 06, 08, 09 reutilizan el histórico original; el barrido nuevo de campo `L=32, T=1.5, H={-0.75,-1,-1.5,-2,-3}`, 100 escapes por punto y algoritmo/dinámica, es **exploratorio**, no un nuevo resultado de alta precisión. Las trayectorias trazadas son ejemplos reales de una realización con `L=32`, `T=1.5`, `H=-0.75`, Glauber, semilla `20261115`; no son promedios. Cualquier campaña más precisa puede lanzarse con `-Runs 500` o más y se almacenará de forma aislada.
