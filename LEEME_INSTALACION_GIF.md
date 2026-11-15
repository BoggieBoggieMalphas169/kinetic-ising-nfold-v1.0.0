# Complemento GIF para kinetic-ising-nfold v1.0.0

Este paquete contiene UNICAMENTE el modulo de animacion. No incluye el nucleo ni los resultados originales.

1. Descomprime su contenido en la RAIZ del repositorio v1.0.0, respetando las carpetas `simulator/src`, `scripts` y `docs`.
2. Abre el archivo existente `simulator/CMakeLists.txt` y, despues de los ejecutables `ising_standard` y `ising_nfold`, anade estas dos lineas (solo una vez):

```cmake
add_executable(ising_animation_trace src/main_animation_trace.c)
target_link_libraries(ising_animation_trace PRIVATE ising_core)
```

3. En PowerShell, desde la raiz del repositorio:

```powershell
python -m pip install -r requirements-animation.txt
.\run_animaciones.ps1
```

Personalizar:

```powershell
.\run_animaciones.ps1 -L 32 -T 1.6 -H (-1.0) -MCSS 13 -Frames 65 -Fps 9
```

Requiere CMake, compilador C y Python. Guarda cada ejecucion en `results/animations/` en una carpeta nueva. No edites otras partes del CMake ni reemplaces el archivo entero. Para mas detalles, lee `docs/ANIMACIONES_V1.md`.
