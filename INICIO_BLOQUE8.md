# Ising — Cierre de la práctica, bloque 8

**Versión de partida intacta:** `v1.0.0` (30-09-2026); snapshot `snap_0cc46433731097c4`.
**Implementación de cierre:** bloques B1–B8 integrados, sin nueva regla cinética.

## 1. Por dónde empezar

1. Lee `docs/entrega/INFORME_FINAL_PRACTICA.pdf` (síntesis científica de entrega).
2. Lee `docs/BLOQUE8_AUDITORIA_Y_CIERRE.md` (pruebas, reproducibilidad, límites).
3. Ejecuta desde PowerShell `& ".\powershell\Ising_Practica_Master.ps1"` y selecciona la opción **17**.
4. Abre el archivo `ESTADO_B8.json` de la nueva ejecución en `results/practica_cierre/` y comprueba `status=passed`.
5. Examina las tres figuras de síntesis y el resultado **INCONCLUSIVE** de Metropolis frío.

## 2. Ejecutar sin PowerShell

```shell
python -m pip install -r requirements.txt
python -m scripts.practica_cierre.cierre_b8 --tests
```

La auditoría compila C en un directorio temporal, ejecuta CTest y pytest y comprueba el snapshot, 24 CSV B6, 6 CSV B7, los hashes originales y la coherencia de las medias/tiempos. No lanza miles de trayectorias nuevas.

## 3. Estado de los resultados

- Histórico: 49 PASS, 3 INCONCLUSIVE, 0 FAIL en 52 comparaciones de campaña, 44 puntos físicos únicos.
- B6: 12 pares PASS sobre 8400 trayectorias nuevas, L=32 T/J=1.5.
- B7: 2 PASS, **1 INCONCLUSIVE** sobre 28000 trayectorias nuevas, L=32 H/J=-0.75.
- B8: auditoría de archivos y regresión. Un `status=passed` de B8 no altera ninguna clasificación física.

## 4. Pendiente en el ordenador final

Los PS1 de los bloques 1–8 deben probarse en Windows, junto con las rutas locales, CMake, Python y dependencias. Este ZIP se generó y se validó en Linux; no afirma compatibilidad Windows demostrada.

Para el portfolio posterior (no para entregar esta práctica) quedan opciones como Potts, Kawasaki, optimización P07D/E y estudios cinéticos de nuevas geometrías.
