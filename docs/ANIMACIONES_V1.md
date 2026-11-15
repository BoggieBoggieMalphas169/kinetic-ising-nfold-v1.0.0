# Animación física real — release 1.0.0 (complemento no invasivo)

Se añade una **capa de observación** para visualizar los procesos que realmente calcula el núcleo C del repositorio: reglas de aceptación **Glauber/heat-bath** y **Metropolis**, cada una con implementaciones **Standard** (intentos con posible rechazo) y **n-fold way** (selección de eventos y tiempo de espera geométrico). No hay código Python que reinvente la dinámica.

## Uso rápido en Windows / PowerShell

Desde la carpeta raíz del repositorio:

```powershell
python -m pip install -r requirements-animation.txt
.\run_animaciones.ps1
```

Si PowerShell bloquea el script, sin cambiar la política global:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_animaciones.ps1
```

Personalización:

```powershell
.\run_animaciones.ps1 -L 32 -T 1.6 -J 1 -H (-1.0) -MCSS 13 -Frames 65 -Fps 9 -Seed 250519
```

Requisitos: CMake, compilador C soportado por CMake (MSVC o GCC), Python 3 con NumPy, Matplotlib y Pillow. El ejecutable se construye automáticamente. Si Python no está en PATH: `-Python '.\.venv\Scripts\python.exe'`. Al cambiar de máquina o tras modificar C, deja que CMake vuelva a compilar (no uses `-SkipBuild`).

Se crean carpetas exclusivas en `results/animations/AAAAMMDD_HHMMSS_<id>/` con:

- `ising_cuatro_dinamicas.gif`: cuatro redes y magnetizaciones sincronizadas por tiempo MCSS;
- `ising_cuatro_dinamicas.png`: fotograma fijo de referencia;
- cuatro archivos `glauber_standard.csv`, `glauber_nfold.csv`, `metropolis_standard.csv`, `metropolis_nfold.csv`;
- `parametros.json`: parámetros y semillas.

**El script no modifica ni sobrescribe los resultados publicados en la release.** Cada ejecución escribe en un directorio nuevo.

## Qué significa el GIF

- Cada cuadrado coloreado es un espín de Ising 2D, con condiciones de contorno periódicas tal y como las define `ising.c`.
- Parte de la red completamente magnetizada `s=+1` y utiliza el mismo Hamiltoniano, temperatura, acoplamiento y campo que los programas de la release.
- Los cuatro paneles muestran *realizaciones aleatorias independientes* (aunque se use la misma semilla de arranque, los algoritmos consumen números aleatorios de forma distinta). No se deben exigir imágenes iguales fotograma a fotograma.
- **En Standard**, cada intento selecciona un sitio aleatorio y lo acepta o rechaza usando `dynamics_probability`. El CSV registra solo las aceptaciones; los rechazos se deducen de la diferencia entre intentos y aceptaciones. Su columna `wait` cuenta los intentos desde la última aceptación.
- **En n-fold**, cada llamada a `nfold_step` selecciona una clase y un sitio, ejecuta un flip real y avanza el reloj mediante `nfold_sample_wait(Q)` (espera geométrica). Se registran el sitio elegido, la clase, el estado y la probabilidad total `Q` anterior al evento.
- Los dos algoritmos deben compararse a **igual tiempo físico discreto equivalente**, `t = intentos / L²`, no igual número de llamadas o cambios de espín. Esto sincroniza la animación.
- Como en los experimentos de **primer paso de la release**, las trayectorias se detienen cuando `M=0`. El último estado queda congelado en el resto de la animación. No representa equilibrio térmico ni una magnetización estacionaria.
- Los distintos algoritmos pueden tener tiempos de primer paso diferentes en una sola realización debido al azar. Una animación *no* prueba equivalencia estadística, ausencia de sesgos ni mejora de rendimiento; esas conclusiones requieren muchas muestras y las pruebas de la release.

## Formato de las trazas

`clock,site,accepted,M,E,wait,class,Q`: solo hay una fila inicial (`clock=0`) y después una fila por flip aceptado. Para Standard, `Q` es la probabilidad de aceptación del **sitio** y no la probabilidad global; para n-fold, `Q` es el valor **global previo** a la transición. No deben compararse estas columnas directamente entre métodos. `class` es la clase elegida inmediatamente antes de invertir el espín.

Para modificar gráficos sin repetir simulación, reutiliza los cuatro CSV y ejecuta:

```powershell
python scripts/render_animation.py --trace-root 'results/animations/CARPETA_EXISTENTE' --L 32 --T 1.6 --J 1 --H -1 --mcss 13 --frames 80 --fps 10 --output 'results/animations/CARPETA_EXISTENTE/nueva_animacion.gif'
```

La reconstrucción gráfica verifica que el cambio de cada sitio reproduce exactamente la magnetización y la energía de Ising registradas, que los relojes crecen y que cada espera coincide con la diferencia entre relojes.

## Modificaciones incorporadas

- `simulator/src/main_animation_trace.c`: adaptador independiente; utiliza `ising_init`, `ising_flip`, `ising_delta_energy`, `dynamics_probability`, `nfold_state_init`, `nfold_step` y el RNG del motor, **sin editar las implementaciones originales**.
- `simulator/CMakeLists.txt`: añade el destino opcional `ising_animation_trace`.
- `scripts/render_animation.py`: reconstruye las redes a partir de los flips reales; crea GIF y PNG.
- `run_animaciones.ps1`: orquestación reproducible y resultados protegidos contra sobrescritura.
- `requirements-animation.txt`: dependencias de visualización.

### Precaución sobre el reloj n-fold

Una transición n-fold puede producirse después del límite de tiempo solicitado. El registrador descarta esa transición de la traza si rebasa el horizonte (aunque el paso ya haya sido calculado internamente), de manera que solo se visualiza la trayectoria dentro del intervalo demandado. No afecta a la dinámica ni a los programas originales.
