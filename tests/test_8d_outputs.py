from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_main_figures_exist_in_both_formats():
    base = ROOT / 'figures' / 'final'
    expected = [
        'fig01_equivalence_vs_temperature',
        'fig02_equivalence_vs_size',
        'fig03_speedup_vs_temperature',
        'fig04_event_compression_vs_temperature',
        'fig05_speedup_vs_size',
        'fig06_compression_vs_inverse_acceptance',
    ]
    for name in expected:
        assert (base / f'{name}.png').is_file()
        assert (base / f'{name}.pdf').is_file()


def test_supplementary_figures_exist():
    base = ROOT / 'figures' / 'supplementary'
    for name in ['figS01_campaign_consistency', 'figS02_dynamic_contrast_preservation']:
        assert (base / f'{name}.png').is_file()
        assert (base / f'{name}.pdf').is_file()


def test_final_tables_have_three_formats():
    base = ROOT / 'results' / 'final_tables'
    names = [
        'table01_headline_summary',
        'table02_physical_validation_by_dynamics',
        'table03_temperature_field_summary',
        'table04_size_robustness_summary',
        'table05_temperature_performance_summary',
        'table06_size_performance_summary',
        'tableS01_campaign_reproducibility',
    ]
    for name in names:
        for suffix in ['.csv', '.md', '.tex']:
            assert (base / f'{name}{suffix}').is_file()


def test_8d_manifest_is_complete_and_snapshot_locked():
    manifest = pd.read_csv(ROOT / 'results' / 'metadata' / 'final_artifacts_8D_manifest.csv')
    assert len(manifest) == 37
    assert manifest['artifact'].nunique() == 37
    assert set(manifest['analysis_snapshot']) == {'snap_0cc46433731097c4'}
    for rel in manifest['artifact']:
        assert (ROOT / rel).is_file()


def test_headline_table_preserves_core_results():
    table = pd.read_csv(ROOT / 'results' / 'final_tables' / 'table01_headline_summary.csv')
    values = dict(zip(table['Metric'], table['Value']))
    assert int(float(values['Campaign comparison records'])) == 52
    assert int(float(values['Unique physical points'])) == 44
    assert int(float(values['Physical-equivalence PASS'])) == 49
    assert int(float(values['Physical-equivalence INCONCLUSIVE'])) == 3
    assert int(float(values['Physical-equivalence FAIL'])) == 0
