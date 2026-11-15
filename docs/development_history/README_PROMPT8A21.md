# Prompt 8A.21 — Quality gate y snapshot reproducible

## Objetivo

Cerrar el bloque 8A con una frontera explícita antes de 8B. El quality gate comprueba
**integridad estructural y trazabilidad**, no decide el resultado científico de la comparación
Standard ↔ n-fold.

Por tanto, `PASS`, `INCONCLUSIVE` y un eventual `FAIL` de equivalencia son resultados que
8B debe interpretar. Un `INCONCLUSIVE` no bloquea este gate.

## Qué bloquea `READY_FOR_8B`

El gate exige que:

- existan todos los outputs canónicos de 8A.20;
- `master_comparisons.csv` use `master_schema_version = 8A20.1`;
- todas sus filas sean `record_level = comparison_summary`;
- `comparison_id` sea completo y único;
- todo registro tenga contexto físico completo y `experiment_id`;
- todo registro tenga `analysis_ready = true`;
- no haya duplicados ambiguos dentro de una campaña;
- los contratos históricos tengan `contract_status = complete`;
- el catálogo tenga IDs únicos y coincida exactamente con los IDs físicos del master;
- la cobertura de cada campaña declarada sea 100 %;
- no haya experimentos faltantes ni duplicados;
- por defecto no haya experimentos inesperados no declarados.

Los solapamientos entre campañas son válidos y solo se informan.

## Ejecución

Después de 8A.19 y 8A.20:

```powershell
python -m scripts.analysis.build_compatibility
python -m scripts.analysis.build_catalog
python -m scripts.analysis.build_quality_snapshot
```

El último comando escribe además:

```text
results/metadata/quality_gate_8A21.csv
results/metadata/scientific_status_8A21.csv
```

Si todos los checks bloqueantes pasan, imprime:

```text
QUALITY GATE: READY FOR 8B
```

## Snapshot

Un gate exitoso crea:

```text
results/snapshots/snap_<hash>/
├── manifest.json
├── quality_gate_report.csv
├── scientific_status_summary.csv
├── README.txt
└── data/
    └── results/
        ├── processed/...
        └── metadata/...
```

El `snapshot_id` se obtiene de SHA-256 de los bytes de los ficheros de entrada más la
versión del contrato 8A.21. Por ello, si los inputs son idénticos, el identificador también
lo es. `created_utc` no interviene en ese ID.

El snapshot incluye copias exactas de los datasets canónicos y sus hashes. Así 8B puede
citar una entrada inmutable, por ejemplo:

```text
analysis_snapshot = snap_0123456789abcdef
```

## Verificación

```powershell
python -m scripts.analysis.build_quality_snapshot `
  --verify results/snapshots/snap_0123456789abcdef
```

Si los bytes siguen siendo idénticos:

```text
SNAPSHOT VERIFIED
```

Si se altera un CSV después de congelarlo, la verificación falla.

## Experimentos inesperados

8A.20 conserva experimentos que no estén en `experiment_design.json`, pero 8A.21 los
bloquea por defecto para impedir que entren accidentalmente en 8B. Si se desea incluirlos
conscientemente:

```powershell
python -m scripts.analysis.build_quality_snapshot --allow-unexpected
```

La opción hace explícita esa decisión. Es preferible actualizar el diseño experimental
cuando esos puntos formen ya parte oficial del estudio.

## Frontera 8A → 8B

La cadena queda:

```text
8A.18  raw → processed
8A.19  contratos + compatibilidad histórica
8A.20  master dataset + catálogo + cobertura
8A.21  quality gate + snapshot SHA-256
                      ↓
                 READY FOR 8B
```

El snapshot congelado, y no una colección informal de CSV sueltos, debe ser la entrada
recomendada para las figuras, tablas y conclusiones de 8B.
