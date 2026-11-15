# Prompt 8D — Figuras y tablas finales

Este bloque transforma los resultados ya validados de 8B y 8C en artefactos listos para
memoria, presentación y GitHub. No introduce nuevas conclusiones físicas: todos los
artefactos proceden del snapshot `snap_0cc46433731097c4`.

## Figuras principales
1. `fig01_equivalence_vs_temperature` — equivalencia física frente a T/J.
2. `fig02_equivalence_vs_size` — equivalencia física frente a L.
3. `fig03_speedup_vs_temperature` — speed-up CPU frente a T/J.
4. `fig04_event_compression_vs_temperature` — compresión de rechazos.
5. `fig05_speedup_vs_size` — speed-up frente a L a T/J=1.5.
6. `fig06_compression_vs_inverse_acceptance` — comprobación C ≈ 1/a.

Cada figura se guarda en PNG (300 dpi) y PDF vectorial.

## Figuras suplementarias
- `figS01_campaign_consistency`
- `figS02_dynamic_contrast_preservation`

## Tablas
Las tablas se escriben en CSV, Markdown y LaTeX:
- `table01_headline_summary`
- `table02_physical_validation_by_dynamics`
- `table03_temperature_field_summary`
- `table04_size_robustness_summary`
- `table05_temperature_performance_summary`
- `table06_size_performance_summary`
- `tableS01_campaign_reproducibility`

## Reproducción
```powershell
python -m pip install -r requirements-analysis.txt
python -m scripts.reproduce_8D
```

## Selección mínima recomendada para una memoria
Si hay que reducir el número de figuras, conservar:
- Fig. 1 — equivalencia frente a temperatura.
- Fig. 2 — equivalencia frente a tamaño.
- Fig. 3 — speed-up frente a temperatura.
- Fig. 6 — mecanismo de compresión frente a 1/aceptación.

Las demás pueden ir como apoyo o material suplementario.
