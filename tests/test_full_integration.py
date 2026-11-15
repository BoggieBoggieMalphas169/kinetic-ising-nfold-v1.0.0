from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_simulator_source_tree_present():
    for rel in [
        "simulator/src/ising.c", "simulator/src/standard_mc.c", "simulator/src/nfold.c",
        "simulator/include/ising.h", "simulator/include/standard_mc.h", "simulator/include/nfold.h",
        "simulator/tests/test_physics.c", "simulator/tests/test_nfold.c",
        "simulator/CMakeLists.txt", "simulator/Makefile",
    ]:
        assert (ROOT / rel).is_file(), rel


def test_prompt6_raw_summaries_present():
    for rel in [
        "simulator/results/production_report_L32/validation_summary.csv",
        "simulator/results/scalability_L/scalability_summary.csv",
        "simulator/results/temperature_sweep/temperature_sweep_summary.csv",
    ]:
        assert (ROOT / rel).is_file(), rel


def test_release_metadata_marks_full_integration():
    meta = json.loads((ROOT / "release/release_metadata.json").read_text(encoding="utf-8"))
    assert meta["version"] == "1.0.0"
    assert meta["simulator_core_included"] is True
    assert meta["analysis_snapshot"] == "snap_0cc46433731097c4"


def test_top_level_build_wrappers_present():
    assert "add_subdirectory(simulator)" in (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "$(MAKE) -C simulator" in (ROOT / "Makefile").read_text(encoding="utf-8")

import pandas as pd
import numpy as np
import pytest

@pytest.mark.parametrize("source,compat", [
    ("simulator/results/production_report_L32/validation_summary.csv", "results/legacy/prompt6/validation_summary.csv"),
    ("simulator/results/scalability_L/scalability_summary.csv", "results/legacy/prompt6/scalability_summary.csv"),
    ("simulator/results/temperature_sweep/temperature_sweep_summary.csv", "results/legacy/prompt6/temperature_sweep_summary.csv"),
])
def test_prompt6_source_summaries_match_prompt8_compatibility_copies(source, compat):
    a = pd.read_csv(ROOT / source)
    b = pd.read_csv(ROOT / compat)
    common = [c for c in a.columns if c in b.columns]
    assert len(a) == len(b)
    assert set(a.columns).issubset(set(b.columns))
    for c in common:
        if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
            assert np.allclose(a[c], b[c], rtol=1e-12, atol=1e-15, equal_nan=True), c
        else:
            assert a[c].fillna("").astype(str).equals(b[c].fillna("").astype(str)), c
