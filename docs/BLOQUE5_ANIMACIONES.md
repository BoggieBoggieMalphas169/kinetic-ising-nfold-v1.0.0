# Bloque 5: animaciones científicas reproducibles de Ising

## Objetivo

Construir GIF y MP4 a partir de la **secuencia completa de eventos aceptados** registrada por el Bloque 3. No es una reconstrucción por inteligencia artificial ni una interpolación de espines. **No se modifica C ni la release v1.0.0**. El Bloque 4 queda preservado.

## Física y escala temporal

Para `N=L²`, cada registro de evento contiene el número acumulado `attempts` (incluidos los rechazos en Standard y el reloj geométrico en n-fold), el sitio invertido y los observables. Cada imagen se calcula en `t = attempts/N` (MCSS); se aplica cada evento cuya marca temporal sea menor o igual que el instante mostrado. La configuración permanece constante en los intervalos sin eventos. **No se interpola el estado**, no se confunde `número de fotograma` con `MCSS` y la duración audiovisual (segundos de GIF/MP4) **no equivale** a un tiempo físico calibrado.

Los instantes para cada clip se distribuyen uniformemente en la escala de *intentos equivalentes*, con cuantización hacia abajo a intentos enteros. Los estados se reconstruyen desde el primer frame `spin_bits` y se aplica cada volteo registrado en `trayectoria_events.csv`. La verificación B3 previa recalcula energía, magnetización y consistencia de cada evento/snapshot.

## Productos

- `B5_01_standard_glauber.gif/mp4`
- `B5_01_standard_metropolis.gif/mp4`
- `B5_01_nfold_glauber.gif/mp4`
- `B5_01_nfold_metropolis.gif/mp4`
- `B5_02_comparacion_glauber.gif/mp4`
- `B5_02_comparacion_metropolis.gif/mp4`
- `B5_00_indice_fotogramas.csv`, con instante MCSS, evento realmente alcanzado, magnetización, energía, hash del estado y bandera de censura.
- `MANIFEST_B5.json`, `SHA256_B5.csv` y `RESUMEN.md` para cada campaña.

Las dos comparaciones usan un **reloj MCSS común** para Standard y n-fold, nunca tiempo normalizado independiente. Cuando uno de los recorridos alcanza su instante terminal antes que el otro, su último estado se **congela solo para la visualización**, con el rótulo FIN. No implica simular más tiempo. Cada motor consume el RNG de manera distinta, por lo que una pareja de realizaciones **no debería** interpretarse como equivalencia trayectoria a trayectoria. Una trayectoria censurada se marca CENSURADA.

## Instalación Windows

Desde la raíz del repositorio (Windows PowerShell):

```powershell
python -m pip install -r requirements_animaciones.txt
& '.\powershell\Ising_Practica_Master.ps1'
```

Seleccionar **11** para generar; **12** para verificar. Para parámetros avanzados:

```powershell
& '.\powershell\08_generar_animaciones.ps1' -Fps 12 -Frames 64 -Dpi 96 -Formato ambos
& '.\powershell\09_validar_animaciones.ps1'
```

Se puede elegir una campaña específica con `-DirectorioTrazas 'results/practica_cierre/MI_CAMPANA_B3'`. Sin ese argumento, se utiliza la campaña B3 válida más reciente. Si no hay trazas, primero generarlas con la **opción 7**. Para ver el modelo en otro régimen (por ejemplo, campo débil), **primero deben generarse trazas B3 nuevas**, evitando tiempos de espera excesivos con límites y registrando las censuras.

Desde terminal Python:

```bash
python -m pip install -r requirements_animaciones.txt
python -m scripts.practica_cierre.animaciones_b5 generar --frames 64 --fps 12 --formato ambos
python -m scripts.practica_cierre.animaciones_b5 validar
```

Los resultados se guardan en un directorio nuevo `results/practica_cierre/<id>_animaciones_b5_<uuid>/` sin sobrescribir fuentes. No se ejecuta el simulador durante la conversión a GIF/MP4. Para más rapidez se puede usar `--formato gif` o `--formato mp4`.

## Validación

- Se comprueba **B3 antes de generar**: eventos ordenados, reloj entero, energía, M, snapshots y correspondencia con el resumen.
- Se exige SHA-256 del manifiesto histórico y se verifican los hashes de las fuentes B3 antes y después.
- Para **cada fotograma**, el validador reejecuta la reconstrucción y comprueba hash de espines, tiempo, M, E y número de eventos.
- La integridad de GIF, MP4 y CSV se controla por SHA-256 dentro del manifest de la nueva campaña.
- Los videos presentan trayectorias particulares: **no son una prueba estadística adicional** y tampoco miden speed-up, porque el coste de escritura afecta al rendimiento.

La ejecución de la conversión solo se ha comprobado en Linux; PowerShell requiere comprobación en el Windows del equipo de la práctica.
