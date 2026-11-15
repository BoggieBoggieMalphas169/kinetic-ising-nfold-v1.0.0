# BLOQUE 4 - Visualizacion de trayectorias de Ising

Este ZIP integra **B1 + B2 + B3 + B4**. No sustituye ni modifica el motor C historico.

- `powershell/Ising_Practica_Master.ps1`: menu principal; opcion **9** genera B4, **10** valida B4.
- `powershell/06_generar_visualizaciones.ps1`: render de curvas y mosaicos desde trazas B3 existentes.
- `powershell/07_validar_visualizaciones.ps1`: comprobacion del origen, hashes y reconstruccion de series.
- `scripts/practica_cierre/visualizacion_b4.py`: implementacion Python.
- `docs/BLOQUE4_VISUALIZACIONES.md`: fisica, decisiones computacionales y limites.
- `results/practica_cierre/*_visualizacion_b4_*/`: 11 figuras de ejemplo en PNG/PDF y archivos derivados.

Pasos en PowerShell: `& '.\powershell\Ising_Practica_Master.ps1'` > opcion **9** y despues **10**. El modo render **no ejecuta simulaciones C**. Si quieres otros parametros fisicos, primero genera una campaña B3 (opcion 7).

**Importante:** son realizaciones independientes, no promedios de ensemble. MCSS no representa segundos. La animacion GIF/MP4 es el siguiente bloque B5.
