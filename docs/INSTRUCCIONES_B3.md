# Uso del Bloque 3 en Windows — Ising Standard vs n-fold

## Paso 1. Descargar y descomprimir

Descomprime `Ising_B3_Trazas_Integrado.zip` en una carpeta nueva. Este ZIP incluye los archivos previos de B1 y B2. Trabaja dentro de la carpeta `kinetic-ising-nfold-v1.0.0/` que contiene `README.md`, `powershell/` y `simulator/`. Evita mezclar los archivos sueltos del ZIP nuevo con carpetas antiguas.

## Paso 2. Preparar/validar lo anterior

Abre PowerShell en la raíz y ejecuta:

```powershell
& '.\powershell\Ising_Practica_Master.ps1'
```

Las opciones `1` y `2` preparan el entorno Python y comprueban la release. Las opciones 3–6 siguen correspondientes al bloque 2. Se mantienen las verificaciones del snapshot histórico.

## Paso 3. Generar trazas de las cuatro dinámicas

En el menú, opción `7`. De forma predeterminada se ejecuta `L=16`, `T=1.5`, `J=1`, `H=-3`, `seed=1234`; se guarda un frame cada ocho eventos, con límites protectores. Si quieres variar parámetros, ejecuta directamente el nuevo PS1:

```powershell
& '.\powershell\04_generar_trazas.ps1' -L 16 -T 1.5 -J 1 -H (-3.0) -Stride 8
```

Para contrastar un campo débil, por ejemplo:

```powershell
& '.\powershell\04_generar_trazas.ps1' -L 16 -T 1.2 -J 1 -H (-0.75) -Stride 25 -MaxAttempts 2000000 -MaxEvents 100000
```

**Aviso:** en campo débil y baja T los escapes pueden requerir muchísimo tiempo. Si se alcanza un límite y no se llega a `M=0`, el registro sigue siendo correcto pero está censurado.

## Paso 4. Examinar los archivos

El programa crea una carpeta independiente `results/practica_cierre/<fecha>_trazas_b3_<id>/` que contiene:

```text
RESUMEN.md
MANIFEST_B3.json
SHA256_NUEVAS_SALIDAS.csv
logs/
standard_glauber/
standard_metropolis/
nfold_glauber/
nfold_metropolis/
```

En cada caso encontrarás `trayectoria_frames.csv`, `trayectoria_events.csv`, `resumen_trazado.csv`, `resumen_control.csv`, `resumen_original.csv`, `validacion_traza.json`.

El archivo de eventos describe **todos** los flips aceptados y su tiempo de espera. El de frames contiene el estado inicial, instantáneas cada K eventos, y el final. Los bits `0` y `1` representan `-1` y `+1` respectivamente.

## Paso 5. Revalidar después

En el menú opción `8` o ejecuta:

```powershell
& '.\powershell\05_validar_trazas.ps1'
```

Se verifica la última campaña B3, incluidos los hashes de archivos, la reconstrucción de eventos y la coincidencia con el motor histórico. También puedes pasar `-Directorio 'ruta/a/carpeta'` para un experimento anterior.

## ¿En qué se diferencia B3 de B4/B5?

**B3 entrega datos físicos reales de evolución.** No se han generado aún GIF, MP4, series temporales ni mapas de dominios. Esos productos derivarán de los CSV de B3 en los siguientes bloques. Los fotogramas no representan intervalos iguales de MCSS; los saltos de tiempo se deben incorporar en la visualización.

## Seguridad de datos

- No modifica `simulator/src/` ni `simulator/include/` originales: el código trazado vive en `simulator/tracing/`.
- No toca `results/snapshots/`, `simulator/results/` ni los productos oficiales P08.
- No escribe sobre archivos de trazas existentes.
- Los CSV de resumen incluyen `cpu_seconds`, pero **no se deben usar estos tiempos trazados para comparar rendimiento**.
- Si PowerShell falla por una dependencia, revisa `logs/` dentro de la carpeta de campaña; las pruebas de Windows deben hacerse en tu equipo.
