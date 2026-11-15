# Bloque 4 - Trayectorias, magnetizacion y energia (Practica de Ising)

## Alcance y origen de datos

Este desarrollo **no introduce dinamicas nuevas ni modifica el motor C**. Lee las trazas validadas del bloque 3 (`simulator/tracing/`) y produce datos derivados y figuras mediante `scripts/practica_cierre/visualizacion_b4.py`.

La fuente consta de `trayectoria_events.csv` (todos los eventos aceptados, con sus esperas en intentos) y `trayectoria_frames.csv` (instantaneas espaciadas en **numero de eventos**, mas los estados inicial y final). La salida del bloque 4 se guarda en una carpeta de ejecucion nueva `results/practica_cierre/<id>_visualizacion_b4_<uuid>/`.

## Definiciones y convenciones fisicas

Para una red cuadrada de lado `L` y `N=L^2`:

- `m(t) = M(t)/N`, donde `M = sum_i s_i`.
- `e(t) = E(t)/N`, con `E = -J sum_<i,j> s_i s_j - H sum_i s_i`, contando cada enlace una vez.
- `t = attempts/N` en **MCSS**. En n-fold, `attempts` representa intentos Standard equivalentes sorteados por el reloj geometrico exacto del modelo discreto.
- Entre dos eventos aceptados no cambia el estado, aunque siga pasando tiempo. Por eso las graficas temporales se dibujan como escalones. Si termina una trayectoria por un limite de intentos sin un evento adicional, se agrega un ultimo punto en el instante terminal sin cambiar los observables.
- Los fotogramas B3 no estan equiespaciados en MCSS. El mosaico B4 selecciona para cada tiempo objetivo **el ultimo fotograma disponible que ya ha ocurrido**, sin interpolar ni inventar espines. Puede mostrar menos paneles que los solicitados si se repiten tiempos observados.
- Una trayectoria con `reached_M0=0` se marca **CENSURADA**, no como escape. Las figuras de una realizacion **no** prueban equivalencia estadistica. Las pruebas de equivalencia son las del analisis P08/B2 con ensembles independientes.

## Salidas de B4

| Nombre | Contenido |
|---|---|
| `B4_00_datos_series_*.csv` | Datos por **cada evento aceptado** (mas tiempo inicial y cola final de rechazos, si existe); indices, intentos, MCSS, M, E, M/N y E/N |
| `B4_01_series_*.png/.pdf` | Dos paneles por combinacion: magnetizacion y energia frente a MCSS |
| `B4_02_instantaneas_*.png/.pdf` | Configuraciones de Ising observadas y tiempos/magnetizacion/energia de cada frame |
| `B4_03_comparacion_*.png/.pdf` | M(t) y E(t) en las dos realizaciones Standard/n-fold de la **misma regla** y condiciones |
| `B4_04_galeria_estados_finales.png/.pdf` | Cuatro estados terminales, solo si existen las cuatro combinaciones y parametros comunes |
| `B4_05_frames_seleccionados.csv` | Registro exacto de frames escogidos y hash de cada configuracion |
| `B4_06_resumen_fisico.csv` | Metadatos, estados de escape/censura, hashes de los CSV de origen |
| `MANIFEST_B4.json`, `SHA256_B4.csv`, `RESUMEN.md` | Proveniencia y verificacion de cada derivado |

## Como ejecutarlo

Desde PowerShell, situate en cualquier carpeta y ejecuta el PS1 del repositorio por su ruta:

```powershell
& '.\powershell\06_generar_visualizaciones.ps1'
& '.\powershell\07_validar_visualizaciones.ps1'
```

Tambien hay opciones `9` (generar) y `10` (validar) en `powershell/Ising_Practica_Master.ps1`.

Si deseas usar una campaña B3 especifica:

```powershell
& '.\powershell\06_generar_visualizaciones.ps1' -DirectorioTrazas 'results/practica_cierre/MI_CAMPANA_B3' -Paneles 7 -Dpi 180
```

No vuelvas a simular para regenerar B4. Para producir **nuevas trazas fisicas**, usa primero la opcion 7 del menu, y despues la 9.

Alternativa independiente de PowerShell:

```bash
python -m scripts.practica_cierre.visualizacion_b4 generar
python -m scripts.practica_cierre.visualizacion_b4 validar
```

## Validacion y limites

1. Se valida *antes* de dibujar la campaña B3: SHA-256, coherencia de todos los eventos, energia y magnetizacion reconstruidas, resultados comparados con el ejecutable original y con el control sin trazas.
2. Se exige que los archivos declarados por `release/release_manifest.csv` no hayan cambiado.
3. Se comparan los hashes de la fuente B3 antes y despues de generar los productos.
4. El verificador de salida B4 comprueba las fuentes y cada hash nuevo; vuelve a reconstruir los CSV de series a partir de las trazas originales.
5. Los tiempos de CPU de las versiones instrumentadas **no son benchmarks** y no se deben comparar como speed-ups.
6. Este bloque **no genera GIF ni MP4**. La animacion con un reloj temporal riguroso es tarea del bloque 5.
7. No se han repetido las campañas de campo debil para este bloque; la muestra integrada con `H/J=-3` es una demostracion de instrumentacion y visualizacion.

## Relacion con B5

El archivo `trayectoria_frames.csv` conserva una malla de Ising y un instante MCSS por fotograma; sera la entrada de B5. Al construir GIF/MP4 debe decidirse explicitamente entre reproduccion a tiempo MCSS proporcional (duraciones de fotograma variables) o presentacion secuencial con un **reloj MCSS rotulado**, sin presentarla como tiempo uniforme.
