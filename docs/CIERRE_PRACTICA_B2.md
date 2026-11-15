# Bloque 2 - Graficas nuevas de Nivel 2

Esta extension, sucesora de B1, no modifica el motor C ni los datasets de la release
integrada `v1.0.0`. Produce figuras y diagnosticos **nuevos**, no modifica `figures/final`
ni el snapshot congelado. Las comparaciones historicas siguen siendo 49 PASS,
3 INCONCLUSIVE y 0 FAIL, sin reinterpretar los casos inconclusos.

## Ejecutar en Windows

```powershell
& '.\powershell\Ising_Practica_Master.ps1'
# opciones 4 (todas), 5 (distribuciones) y 6 (rendimiento)
# o directamente:
& '.\powershell\03_generar_nivel2.ps1' -Solo all
```

Usa el ejecutable del `.venv` preparado en B1; también permite `-Python "C:\...\python.exe"`.
Equivalente multiplataforma: `python -m scripts.practica_cierre.nivel2 --solo all`.

## Resultados

Cada invocacion genera una carpeta nueva, sin sobrescribir ejecuciones previas:
`results/practica_cierre/<ID>_nivel2/`.

- `figuras_nivel2/`: PNG y PDF vectoriales. Las familias N2.1-N2.3 generan cuatro
  condiciones (tres inconclusas y un control) cada una.
- N2.4: cuatro combinaciones dinamica/campo, usando todas las temperaturas del
  barrido P06. `N2_04_bootstrap_medias.csv` conserva intervalos bootstrap (400 replicas,
  semillas de bootstrap fijas y reproducibles).
- N2.5: cuatro graficas de costo por operacion basadas en los resúmenes historicos de escalabilidad P06.
- N2.6: dos figuras de aceleracion CPU frente a aceptacion Standard (una por regla dinamica),
  con los campos debil/fuerte identificados.
- `N2_01_03_diagnosticos.csv`: tamanos de muestra, medias, razon, KS exploratorio no ajustado.
- `MANIFEST_SALIDAS.csv`: lista de archivos con SHA256; `metadata.json`: procedencia,
  software, fuentes y hashes; `RESUMEN.md`: alcance y precauciones.

**Precauciones fisicas:** tiempos en MCSS, no segundos. Los intervalos de `ln(<tau>)`
son percentiles bootstrap de la media transformada. La recta para T<=1.2 es un
**ajuste local descriptivo**, no una barrera de nucleacion universal. El KS calculado
solo describe las curvas representadas; no sustituye el contraste con correccion
Holm de P08 ni demuestra igualdad si no rechaza. Los tiempos por operacion y
speed-up son datos historicos del hardware de P06, no nuevos benchmarks.
Los CSV actuales se comprueban antes de generar: pertenecen a pares iguales en
L,T,J,H y dinamica, y todas las realizaciones llegan a M=0; si aparecen censuras
futuras, el programa **se detiene** en vez de estimar una ECDF incorrecta.

## Estado del resto de la practica

Queda para B3/B4 la instrumentacion C pasiva de trazas espaciales M(t), E(t) y
snapshots, y despues (B5) la generacion de GIF/MP4. La dependencia de la vida
media con mas valores de |H| (nueva campana) y la precision de los tres casos
inconclusos requieren nuevas ejecuciones y no se inventan en B2.
