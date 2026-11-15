# Bloque 6 — Barrido de campo: vida media de escape y equivalencia cinética

## Objetivo

Cerrar la figura de nivel 2 `N2.09`: la dependencia del **tiempo medio de primer paso** con la intensidad del campo negativo, conservando la especificación científica de la release `v1.0.0`:

\[
\mathcal H=-J\sum_{\langle ij\rangle}s_i s_j-H\sum_i s_i,\qquad
s_i=\pm1,\quad s_i(0)=+1,\quad H<0.
\]

Finalización al alcanzar por primera vez `M=0`. La unidad de tiempo es MCSS (`attempts / L²`). Para una comparación físicamente válida, se conserva la misma dinámica de Glauber o Metropolis y todos los demás parámetros al variar `H`.

## Qué se ha añadido

- `scripts/practica_cierre/barrido_campo_b6.py`: configuración de pilotos/campañas, compilación de binarios **originales** en una carpeta temporal por ejecución, validaciones C/CTest, ejecución de ensembles, sumarios, bootstrap y figuras.
- `powershell/10_barrido_campo.ps1`: piloto reproducible o campaña de práctica parametrizada.
- `powershell/11_analizar_barrido_campo.ps1`: genera una carpeta nueva de análisis desde cualquier campaña B6 verificada.
- `powershell/Ising_Practica_Master.ps1`: opciones `13` y `14`.
- `tests/test_bloque6_campo.py`: diseño, semillas, magnitudes de tiempo, estadísticas, seguridad del manifiesto, tratamiento de censura y figuras sin datos completos.

No se modifican `simulator/src/*`, `results/snapshots/*`, los datos P06 ni los ficheros cubiertos por `release/release_manifest.csv`.

## Diseño y resultados ejecutados

### Piloto

`L=16`, `T/J=1.5`, `J=1`, `H/J=-3,-2.5,-2,-1.5,-1,-0.75`; `35` runs por algoritmo/campo/dinámica (840 runs en total). Sirve para probar el circuito y observar costes. **No** se usa como evidencia concluyente de equivalencia al 5%.

### Campaña ampliada (resultados nuevos)

`L=32`, `T/J=1.5`, `J=1`, los mismos seis campos, **350 runs por cada algoritmo/campo/dinámica (8.400 realizaciones)**. Los 8.400 escapes se observaron dentro del horizonte. Se aplicaron `1200` réplicas de bootstrap independientes en cada par.

En los 12 pares, el intervalo bootstrap 95% de la razón de medias se sitúa dentro de `[0.95,1.05]`, un criterio de equivalencia práctica convenido. Este resultado no elimina ni revisa las tres inconclusiones previas a `T/J=0.8/0.9`; corresponde a otro dominio físico.

Los histogramas/curvas de supervivencia del bloque 2 y las animaciones de B5 son experimentos diferentes: no deben mezclarse sin emparejar `L,T,J,H,dynamics`.

## Interpretación de resultados

- Al aumentar `|H|/J` en el intervalo probado, el escape es más rápido. Se favorece energéticamente la inversión de dominios y se reduce la espera metaestable.
- Standard y n-fold proporcionan medias compatibles en la campaña ampliada: el n-fold evita rechazos computacionales, no modifica las tasas relativas de transición de la dinámica correspondiente.
- Se trata de una observación **a un tamaño y temperatura determinados**, no de una determinación del campo crítico ni de una validación universal de una ley de nucleación.
- Los tiempos CPU por realización son indicadores exploratorios: no sustituyen un benchmark controlado de P07D/P07E.

## Tratamiento de censura

Los dos ejecutables admiten un límite temporal en intentos. Standard se detiene al llegar al límite; el motor n-fold puede ejecutar el siguiente evento tras un salto geométrico que sobrepase el horizonte. Para permitir comparaciones **sin modificar el motor**, el análisis B6 recorta esa observación al horizonte predefinido y la clasifica como censurada, incluso si el evento posterior alcanza `M=0`.

Si un par Standard/n-fold tiene una sola observación censurada, **no se calcula la media incondicional ni se asigna PASS/FAIL** para ese campo. Se registran las fracciones de escapes y la necesidad de ampliar el horizonte. Así se evitan medias de solo supervivientes o filtrar pérdidas silenciosamente. Un trabajo posterior podría incorporar métodos de supervivencia (Kaplan-Meier, RMST), definidos con suficiente información y una regla de censura coherente.

## Salidas y trazabilidad

Cada ejecución ocupa `results/practica_cierre/<id>_barrido_H_b6_*/` con `DISENO.json`, `datos_nuevos/barrido_H/*.csv` (24 pares de archivos en campañas completas), `MANIFEST_DATOS_B6.json` con semillas/hashes, `resumen_barrido_H.csv`, `MANIFEST_B6_SALIDAS.csv`, `figuras_b6/` (cuatro figuras PNG+PDF), logs, `RESUMEN.md` y `ESTADO.json`.

Las figuras son:

- `N2_09_vida_vs_campo_{glauber|metropolis}.png/.pdf`: medias + IC bootstrap en escala semilog y ambos algoritmos.
- `N2_10_equivalencia_censura_{glauber|metropolis}.png/.pdf`: razón de medias con IC y fracción que escapó por campo.

Las semillas derivan de SHA-256 a partir de semilla de la campaña, dinámica, algoritmo y campo: son estables y diferenciadas. Se comparan **distribuciones estadísticas**, no trayectorias idénticas con la misma secuencia RNG.

## Uso en Windows / PowerShell

Desde la raíz de la carpeta extraída:

```powershell
python -m pip install -r requirements.txt
& ".\powershell\Ising_Practica_Master.ps1"
```

Elegir `13` genera el piloto; `14` pregunta por la carpeta existente que se desea analizar otra vez. También:

```powershell
# Piloto predeterminado: 40 realizaciones por combinación
& ".\powershell\10_barrido_campo.ps1" -Perfil piloto

# Campaña mayor: se crea una carpeta nueva. No sobrescribe el baseline.
& ".\powershell\10_barrido_campo.ps1" -Perfil practica -Runs 500

# Barrido personalizable, manteniendo H negativo:
& ".\powershell\10_barrido_campo.ps1" -Perfil piloto -L 16 -T 1.5 -Runs 100 `
   -Campos '-3,-2.5,-2,-1.5,-1,-0.75' -Dinamicas ambas

# Análisis nuevo, sin relanzar la simulación ni sobrescribir CSV
& ".\powershell\11_analizar_barrido_campo.ps1" -DirectorioBarrido '.\results\practica_cierre\ID_barrido_H_b6_XXXXXXXX'
```

Requisitos: CMake y compilador C, Python con requirements, PowerShell. Los `.ps1` se han inspeccionado pero no ejecutado en Windows en esta sesión. Se utilizan rutas **relativas y ASCII para el argumento `--output` del ejecutable C**, ejecutando cada simulación desde su directorio de campaña; esto evita dificultades por tildes en las rutas de Windows.

## Próximos bloques

- **B7**: estudio de los tres puntos históricos inconclusos en `L=32`, `H/J=-0.75`, `T/J=0.8/0.9`. Sus muestras deben ampliarse de forma controlada y analizar colas, sin forzar PASS.
- **B8**: auditoría final, compilación en el ordenador del estudiante, actualización de la memoria e informe entregable.
