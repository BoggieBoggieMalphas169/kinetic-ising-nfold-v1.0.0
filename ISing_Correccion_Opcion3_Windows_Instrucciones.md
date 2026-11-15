# Ising B8 — Corrección de reproducibilidad P08 en Windows

## Motivo

La opción 3 del menú maestro (`02_reproducir_historico.ps1`) compara 37 artefactos mediante SHA-256 de bytes. Esto es demasiado estricto cuando la regeneración ocurre en Windows: los CSV, MD y TEX pueden usar `CRLF`, mientras que los originales guardan `LF`; las figuras PNG pueden variar por el rasterizador/fuentes y los PDF por sus metadatos. En el registro del usuario aparecían **37 NO**: eso **no prueba** que cambiasen los resultados numéricos.

## Qué cambia

Un solo archivo: `scripts/practica_cierre/validar_baseline.py`. No modifica los motores de física, ningún CSV histórico ni la función original que genera tablas y figuras. La opción 2 y la auditoría siguen utilizando el mismo código de validación que ya funcionaba en Windows.

Al ejecutar la opción 3 ahora:

1. Se conserva la comparación SHA-256 original, archivo por archivo, en `comparacion_8D.csv` (campo `identico`). **No se finge identidad binaria**.
2. Se reconocen los cambios de finales de línea (LF/CRLF).
3. Las **7 tablas CSV** se comparan en estructura, filas, texto y números (diferencia relativa/absoluta máxima permitida 1e-12); un valor alterado provoca `failed`.
4. Las **8 imágenes PNG** se comparan píxel a píxel si son idénticas; para diferencias entre plataformas se calcula diferencia media de canales normalizada (umbral 0.025). Un cambio visual demasiado grande provoca `failed`. Es una prueba de semejanza visual, **no identidad científica punto a punto**; inspecciona siempre las figuras regeneradas.
5. Los PDF se contrastan a través de la figura PNG emparejada; la identidad del PDF en sí no se afirma si cambia el hash. Las variantes MD/TEX se etiquetan expresamente como diferencias de presentación cuando la representación no coincide.
6. Guarda **los 37 artefactos** en `results/practica_cierre/<nueva_ejecucion>_reproducir_8D.../artefactos_regenerados/` para la exposición.
7. Verifica nuevamente que los archivos de la release histórica no fueron modificados.

## Instrucciones en Windows

1. En la carpeta principal del repositorio, desde PowerShell, haz copia de seguridad:

```powershell
Copy-Item '.\scripts\practica_cierre\validar_baseline.py' '.\scripts\practica_cierre\validar_baseline.py.bak'
```

2. Copia este ZIP en la misma carpeta y extráelo sobre la raíz:

```powershell
Expand-Archive -Path '.\Ising_B8_Parche_Opcion3_Windows.zip' -DestinationPath '.' -Force
```

3. Abre de nuevo el menú y ejecuta la opción **3**:

```powershell
& '.\powershell\Ising_Practica_Master.ps1'
```

4. Abre `validation.json`, `comparacion_8D.csv` y la carpeta `artefactos_regenerados` en la última campaña `_reproducir_8D_...`. Si `status` es `passed`, revisa también `sha256_identical`, las notas y `comprobacion_portable` para distinguir igualdad exacta de compatibilidad. Si sigue siendo `failed`, consulta en el CSV las entradas `DATOS_DIFERENTES` o `VISUAL_DIFERENTE` y remite el informe para identificar el cambio concreto.

## Qué se ha probado

- En Linux, la opción 3 corregida ha terminado `passed`, guardando 37 artefactos y comparando 7 CSV y 8 PNG. Los 8 PDF tenían SHA-256 distinto; se refleja así, no se oculta.
- Las pruebas unitarias específicas detectan correctamente diferencias CRLF/LF, cambios en números de CSV y una imagen evidentemente adulterada.
- La suite completa del proyecto **158 passed** en el entorno de prueba, usando las campañas históricas incluidas.
- **No se ha validado aún el comportamiento en Windows del usuario**: la prueba final allí es repetir la opción 3.

El fichero `.bak` es solo tu copia local; el parche incluye únicamente el `.py` y este README. No es necesario repetir campañas físicas B6/B7.
