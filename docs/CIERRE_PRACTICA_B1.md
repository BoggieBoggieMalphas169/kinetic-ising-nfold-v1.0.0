# Cierre de practica: Bloque 1 (reentrada y automatizacion)

**Referencia protegida:** `v1.0.0` (30 de septiembre de 2026), snapshot
`snap_0cc46433731097c4`. **Fecha de implementacion:** 15 de noviembre de 2026.

## Modificaciones efectivas

Se incorporan cuatro scripts PowerShell para Windows (`00_preparar_entorno.ps1`,
`01_validar.ps1`, `02_reproducir_historico.ps1`, `Ising_Practica_Master.ps1`)
y una biblioteca comun (`common.ps1`) en la carpeta `powershell/`.
El controlador independiente `scripts/practica_cierre/validar_baseline.py` permite
realizar las mismas comprobaciones en Windows, Linux o macOS, con reportes por ejecucion.
Hay cuatro pruebas de regresion nuevas en `tests/test_practica_cierre.py`.

No se han tocado `simulator/src`, `simulator/include`, los tests historicos,
las probabilidades de Metropolis/Glauber, el RNG ni el reloj n-fold. Las
salidas de esta fase son locales y se excluyen de Git mediante `results/.gitignore`.

## Resultados de prueba, entorno Linux de construccion

- `scripts/release_check.py --verify-frozen`: **PASS**.
- `scripts.analysis.build_quality_snapshot --verify ...`: **SNAPSHOT VERIFIED**.
- CMake (Release) y CTest: **6/6 PASS**.
- `pytest -q`: **90/90 PASS** (86 tests previos + 4 incorporados).
- Reproduccion 8D en copia temporal: **37/37 artefactos generados**;
  **29/37 archivos coinciden exactamente por SHA-256**; 8 PDF cambian
  por metadatos, pero la comparacion visual pixel a pixel con PyMuPDF
  del entorno de construccion permite comprobar el contenido.
- Cambios en archivos cubiertos por el manifiesto historico: **ninguno**.

Estas pruebas se realizaron en Linux. Los PS1 se han escrito para PowerShell
Windows, pero **es necesario ejecutarlos en el PC Windows** para completar la
validacion especifica de ese entorno y de su compilador C.

## Como continuar

Desde Windows abre `powershell/README_BLOQUE1.md`, prepara `.venv`, ejecuta
`01_validar.ps1` y `02_reproducir_historico.ps1`. No modifiques los archivos
congelados. El siguiente bloque (C2) sera de graficas del Nivel 2 sobre los CSV
historicos, sin modificaciones del motor de simulacion.
