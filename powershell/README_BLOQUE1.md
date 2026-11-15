# Bloque 1 — Recuperacion y automatizacion inicial

**Base**: release integrada `kinetic-ising-nfold-v1.0.0` y snapshot `snap_0cc46433731097c4`.
Este bloque NO modifica el simulador C (Standard/n-fold), el RNG, las probabilidades de
transicion ni el reloj. Los PS1 se limitan a preparar dependencias y ejecutar el
programa `scripts/practica_cierre/validar_baseline.py`.

## En Windows / PowerShell

1. Descomprime el ZIP completo en una carpeta nueva. Conserva otra copia intacta del ZIP original.
2. Abre PowerShell en la carpeta del repositorio (o ejecuta el PS1 usando la ruta completa).
3. Prepara las dependencias **solo la primera vez**:

   ```powershell
   & '.\powershell\00_preparar_entorno.ps1'
   ```

4. Ejecuta los controles:

   ```powershell
   & '.\powershell\01_validar.ps1'
   ```

5. Reproduce las 6 figuras finales, 2 suplementarias y 7 tablas en copia temporal segura:

   ```powershell
   & '.\powershell\02_reproducir_historico.ps1'
   ```

6. Alternativamente usa el menu:

   ```powershell
   & '.\powershell\Ising_Practica_Master.ps1'
   ```

Si usas otra instalacion Python, agrega `-Python 'C:\ruta\a\python.exe'` a los PS1.
**Requisitos**: Python 3.10+ (incluidos pip y venv), CMake >=3.16, un compilador de C
(MinGW/GCC o MSVC con generador correcto). Para la reproduccion grafica hace falta
Matplotlib, pandas, NumPy, SciPy; `00_preparar_entorno.ps1` instala requirements.txt.

No se asume que `py` exista; si `python` no se reconoce, usa `-Python`.
El menu NO ofrece opciones de nivel 2 ni de animacion hasta que se implementen de verdad.

## Seguridad y resultados

- Cada ejecucion genera `results/practica_cierre/<id_unico>/` con `validation.json`,
  `RESUMEN.md` y logs individuales. No se reusa ni se sobrescribe una ejecucion anterior.
- Se usan `build/practica_b1/` y `.venv/` para salidas de compilacion y dependencias.
- `01_validar` verifica release, snapshot, CMake, CTest y pytest. Comprueba las huellas
  SHA-256 de **todos los archivos congelados** antes y despues.
- `02_reproducir_historico` copia la release a un directorio temporal externo, ejecuta
  `scripts.reproduce_8D` **solo alli**, compara 37 archivos producidos y guarda
  `comparacion_8D.csv`. Esta opcion no ejecuta simulaciones C.
- En una reproduccion identica de los datos y las imagenes PNG, los PDF pueden variar
  en bytes debido a metadatos de creacion. Si PyMuPDF esta instalado, el controlador
  compara adicionalmente la rasterizacion de sus paginas. Sin ese paquete opcional,
  el informe deja explicitamente la igualdad visual de los PDF sin verificar.
- Los archivos protegidos **no** se reescriben: `simulator/results/`, `results/snapshots/`,
  `results/legacy/prompt6/`, `figures/final/`, etc.
- El auditor usa el manifiesto historico; NO se recomienda pasar el antiguo comando de
  reproduccion `python -m scripts.reproduce_8D` sobre el repositorio de referencia porque
  puede modificar imagenes/manifest aunque el contenido fisico sea equivalente.

## Diagnostico

En un Windows con CMake multi-config, el verificador invoca `cmake --build ... --config Release`
y `ctest -C Release`. Si no existe compilador C, el log `cmake_configurar.log`
identifica el problema; instalar dependencias Python por si solo no lo resuelve.

Para ejecutar el motor desde otro sistema, sin PowerShell, basta con:

```bash
python scripts/practica_cierre/validar_baseline.py validar
python scripts/practica_cierre/validar_baseline.py reproducir
```

## Alcance y siguiente bloque

Este bloque congela la referencia y automatiza la reentrada. El siguiente bloque sera
**C2 (graficas del Nivel 2 a partir de CSV existentes)**. Mas adelante: observador C
pasivo de configuraciones, series M(t)/E(t) y GIF/MP4 de las cuatro combinaciones.
No se implementan todavia ni se anuncian como terminados.
