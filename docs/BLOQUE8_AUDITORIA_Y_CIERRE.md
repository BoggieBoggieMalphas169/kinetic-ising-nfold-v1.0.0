# Bloque 8 — Auditoría reproducible y cierre científico

## Diseño

El bloque 8 no añade cambios al motor C original. Consolida la práctica y deja una auditoría repetible de la release histórica de septiembre y las nuevas campañas B1–B7. La etiqueta PASS del auditor significa **integridad técnica de datos y pruebas**, y no equivale a PASS físico en todas las condiciones.

### Archivos B8

- `scripts/practica_cierre/cierre_b8.py`: auditoría, controles de CSV, hashes, estadísticas y tres figuras finales.
- `tests/test_bloque8_cierre.py`: siete pruebas de integridad estadística, rutas, unidades MCSS, duplicados semilla/stream y muestras fijas.
- `powershell/14_cierre_practica_b8.ps1`: ejecuta la auditoría, con parámetro `-Rapida` para saltar compilación/pytest.
- `powershell/Ising_Practica_Master.ps1`: nueva opción 17.
- `docs/entrega/INFORME_FINAL_PRACTICA.md` y `.pdf`: memoria científica final.
- `docs/entrega/figuras/`: imágenes publicables generadas desde los CSV de B6/B7.
- `results/practica_cierre/<id>_cierre_b8_*/`: informe máquina/Markdown, registros de pruebas y figuras regeneradas.

## Comprobaciones técnicas

1. `scripts/release_check.py --verify-frozen` y snapshot: PASS.
2. Los 374 archivos originales del manifiesto SHA-256 se conservan sin modificaciones.
3. CMake/CTest: 6/6 pruebas del motor C original, más 1/1 prueba C de integración del motor de trazas.
4. `pytest`: 158/158 pruebas Python; 6 advertencias de deprecación.
5. B6: 24 CSV con hashes correctos; 8400 realizaciones; 12 razones de medias recomputadas; 12 PASS, cero censuras.
6. B7: 6 CSV con hashes correctos; 28000 nuevas realizaciones; 3 razones de medias recomputadas; 2 PASS y 1 INCONCLUSIVE; cero censuras.
7. En B2 hay 22 PNG científicos; B4 conserva 11 figuras; B5 conserva seis GIF y seis MP4; P08 conserva seis figuras principales.
8. Se contrastan unidades MCSS = intentos equivalentes / L², criterios de escape M=0, parámetros, semilla+stream y nombres de algoritmo/dinámica en cada fila de B6/B7.

## Conclusiones defendibles

El método n-fold proporciona la misma probabilidad condicional de próximo evento y el mismo reloj de intentos del método Standard para cada regla microscópica si está implementado correctamente. El análisis cuantitativo demuestra compatibilidad dentro del margen práctico predefinido en la mayoría de puntos analizados, sin resolver todavía un caso frío de Metropolis. Las animaciones representan trayectorias reales, pero no demuestran equivalencia de distribuciones. La ventaja computacional depende del régimen de aceptación.

## Advertencias necesarias

- El caso Metropolis T/J=0.8, H/J=-0.75, L=32 sigue INCONCLUSIVE con R_tau=0.9609 e IC95% [0.9175,1.0038].
- No borrar ni actualizar los snapshots de septiembre. B6 y B7 son ampliaciones etiquetadas por separado.
- No confundir KS sin rechazo con demostración de igualdad exacta.
- No presentar los tiempos CPU exploratorios B6 como benchmark de compilador/hardware P07D/E.
- Las pruebas ejecutadas para B8 se realizaron en Linux. Los scripts PowerShell deben ejecutarse y comprobarse en el ordenador Windows final.
- Verificar los requisitos formales específicos del profesor antes de entregar.
