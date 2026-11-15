# Informe de validacion: Bloque 2 - Nivel 2

**Fecha:** 15-11-2026.  **Base:** release integrada `v1.0.0` y B1.

## Pruebas ejecutadas en este entorno (Linux)

| Control | Resultado |
|---|---|
| Release historica `scripts/release_check.py --verify-frozen` | **PASS** |
| Snapshot `snap_0cc46433731097c4` | **VERIFIED** |
| Compilacion C (CMake Release) | **PASS** |
| CTest (fisica, n-fold, smoke y CSV) | **6/6 PASS** |
| Suite Python completa, incluidas 6 pruebas nuevas de B2 | **96/96 PASS** |
| Generacion completa N2.1-N2.6 | **PASS** |
| Salidas graficas | **22 figuras, cada una PNG + PDF = 44** |
| Salidas CSV derivadas | **3** |
| Coincidencia de medias de CSV de nivel de realizacion y resumen termico | **PASS** |
| Fuentes P06 y snapshot alterados | **0** |
| Repetibilidad de salidas PNG + CSV (dos ejecuciones) | **25/25 hashes identicos** |
| Inspeccion de PDF renderizado y PNG principal | **PASS** |

El bloque se ha ejecutado con 56 CSV de tiempo de escape del barrido termico
(**98.600 realizaciones**), mas los resúmenes historicos de escalabilidad.
Se detectaron **0 realizaciones censuradas** en esas 56 series; el programa
se niega a producir ECDF/supervivencias ingenuas si el archivo contiene
`reached_M0=0`. Tambien rechaza datasets duplicados, pareados incompletos y
fuentes cuyo SHA-256 difiere del manifiesto.

Las nuevas figuras documentan, pero **no vuelven a estimar la clasificacion
oficial de equivalencia**: 49 PASS, 3 INCONCLUSIVE y 0 FAIL permanecen sin
cambios. El grafico ECDF (Glauber, H/J=-0.75, T/J=0.8) produce un valor
KS exploratorio D=0.17333, consistente con el CSV de la campaña; esto no
constituye prueba de discrepancia confirmada tras ajuste de Holm.

## Limitaciones explicitas

- **PowerShell en Windows** no se ha probado en este entorno: los `.ps1` se
  inspeccionaron e integraron, pero la comprobacion de ejecucion de Windows
  sigue siendo una tarea local del usuario.
- Los archivos PDF pueden incorporar metadatos de creacion; se verifico la
  consistencia de 22 PNG y los CSV byte a byte, **no identidad binaria de PDF**.
- No se ha modificado el motor C: no existe todavia exportacion de
  configuraciones intermedias ni animacion.
- No se ha simulado ningun nuevo valor de campo ni se han ampliado las
  tres condiciones estadisticamente inconclusas.

## Instrumentacion nueva

- `scripts/practica_cierre/nivel2.py`: contratos, estadistica, generacion y auditoria.
- `powershell/03_generar_nivel2.ps1`: ejecucion directa (modos all, distribuciones, rendimiento).
- `powershell/Ising_Practica_Master.ps1`: menu con opciones 4-6 nuevas.
- `tests/test_nivel2_practica.py`: 6 pruebas de logica y deteccion de errores.
- `docs/CIERRE_PRACTICA_B2.md`: contrato de entradas/salidas, hipotesis y limitaciones.

**Estado:** bloque 2 implementado y verificado en Linux; comprobacion de
Windows y desarrollo fisico de trazas reservados para B3.
