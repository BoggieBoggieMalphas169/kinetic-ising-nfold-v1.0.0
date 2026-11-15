# Ising cinetico: Bloque 2 - instrucciones de uso

**Producto:** repositorio integrado B1 + B2, con las graficas Nivel 2 N2.1-N2.6
ya generadas en una ejecucion de ejemplo, junto con sus scripts de regeneracion.
**Base fisica:** release `v1.0.0`, snapshot `snap_0cc46433731097c4`.

## 1. Abrir en PowerShell (Windows)

1. Descomprime `Ising_B2_Nivel2_integrado.zip` completo **en una carpeta nueva**.
2. Abre PowerShell dentro de `kinetic-ising-nfold-v1.0.0`.
3. Si no tienes el entorno de B1 preparado en esta carpeta:

   ```powershell
   & '.\powershell\00_preparar_entorno.ps1'
   ```

4. Abre el menu:

   ```powershell
   & '.\powershell\Ising_Practica_Master.ps1'
   ```

5. Opciones **4** (todas), **5** (distribuciones) y **6** (rendimiento).
   Alternativa directa:

   ```powershell
   & '.\powershell\03_generar_nivel2.ps1' -Solo all
   ```

6. Si `python` no se reconoce, indica su ruta:

   ```powershell
   & '.\powershell\03_generar_nivel2.ps1' -Solo all -Python 'C:\ruta\python.exe'
   ```

**No se necesita `py` ni volver a compilar C para este bloque.** Se requiere
Python con `numpy`, `pandas`, `matplotlib`, `scipy` (instalados por B1).
Si quieres comprobar la regresion del motor C, usa la opcion 2 de B1.

## 2. Ubicacion de las salidas

Cada ejecucion crea un nuevo directorio independiente:

```
results/practica_cierre/<fecha>_nivel2_<id>/
    figuras_nivel2/
       N2_01_...png / .pdf          supervivencia
       N2_02_...png / .pdf          ECDF y diferencia
       N2_03_...png / .pdf          log10 de tau
       N2_04_...png / .pdf          ln(media tau) vs 1/T
       N2_05_...png / .pdf          ns/intento y ns/evento vs L
       N2_06_...png / .pdf          speed-up vs aceptacion
       N2_01_03_diagnosticos.csv
       N2_04_bootstrap_medias.csv
       N2_06_speedup_vs_aceptacion_datos.csv
    metadata.json                   procedencia y SHA256 de entradas
    MANIFEST_SALIDAS.csv           SHA256 de salidas
    RESUMEN.md                      detalles de cada ejecucion
```

Las opciones 4, 5 o 6 **no** sobrescriben `simulator/results/`,
`results/snapshots/`, `figures/final/` ni otros archivos historicos.
El script comprueba los hashes de las fuentes con el manifiesto de la release
antes de procesar, y vuelve a comprobar que siguen intactas al finalizar.

## 3. Resultados fisicos: como interpretarlos

- **N2.1-N2.3:** tres puntos historicos `INCONCLUSIVE`, mas un control de campo fuerte.
  Un contraste KS exploratorio no ajustado no sustituye la conclusion estadistica
  oficial con correccion por multiplicidad.
- **N2.4:** barras de error bootstrap 95% para `ln(<tau>)`, con 400 replicas por muestra.
  Los ajustes sobre `T/J <= 1.2` son **descriptivos locales**, no una prueba de
  barrera universal de nucleacion.
- **N2.5-N2.6:** datos historicos CPU del hardware/compilador P06: no se hizo
  un benchmark nuevo. `ns/intento` y `ns/evento` tienen denominadores distintos.
- Todos los tiempos de escape se expresan en **MCSS**, no segundos fisicos.

## 4. Alcance y lo que sigue

Este bloque no anade observacion temporal al motor C, nuevas campanas de campo
ni mas realizaciones. Los siguientes pasos son **B3** exportacion pasiva de
trazas/snapshots, **B4** series `M(t),E(t)` y paneles de nucleacion, **B5** GIF/MP4,
posteriormente las campañas adicionales opcionales y el informe final.

Referencia interna: `docs/CIERRE_PRACTICA_B2.md`.
