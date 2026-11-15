# Bloque 7 — Extensión estadística de los tres casos históricos inconclusos

## 1. Objetivo físico

Comparar la **distribución del tiempo de primer paso** desde todos los espines +1 hasta `M = 0` en el modelo Ising 2D periódico, con `L=32`, `J=1`, `H=-0.75`, y dos reglas separadas: Glauber y Metropolis. La hipótesis computacional es que **Standard aleatorio de un solo espín** y **n-fold exacto con reloj geométrico** representan la misma dinámica estocástica. El algoritmo no garantiza igual trayectoria para igual semilla.

## 2. Casos fijos

| Código | Dinámica | T/J | n histórico/algoritmo |
|---|---|---:|---:|
| glauber_0p8 | Glauber | 0.8 | 150 |
| glauber_0p9 | Glauber | 0.9 | 4000 |
| metropolis_0p8 | Metropolis | 0.8 | 150 |

El histórico Glauber T=0.9 consta de dos lotes (1000 y 3000) con semillas distintas; por eso la clave de identidad de repetición es `(seed, stream)`.

## 3. Diseño prospectivo

- Todos los parámetros físicos se mantienen fijos, tal como en el histórico. Se crean **nuevas semillas** para cada par (caso, algoritmo), independientes de las históricas.
- El diseño (réplicas, semilla, horizonte y número de réplicas bootstrap) se graba en `B7_DISENO_PREVIO.json` **antes** de ejecutar el primer simulador.
- **Piloto:** 30 nuevos runs por algoritmo para cada caso a 0.8, y 80 para Glauber a 0.9. Útil para probar la maquinaria, no para declarar equivalencia con potencia suficiente.
- **Práctica:** 3500 nuevos runs/algoritmo por caso a 0.8; 7000 runs/algoritmo a 0.9. Tiene coste de CPU alto y está pensada para mejorar precisión. No garantiza PASS.
- Todos los eventos físicos son exactamente los del motor histórico; la capa B7 es Python que llama a los ejecutables C sin editar el código fuente.
- Horizonte estándar B7: `100000000` intentos equivalentes (97656.25 MCSS a L=32). Si un n-fold supera el límite con un salto, se censura al horizonte. **Nunca** se interpreta el tiempo de una trayectoria censurada como vida completa.

## 4. Análisis y estados

Se calcula `R_tau = mean(tau_nfold) / mean(tau_standard)` y su intervalo percentil bootstrap no paramétrico al 95 %, re-muestreando repeticiones **por algoritmo**. Para declarar `PASS` se exige `CI entero ⊂ [0.95,1.05]`. Para declarar `FAIL` se requiere `CI entero fuera del margen por un lado`; en otro caso `INCONCLUSIVE`. Los puntos censurados dan `CENSURADO_NO_EVALUABLE` para razón de medias.

Se publican **tres análisis distintos** sin sustitución entre ellos: `HISTORICO` (recalculado desde raw originales), `SOLO_NUEVOS` (**primario** del seguimiento prospectivo) y `COMBINADO` (análisis secundario). Si los datos históricos contienen alguna dependencia cruzada asociada a semillas comunes entre motores, el bootstrap independiente podría no capturar esa covarianza; por eso se mantienen visibles el resultado nuevo y el combinado, sin intercambiarlos.

La prueba Kolmogorov–Smirnov de dos muestras complementa la comparación de medias. Se corrigen los tres valores p **de SOLO_NUEVOS** por Holm. No rechazar KS no prueba igualdad de distribuciones; rechazar KS merece replicación independiente y revisión de colas, no implica automáticamente un bug. Las figuras muestran supervivencia con **Kaplan–Meier**, que trata correctamente el censurado derecho, distribución de escapes observados en `log10(t/MCSS)` y diagnóstico de medias acumuladas (solo en ausencia de censura).

## 5. Flujo y salidas

```text
simulator/results/temperature_sweep/raw/ (solo lectura)
                  │
                  ▼
results/practica_cierre/<timestamp>_inconclusos_b7_<id>/
   B7_DISENO_PREVIO.json             ← protocolo pre-registrado
   build_b6/                         ← binarios C nuevos; ignorar al publicar
   datos_nuevos/                     ← 6 CSV originales nuevos
   B7_MANIFEST_DATOS.json            ← SHA-256 de nuevos e históricos
   B7_RESUMEN_COMPARACIONES.csv      ← R_tau e intervalos 3 × casos
   B7_INFORME.md                     ← lectura física y límites
   figuras_b7/                       ← PNG y PDF de 10 figuras
   MANIFEST_B6_SALIDAS.csv           ← hashes de las salidas derivadas
   B7_ESTADO.json                    ← estado de ejecución (PASS del pipeline)
   logs/                             ← comandos usados y consola C
```

**El estado `PASS` del pipeline NO es un PASS de equivalencia física**. Debe leerse el campo `status` de `B7_RESUMEN_COMPARACIONES.csv`.

## 6. Cómo ejecutar y regenerar (Windows PowerShell)

```powershell
# Desde la raíz del repositorio:
& '.\powershell\Ising_Practica_Master.ps1'    # opciones 15 y 16

# Piloto pequeño (no confirma equivalencia)
& '.\powershell\12_inconclusos_b7.ps1' -Perfil piloto

# Campaña de precisión; CPU puede ser muy costosa
& '.\powershell\12_inconclusos_b7.ps1' -Perfil practica

# Alternativa con número de muestras fijado por el estudiante antes de correr
& '.\powershell\12_inconclusos_b7.ps1' -Perfil practica -RunsFrio 800 -RunsTemplado 2000

# Regenerar gráficos sin repetir C ni sobrescribir CSV
& '.\powershell\13_analizar_inconclusos_b7.ps1' -DirectorioB7 'results/practica_cierre/<id_del_barrido_B7>'
```

Los scripts usan `common.ps1` para localizar Python. Las salidas siempre van a directorios nuevos. En Linux o macOS: `python -m scripts.practica_cierre.inconclusos_b7 generar --perfil piloto`.

## 7. Garantías, pruebas y límites

Se verifica antes/después el SHA-256 de los archivos protegidos y el snapshot, se valida la estructura y el tiempo de todos los CSV, se comprueban las semillas y los hashes históricos antes de combinar y se rechazan rutas manipuladas. No se modifica el código de Standard o n-fold, sus RNG, el reloj MCSS ni la release original. Las pruebas contienen además casos de censura, bootstrap reproducible, criterios de equivalencia y función Kaplan–Meier.

No se realiza ninguna parada opcional una vez que comienza una campaña: el criterio de éxito de simulación no depende de alcanzar estadísticamente un PASS. Para poder reproducir un estudio prospectivo debe archivarse también `B7_DISENO_PREVIO.json` y no sólo la figura final.

## 8. Próximo bloque

Bloque 8: auditoría y presentación de todos los resultados de B1–B7, comprobación final en Windows y memoria científica de entrega. Si una comparación B7 permanece inconclusa, se documenta su límite estadístico en lugar de alterar el margen o modificar parámetros físicos.
