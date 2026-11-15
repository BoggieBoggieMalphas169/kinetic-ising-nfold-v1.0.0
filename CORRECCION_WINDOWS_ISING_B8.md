# Corrección de compatibilidad Windows para Ising B8

**Alcance:** corrige los dos fallos de B6 en Windows y la selección automática de NMake en el validador B1. El fallo `ModuleNotFoundError: imageio` no requiere modificar código: se resuelve instalando el conjunto de dependencias multimedia ya incluido en `requirements_animaciones.txt`.

## Diagnóstico confirmado

- `test_real_B5_output_and_multimedia_decoding_when_present`: falta `imageio` en el entorno virtual de Windows.
- `test_missing_pair_and_tamper_rejected` y `test_b6_integrated_campaign_is_complete_and_untampered`: `str(Path(...))` representa las rutas usando `\` en Windows, mientras que la comprobación exigía `datos_nuevos/`.
- La opción 2 del menú lanzaba CMake sin generador explícito, de modo que Windows elegía NMake aunque GCC estuviese disponible. El validador corregido detecta Ninja o MinGW Makefiles y usa una carpeta de compilación diferenciada por generador para evitar cachés anteriores incompatibles.

## Aplicación del parche en la carpeta de proyecto existente

**No borres la carpeta del proyecto ni sustituyas `.git`.** Abre PowerShell desde su raíz y haz copia de los dos archivos:

```powershell
Copy-Item '.\scripts\practica_cierre\barrido_campo_b6.py' '.\scripts\practica_cierre\barrido_campo_b6.py.bak'
Copy-Item '.\scripts\practica_cierre\validar_baseline.py' '.\scripts\practica_cierre\validar_baseline.py.bak'
```

Coloca `Ising_B8_Parche_Windows.zip` en la raíz del repositorio, o modifica la ruta al archivo de descarga, y ejecuta:

```powershell
Expand-Archive -LiteralPath '.\Ising_B8_Parche_Windows.zip' -DestinationPath '.' -Force
```

El ZIP del parche contiene solo los dos archivos Python corregidos con las mismas rutas relativas, además de este documento.

## Instalar dependencias multimedia en el entorno ya creado

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r '.\requirements_animaciones.txt'
```

`requirements.txt` original está congelado: no es necesario ni recomendable modificarlo.

## Validar

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' scripts/release_check.py --verify-frozen
& '.\.venv\Scripts\python.exe' -m scripts.analysis.build_quality_snapshot --verify results/snapshots/snap_0cc46433731097c4
```

Después, para que CMake utilice GCC/MinGW en Windows:

```powershell
$env:CMAKE_GENERATOR = 'MinGW Makefiles'
& '.\powershell\Ising_Practica_Master.ps1'
```

Selecciona **2** y, cuando esté todo validado, **17** para la auditoría final. Si `mingw32-make --version` no funciona pero sí `ninja --version`, establece `$env:CMAKE_GENERATOR = 'Ninja'`. El validador nuevo también intenta detectar automáticamente un generador disponible.

## Qué NO se altera

El código C, las reglas de Metropolis/Glauber, el algoritmo n-fold, los CSV históricos, el snapshot y los archivos protegidos de la release. La validación repetida en Linux del ZIP corregido dio **158/158 pruebas Python**, verificación de release **PASS** y snapshot **VERIFIED**. La prueba de ejecución PowerShell y CMake en Windows aún debe hacerse en la máquina del usuario.

## Localización precisa de los cambios

- `scripts/practica_cierre/barrido_campo_b6.py`: validación por componentes de ruta en `analyze_records`, y comprobación de la ruta real para impedir salir del directorio de campaña.
- `scripts/practica_cierre/validar_baseline.py`: selección de generador durante `run_validation` con detección de `ninja`/`mingw32-make` y preferencia de `CMAKE_GENERATOR` si está disponible.
