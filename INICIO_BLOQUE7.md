# Bloque 7: cierre de los tres resultados inconclusos

Añadido `scripts/practica_cierre/inconclusos_b7.py` para generar muestras adicionales de **los tres puntos exactos** del barrido térmico histórico, comprobar sus CSV y comparar la vida media con IC bootstrap del 95 %, con margen prefijado [0.95, 1.05]. No cambia `simulator/src/`, `release/`, el snapshot o los datos de Prompt 6.

**No equivale a forzar tres PASS:** si la nueva muestra es pequeña o el IC atraviesa el margen, el resultado será `INCONCLUSIVE`; si hay censura, `CENSURADO_NO_EVALUABLE`.

## Inicio Windows

```powershell
& '.\powershell\Ising_Practica_Master.ps1'
# O, para una campaña de precisión (coste computacional elevado):
& '.\powershell\12_inconclusos_b7.ps1' -Perfil practica
```

El menú ofrece opciones **15 (nuevas simulaciones)** y **16 (regenerar análisis)**. La documentación detallada está en `docs/BLOQUE7_INCONCLUSOS.md`.
