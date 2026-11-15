from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.analysis.aggregate_runs import aggregate_runs
from scripts.analysis.load_results import DataContractError, load_raw_results
from scripts.analysis.statistics import blocking_table, mean_ci


def test_standard_file_is_normalized(tmp_path: Path):
    raw = tmp_path / "results" / "raw" / "standard"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {
            "run": [0, 1],
            "L": [4, 4],
            "N": [16, 16],
            "T": [1.5, 1.5],
            "J": [1.0, 1.0],
            "H": [-3.0, -3.0],
            "dynamics": ["glauber", "glauber"],
            "seed": [10, 11],
            "stream": [0, 1],
            "attempts": [32, 48],
            "time_mcss": [2.0, 3.0],
            "accepted": [10, 12],
            "acceptance_rate": [10 / 32, 12 / 48],
            "final_M": [0, 0],
            "final_E": [-12.0, -10.0],
            "reached_M0": [1, 1],
        }
    ).to_csv(raw / "standard.csv", index=False)

    loaded = load_raw_results(tmp_path / "results" / "raw")
    assert set(loaded.runs["algorithm"]) == {"standard"}
    assert np.allclose(loaded.runs["equivalent_attempts"], loaded.runs["attempts"])
    assert loaded.runs["reached_M0"].all()


def test_nfold_preserves_event_clock(tmp_path: Path):
    raw = tmp_path / "results" / "raw" / "nfold"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {
            "run": [0, 1],
            "L": [4, 4],
            "T": [1.5, 1.5],
            "J": [1.0, 1.0],
            "H": [-0.75, -0.75],
            "dynamics": ["glauber", "glauber"],
            "time_mcss": [20.0, 22.0],
            "events": [30, 35],
            "equiv_attempts": [320.0, 352.0],
            "final_M": [0, 0],
            "reached_M0": [True, True],
        }
    ).to_csv(raw / "nfold.csv", index=False)

    loaded = load_raw_results(tmp_path / "results" / "raw")
    row = loaded.runs.iloc[0]
    assert row["algorithm"] == "nfold"
    assert row["N"] == 16
    assert row["events"] == 30
    assert row["equivalent_attempts"] == 320
    assert pd.isna(row["attempts"])


def test_aggregate_lifetime(tmp_path: Path):
    raw = tmp_path / "raw" / "standard"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {
            "L": [4, 4, 4],
            "N": [16, 16, 16],
            "T": [1.5] * 3,
            "J": [1.0] * 3,
            "H": [-3.0] * 3,
            "dynamics": ["glauber"] * 3,
            "time_mcss": [1.0, 2.0, 3.0],
            "attempts": [16, 32, 48],
        }
    ).to_csv(raw / "runs.csv", index=False)
    loaded = load_raw_results(tmp_path / "raw")
    summary = aggregate_runs(loaded.runs)
    assert len(summary) == 1
    assert summary.loc[0, "runs"] == 3
    assert summary.loc[0, "mean_tau_mcss"] == pytest.approx(2.0)
    assert summary.loc[0, "mean_equiv_attempts"] == pytest.approx(32.0)


def test_bad_lattice_is_rejected(tmp_path: Path):
    raw = tmp_path / "raw" / "standard"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {"L": [4], "N": [15], "T": [1.5], "J": [1.0], "H": [-3.0], "time_mcss": [1.0], "attempts": [16]}
    ).to_csv(raw / "bad.csv", index=False)
    with pytest.raises(DataContractError, match=r"N != L\^2"):
        load_raw_results(tmp_path / "raw")


def test_statistics_helpers():
    stats = mean_ci([1, 2, 3, 4])
    assert stats["n"] == 4
    assert stats["mean"] == pytest.approx(2.5)
    table = blocking_table(np.arange(64, dtype=float), min_blocks=8)
    assert list(table["block_size"]) == [1, 2, 4, 8]

from scripts.analysis.prompt6_compat import (
    detect_prompt6_study,
    load_prompt6_summaries,
    normalize_prompt6_summary,
)


def _validation_row():
    return pd.DataFrame(
        {
            "dynamics": ["glauber"],
            "H": [-3.0],
            "n_standard": [1000],
            "n_nfold": [1000],
            "mean_standard_mcss": [1.4458],
            "mean_standard_ci95_lo": [1.4419],
            "mean_standard_ci95_hi": [1.4496],
            "median_standard_mcss": [1.4463],
            "sd_standard_mcss": [0.0616],
            "mean_nfold_mcss": [1.4422],
            "mean_nfold_ci95_lo": [1.4383],
            "mean_nfold_ci95_hi": [1.4460],
            "median_nfold_mcss": [1.4404],
            "sd_nfold_mcss": [0.0624],
            "ratio_nfold_standard": [0.9975],
            "ratio_bootstrap_ci95_lo": [0.9938],
            "ratio_bootstrap_ci95_hi": [1.0012],
            "ks_D": [0.043],
            "ks_p": [0.307],
            "equivalence_margin": [0.05],
            "equivalence_pass": [True],
            "mean_standard_attempts": [1480.5],
            "mean_nfold_equiv_attempts": [1476.8],
            "mean_nfold_events": [605.6],
            "nfold_weighted_mean_wait": [2.4384],
            "mean_per_run_cpu_ratio_std_over_nfold": [0.4879],
        }
    )


def test_prompt6_validation_uses_explicit_context():
    df = _validation_row()
    normalized, report = normalize_prompt6_summary(
        df,
        "validation_summary.csv",
        {"L": 32, "T": 1.5, "J": 1.0},
    )
    row = normalized.iloc[0]
    assert detect_prompt6_study(df) == "validation"
    assert row["record_level"] == "comparison_summary"
    assert row["L"] == 32
    assert row["N"] == 1024
    assert row["T"] == pytest.approx(1.5)
    assert row["invT"] == pytest.approx(2 / 3)
    assert row["mean_tau_standard_mcss"] == pytest.approx(1.4458)
    assert row["equivalence_status"] == "PASS"
    assert row["nfold_equiv_attempts_per_event"] == pytest.approx(2.4384)
    assert report["contract_status"] == "complete"
    assert set(report["context_fields_applied"].split(";")) == {"J", "L", "T"}


def test_prompt6_validation_without_context_is_partial_not_fabricated():
    normalized, report = normalize_prompt6_summary(_validation_row(), "validation_summary.csv")
    row = normalized.iloc[0]
    assert pd.isna(row["L"])
    assert pd.isna(row["T"])
    assert pd.isna(row["J"])
    assert row["contract_status"] == "partial"
    assert report["contract_status"] == "partial"


def test_prompt6_scalability_contract():
    df = pd.DataFrame(
        {
            "dynamics": ["glauber"],
            "H": [-0.75],
            "L": [32],
            "N": [1024],
            "T": [1.5],
            "J": [1.0],
            "runs": [1000],
            "mean_tau_standard_mcss": [24.579],
            "mean_tau_nfold_mcss": [24.559],
            "lifetime_ratio_nfold_standard": [0.99917],
            "ratio_bootstrap_ci95_lo": [0.9881],
            "ratio_bootstrap_ci95_hi": [1.0107],
            "equivalence_margin": [0.05],
            "equivalence_pass": [1],
            "cpu_standard_s_per_escape": [0.000503699],
            "cpu_nfold_s_per_escape": [0.000262033],
            "speedup_standard_over_nfold": [1.92227],
            "mean_standard_attempts_per_escape": [25168.859],
            "mean_nfold_equiv_attempts_per_escape": [25148.035],
            "mean_nfold_events_per_escape": [1961.81],
            "nfold_equiv_attempts_per_event": [12.8188],
            "standard_cpu_ns_per_attempt": [20.01],
            "nfold_cpu_ns_per_event": [133.57],
        }
    )
    normalized, report = normalize_prompt6_summary(df, "scalability_summary.csv")
    row = normalized.iloc[0]
    assert detect_prompt6_study(df) == "scalability_L"
    assert row["invT"] == pytest.approx(2 / 3)
    assert row["speedup_standard_over_nfold"] == pytest.approx(1.92227)
    assert row["equivalence_status"] == "PASS"
    assert report["contract_status"] == "complete"


def test_prompt6_temperature_preserves_inconclusive_and_holm():
    df = pd.DataFrame(
        {
            "dynamics": ["glauber"],
            "H": [-0.75],
            "L": [32],
            "N": [1024],
            "T": [0.8],
            "invT": [1.25],
            "J": [1.0],
            "runs": [150],
            "mean_tau_standard_mcss": [4417.26],
            "mean_tau_nfold_mcss": [3813.90],
            "lifetime_ratio_nfold_standard": [0.8634],
            "ratio_bootstrap_ci95_lo": [0.7027],
            "ratio_bootstrap_ci95_hi": [1.0534],
            "equivalence_margin": [0.05],
            "equivalence_pass": [0],
            "equivalence_status": ["INCONCLUSIVE"],
            "ratio_ci_contains_one": [1],
            "ks_statistic": [0.1733],
            "ks_pvalue": [0.0219],
            "cpu_standard_s_per_escape": [0.07424],
            "cpu_nfold_s_per_escape": [0.0004224],
            "speedup_standard_over_nfold": [175.77],
            "mean_standard_attempts_per_escape": [4523279.2],
            "mean_nfold_equiv_attempts_per_escape": [3905437.5],
            "mean_nfold_events_per_escape": [3661.15],
            "nfold_equiv_attempts_per_event": [1066.73],
            "standard_acceptance_fraction": [0.000909],
            "standard_cpu_ns_per_attempt": [16.41],
            "nfold_cpu_ns_per_event": [115.37],
            "ks_holm_reject_fwer_0p05": [0],
        }
    )
    normalized, report = normalize_prompt6_summary(df, "temperature_sweep_summary.csv")
    row = normalized.iloc[0]
    assert detect_prompt6_study(df) == "temperature_sweep"
    assert row["equivalence_status"] == "INCONCLUSIVE"
    assert bool(row["equivalence_pass"]) is False
    assert bool(row["ks_holm_reject_fwer_0p05"]) is False
    assert row["speedup_standard_over_nfold"] == pytest.approx(175.77)
    assert report["contract_status"] == "complete"


def test_prompt6_context_conflict_is_rejected():
    df = _validation_row()
    df["T"] = 1.5
    with pytest.raises(DataContractError, match="conflicts with stored T"):
        normalize_prompt6_summary(df, "validation_summary.csv", {"T": 2.0})


def test_prompt6_loader_builds_one_comparison_table(tmp_path: Path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _validation_row().to_csv(legacy / "validation_summary.csv", index=False)

    context = tmp_path / "context.json"
    context.write_text(
        '{"schema_version":"8A19-context-v1","files":{"validation_summary.csv":{"L":32,"T":1.5,"J":1.0}}}',
        encoding="utf-8",
    )
    loaded = load_prompt6_summaries(legacy, context)
    assert len(loaded.comparisons) == 1
    assert loaded.comparisons.loc[0, "schema_version"] == "8A19.1"
    assert loaded.report.loc[0, "contract_status"] == "complete"

from scripts.analysis.master_catalog import (
    DESIGN_SCHEMA_VERSION,
    build_master_catalog,
    canonical_physical_key,
    expand_experiment_design,
    load_experiment_design,
)


def _comparison_row(
    study="validation",
    dynamics="glauber",
    L=32,
    T=1.5,
    J=1.0,
    H=-3.0,
    source_file="summary.csv",
    source_row=0,
):
    return {
        "schema_version": "8A19.1",
        "record_level": "comparison_summary",
        "source_schema": "test",
        "study": study,
        "source_file": source_file,
        "source_row": source_row,
        "dynamics": dynamics,
        "L": L,
        "N": L * L,
        "T": T,
        "invT": 1.0 / T,
        "J": J,
        "H": H,
        "mean_tau_standard_mcss": 10.0,
        "mean_tau_nfold_mcss": 10.1,
        "lifetime_ratio_nfold_standard": 1.01,
        "equivalence_status": "PASS",
        "contract_status": "complete",
    }


def _mini_design(h_values=(-3.0, -0.75)):
    return {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "studies": {
            "validation": {
                "parameters": {
                    "dynamics": ["glauber"],
                    "L": [32],
                    "T": [1.5],
                    "J": [1.0],
                    "H": list(h_values),
                }
            }
        },
    }


def test_master_ids_are_deterministic_under_row_reordering():
    rows = [
        _comparison_row(H=-3.0, source_row=0),
        _comparison_row(H=-0.75, source_row=1),
    ]
    a = build_master_catalog(pd.DataFrame(rows)).master_comparisons
    b = build_master_catalog(pd.DataFrame(list(reversed(rows)))).master_comparisons
    map_a = dict(zip(a["physical_key"], a["experiment_id"]))
    map_b = dict(zip(b["physical_key"], b["experiment_id"]))
    assert map_a == map_b


def test_cross_study_overlap_is_not_a_duplicate():
    rows = [
        _comparison_row(study="validation", source_file="v.csv", source_row=0),
        _comparison_row(study="scalability_L", source_file="s.csv", source_row=0),
    ]
    built = build_master_catalog(pd.DataFrame(rows))
    master = built.master_comparisons
    assert len(built.experiment_catalog) == 1
    assert master["cross_study_overlap"].all()
    assert not master["duplicate_within_study"].any()
    assert master["analysis_ready"].all()
    assert built.experiment_catalog.loc[0, "study_count"] == 2


def test_duplicate_within_study_is_flagged_and_not_analysis_ready():
    rows = [
        _comparison_row(source_file="a.csv", source_row=0),
        _comparison_row(source_file="b.csv", source_row=0),
    ]
    built = build_master_catalog(pd.DataFrame(rows))
    master = built.master_comparisons
    assert master["duplicate_within_study"].all()
    assert not master["analysis_ready"].any()
    assert set(master["catalog_status"]) == {"duplicate_within_study"}


def test_design_detects_missing_and_unexpected_points():
    rows = [
        _comparison_row(H=-3.0, source_row=0),
        _comparison_row(H=-1.0, source_row=1),  # not in the declared design
    ]
    built = build_master_catalog(pd.DataFrame(rows), _mini_design())
    assert len(built.missing_experiments) == 1
    assert built.missing_experiments.iloc[0]["H"] == pytest.approx(-0.75)
    assert len(built.unexpected_experiments) == 1
    assert built.unexpected_experiments.iloc[0]["H"] == pytest.approx(-1.0)
    summary = built.coverage_summary.iloc[0]
    assert summary["expected_points"] == 2
    assert summary["observed_expected_points"] == 1
    assert summary["missing_points"] == 1
    assert summary["unexpected_points"] == 1
    assert summary["coverage_fraction"] == pytest.approx(0.5)


def test_partial_context_is_preserved_but_has_no_experiment_id():
    row = _comparison_row()
    row["T"] = pd.NA
    row["N"] = pd.NA
    built = build_master_catalog(pd.DataFrame([row]))
    master_row = built.master_comparisons.iloc[0]
    assert master_row["catalog_status"] == "partial_context"
    assert pd.isna(master_row["experiment_id"])
    assert not bool(master_row["analysis_ready"])
    assert built.experiment_catalog.empty


def test_prompt6_declared_design_has_52_campaign_records_and_44_unique_points():
    design_path = Path(__file__).parents[1] / "results" / "metadata" / "experiment_design.json"
    design = load_experiment_design(design_path)
    expected = expand_experiment_design(design)
    assert len(expected) == 52

    rows = []
    for i, r in expected.iterrows():
        rows.append(
            _comparison_row(
                study=r["study"],
                dynamics=r["dynamics"],
                L=int(r["L"]),
                T=float(r["T"]),
                J=float(r["J"]),
                H=float(r["H"]),
                source_file=f"{r['study']}.csv",
                source_row=int(i),
            )
        )
    built = build_master_catalog(pd.DataFrame(rows), design)
    assert len(built.master_comparisons) == 52
    assert len(built.experiment_catalog) == 44
    assert built.missing_experiments.empty
    assert built.duplicate_experiments.empty
    assert built.unexpected_experiments.empty
    assert (built.coverage_summary["coverage_fraction"] == 1.0).all()
    # Four physical points (2 dynamics x 2 fields at L=32,T=1.5) occur in all 3 campaigns.
    triple = built.experiment_catalog[built.experiment_catalog["study_count"] == 3]
    assert len(triple) == 4


def test_design_rejects_duplicate_expected_points():
    design = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "studies": {
            "x": {
                "points": [
                    {"dynamics": "glauber", "L": 8, "T": 1.5, "J": 1.0, "H": -3.0},
                    {"dynamics": "glauber", "L": 8, "T": 1.5, "J": 1.0, "H": -3.0},
                ]
            }
        },
    }
    with pytest.raises(DataContractError, match="duplicate expected points"):
        expand_experiment_design(design)

from scripts.analysis.quality_gate import (
    create_snapshot,
    run_quality_gate,
    verify_snapshot,
)


def _write_gate_fixture(root: Path, *, status="PASS", make_missing=False, unexpected=False):
    processed = root / "results" / "processed"
    metadata = root / "results" / "metadata"
    processed.mkdir(parents=True)
    metadata.mkdir(parents=True)

    master = pd.DataFrame([
        {
            **_comparison_row(),
            "master_schema_version": "8A20.1",
            "comparison_id": "cmp_test",
            "experiment_id": "exp_test",
            "physical_key": "dynamics=glauber|L=32|N=1024|T=1.5|J=1|H=-3",
            "physical_context_complete": True,
            "catalog_status": "observed",
            "design_status": "expected",
            "analysis_ready": True,
            "duplicate_within_study": False,
            "cross_study_overlap": False,
            "within_study_count": 1,
            "cross_study_count": 1,
            "equivalence_status": status,
            "contract_status": "complete",
        }
    ])
    master.to_csv(processed / "master_comparisons.csv", index=False)
    pd.DataFrame([
        {
            "master_schema_version": "8A20.1",
            "experiment_id": "exp_test",
            "physical_key": master.loc[0, "physical_key"],
            "dynamics": "glauber",
            "L": 32,
            "N": 1024,
            "T": 1.5,
            "J": 1.0,
            "H": -3.0,
            "comparison_records": 1,
            "study_count": 1,
            "studies": "validation",
            "source_files": "summary.csv",
            "cross_study_overlap": False,
            "duplicate_within_study_any": False,
            "analysis_ready_records": 1,
        }
    ]).to_csv(processed / "master_experiment_catalog.csv", index=False)
    pd.DataFrame([
        {
            "study": "validation",
            "expected_points": 1,
            "observed_expected_points": 0 if make_missing else 1,
            "missing_points": 1 if make_missing else 0,
            "duplicate_expected_points": 0,
            "unexpected_points": 1 if unexpected else 0,
            "coverage_fraction": 0.0 if make_missing else 1.0,
        }
    ]).to_csv(metadata / "experiment_coverage_summary.csv", index=False)
    cols = ["study", "experiment_id", "physical_key", "dynamics", "L", "N", "T", "J", "H", "observed_records", "coverage_status"]
    missing_df = pd.DataFrame(columns=cols)
    if make_missing:
        missing_df = pd.DataFrame([["validation", "exp_m", "k", "glauber", 16, 256, 1.5, 1.0, -3.0, 0, "missing"]], columns=cols)
    missing_df.to_csv(metadata / "missing_experiments.csv", index=False)
    pd.DataFrame(columns=cols).to_csv(metadata / "duplicate_experiments.csv", index=False)
    unexpected_df = pd.DataFrame(columns=cols)
    if unexpected:
        unexpected_df = pd.DataFrame([["validation", "exp_u", "u", "glauber", 64, 4096, 1.5, 1.0, -3.0, 1, "unexpected"]], columns=cols)
    unexpected_df.to_csv(metadata / "unexpected_experiments.csv", index=False)
    (metadata / "experiment_design.json").write_text(
        '{"schema_version":"8A20-design-v1","studies":{"validation":{"parameters":{"dynamics":["glauber"],"L":[32],"T":[1.5],"J":[1.0],"H":[-3.0]}}}}',
        encoding="utf-8",
    )


def test_quality_gate_ready_and_inconclusive_does_not_block(tmp_path: Path):
    _write_gate_fixture(tmp_path, status="INCONCLUSIVE")
    gate = run_quality_gate(tmp_path)
    assert gate.ready_for_8b
    scientific = dict(zip(gate.scientific_status["equivalence_status"], gate.scientific_status["count"]))
    assert scientific["INCONCLUSIVE"] == 1


def test_quality_gate_blocks_missing_design_point(tmp_path: Path):
    _write_gate_fixture(tmp_path, make_missing=True)
    gate = run_quality_gate(tmp_path)
    assert not gate.ready_for_8b
    failed = set(gate.checks.loc[(gate.checks["severity"] == "BLOCKER") & (~gate.checks["passed"]), "check_id"])
    assert "declared_design_full_coverage" in failed
    assert "no_missing_experiments" in failed


def test_quality_gate_unexpected_requires_explicit_opt_in(tmp_path: Path):
    _write_gate_fixture(tmp_path, unexpected=True)
    assert not run_quality_gate(tmp_path).ready_for_8b
    assert run_quality_gate(tmp_path, allow_unexpected=True).ready_for_8b


def test_snapshot_id_is_deterministic_and_verifiable(tmp_path: Path):
    _write_gate_fixture(tmp_path, status="PASS")
    a = create_snapshot(tmp_path)
    b = create_snapshot(tmp_path)
    assert a.snapshot_id == b.snapshot_id
    ok, report = verify_snapshot(a.path)
    assert ok
    assert report["match"].all()


def test_snapshot_verification_detects_tampering(tmp_path: Path):
    _write_gate_fixture(tmp_path)
    snapshot = create_snapshot(tmp_path)
    copied = snapshot.path / "data" / "results" / "processed" / "master_comparisons.csv"
    copied.write_text(copied.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    ok, report = verify_snapshot(snapshot.path)
    assert not ok
    assert not report.loc[report["path"] == "results/processed/master_comparisons.csv", "match"].iloc[0]

from scripts.analysis.physical_equivalence import (
    analyze_physical_equivalence,
    prepare_physical_equivalence,
)


def _physical_equivalence_fixture(status="PASS", ratio=1.01, lo=0.99, hi=1.03, ks_holm=0):
    row = {
        "comparison_id": "cmp_1",
        "experiment_id": "exp_1",
        "study": "temperature_sweep",
        "dynamics": "glauber",
        "L": 32,
        "N": 1024,
        "T": 1.5,
        "J": 1.0,
        "H": -0.75,
        "mean_tau_standard_mcss": 24.0,
        "mean_tau_nfold_mcss": 24.0 * ratio,
        "lifetime_ratio_nfold_standard": ratio,
        "ratio_ci95_lo": lo,
        "ratio_ci95_hi": hi,
        "equivalence_margin": 0.05,
        "equivalence_pass": status == "PASS",
        "equivalence_status": status,
        "ks_statistic": 0.03,
        "ks_pvalue": 0.6,
        "ks_holm_reject_fwer_0p05": ks_holm,
    }
    return pd.DataFrame([row])


def test_8b1_effect_size_and_equivalence_band():
    out = prepare_physical_equivalence(_physical_equivalence_fixture(), snapshot_id="snap_test")
    row = out.iloc[0]
    assert row["analysis_snapshot"] == "snap_test"
    assert row["relative_difference_pct"] == pytest.approx(1.0)
    assert row["equivalence_band_lo"] == pytest.approx(0.95)
    assert row["equivalence_band_hi"] == pytest.approx(1.05)
    assert row["ratio_ci_band_relation"] == "INSIDE_EQUIVALENCE_BAND"
    assert row["equivalence_status_8b"] == "PASS"
    assert row["combined_evidence"] == "SUPPORTED_WITHIN_TESTED_METRICS"


def test_8b1_exact_equality_not_required_for_practical_equivalence():
    # CI does not contain 1, but lies completely inside the predeclared ±5% band.
    df = _physical_equivalence_fixture(status="PASS", ratio=0.975, lo=0.960, hi=0.990)
    row = prepare_physical_equivalence(df).iloc[0]
    assert not bool(row["ratio_ci_contains_one_8b"])
    assert row["ratio_ci_band_relation"] == "INSIDE_EQUIVALENCE_BAND"
    assert row["equivalence_status_8b"] == "PASS"


def test_8b1_inconclusive_is_preserved():
    df = _physical_equivalence_fixture(status="INCONCLUSIVE", ratio=0.86, lo=0.70, hi=1.06)
    row = prepare_physical_equivalence(df).iloc[0]
    assert row["equivalence_status_8b"] == "INCONCLUSIVE"
    assert row["combined_evidence"] == "INCONCLUSIVE_PRECISION"
    assert row["ratio_ci_band_relation"] == "OVERLAPS_EQUIVALENCE_BOUNDARY"


def test_8b1_ks_rejection_is_mixed_evidence_not_rewritten_mean_result():
    df = _physical_equivalence_fixture(status="PASS", ks_holm=1)
    row = prepare_physical_equivalence(df).iloc[0]
    assert row["equivalence_status_8b"] == "PASS"
    assert row["combined_evidence"] == "MIXED_MEAN_EQUIVALENT_BUT_DISTRIBUTION_REJECTED"


def test_8b1_invalid_lattice_is_rejected():
    df = _physical_equivalence_fixture()
    df.loc[0, "N"] = 1000
    with pytest.raises(DataContractError, match="invalid physical context"):
        prepare_physical_equivalence(df)


def test_8b1_summary_does_not_pool_distinct_regimes():
    a = _physical_equivalence_fixture(status="PASS")
    b = _physical_equivalence_fixture(status="INCONCLUSIVE", ratio=0.86, lo=0.70, hi=1.06)
    b.loc[0, "comparison_id"] = "cmp_2"
    b.loc[0, "experiment_id"] = "exp_2"
    b.loc[0, "H"] = -3.0
    out = analyze_physical_equivalence(pd.concat([a, b], ignore_index=True), snapshot_id="snap_x")
    assert len(out.summary) == 2
    assert out.diagnostics.set_index("diagnostic").loc["comparison_records", "value"] == 2

from scripts.analysis.campaign_consistency import analyze_campaign_consistency


def _campaign_record(study, *, ratio=1.0, lo=0.98, hi=1.02, status="PASS", std_tau=10.0, nf_tau=10.0,
                     experiment_id="exp_repeat", dynamics="glauber", H=-3.0):
    return {
        "analysis_snapshot": "snap_test",
        "comparison_id": f"cmp_{study}",
        "experiment_id": experiment_id,
        "study": study,
        "dynamics": dynamics,
        "L": 32,
        "N": 1024,
        "T": 1.5,
        "J": 1.0,
        "H": H,
        "mean_tau_standard_mcss": std_tau,
        "mean_tau_nfold_mcss": nf_tau,
        "lifetime_ratio_nfold_standard": ratio,
        "ratio_ci95_lo": lo,
        "ratio_ci95_hi": hi,
        "equivalence_status_8b": status,
    }


def test_8b2_consistent_three_campaign_overlap():
    df = pd.DataFrame([
        _campaign_record("validation", ratio=0.998, lo=0.990, hi=1.006, std_tau=10.0, nf_tau=9.98),
        _campaign_record("scalability_L", ratio=1.001, lo=0.994, hi=1.008, std_tau=10.04, nf_tau=10.05),
        _campaign_record("temperature_sweep", ratio=0.999, lo=0.992, hi=1.005, std_tau=9.97, nf_tau=9.96),
    ])
    out = analyze_campaign_consistency(df)
    assert len(out.point_summary) == 1
    row = out.point_summary.iloc[0]
    assert row["campaign_count"] == 3
    assert bool(row["common_ratio_ci_nonempty"])
    assert bool(row["common_ratio_ci_contains_one"])
    assert bool(row["all_pairwise_ratio_ci_overlap"])
    assert row["campaign_consistency_status"] == "CONSISTENT_ACROSS_CAMPAIGNS"
    assert bool(row["campaign_reproducible"])
    assert len(out.pairwise) == 3


def test_8b2_all_pass_but_disjoint_intervals_are_flagged():
    df = pd.DataFrame([
        _campaign_record("validation", ratio=0.960, lo=0.951, hi=0.969),
        _campaign_record("scalability_L", ratio=1.040, lo=1.031, hi=1.049),
    ])
    out = analyze_campaign_consistency(df)
    row = out.point_summary.iloc[0]
    assert not bool(row["common_ratio_ci_nonempty"])
    assert row["campaign_consistency_status"] == "PASS_BUT_NO_COMMON_RATIO_CI_INTERSECTION"
    assert not bool(row["campaign_reproducible"])


def test_8b2_inconclusive_campaign_is_not_rewritten_to_consistent():
    df = pd.DataFrame([
        _campaign_record("validation", status="PASS"),
        _campaign_record("temperature_sweep", status="INCONCLUSIVE", ratio=0.98, lo=0.93, hi=1.03),
    ])
    row = analyze_campaign_consistency(df).point_summary.iloc[0]
    assert row["campaign_consistency_status"] == "MIXED_OR_INCONCLUSIVE_ACROSS_CAMPAIGNS"
    assert not bool(row["campaign_reproducible"])


def test_8b2_rejects_duplicate_same_campaign_for_same_physical_point():
    a = _campaign_record("validation")
    b = _campaign_record("validation", ratio=1.01)
    b["comparison_id"] = "cmp_validation_2"
    c = _campaign_record("temperature_sweep")
    with pytest.raises(DataContractError, match="duplicate records within the same campaign"):
        analyze_campaign_consistency(pd.DataFrame([a, b, c]))


def test_8b2_requires_single_snapshot():
    a = _campaign_record("validation")
    b = _campaign_record("temperature_sweep")
    b["analysis_snapshot"] = "snap_other"
    with pytest.raises(DataContractError, match="exactly one analysis_snapshot"):
        analyze_campaign_consistency(pd.DataFrame([a, b]))

from scripts.analysis.size_scaling_robustness import analyze_size_scaling


def _size_record(L, *, status="PASS", ratio=1.0, lo=0.98, hi=1.02,
                 relation="INSIDE_EQUIVALENCE_BAND", dynamics="glauber", H=-3.0,
                 T=1.5, J=1.0, snapshot="snap_test"):
    return {
        "analysis_snapshot": snapshot,
        "comparison_id": f"cmp_{dynamics}_{H}_{L}",
        "experiment_id": f"exp_{dynamics}_{H}_{L}",
        "study": "scalability_L",
        "dynamics": dynamics,
        "L": L,
        "N": L * L,
        "T": T,
        "J": J,
        "H": H,
        "mean_tau_standard_mcss": 10.0 + 0.01 * L,
        "mean_tau_nfold_mcss": (10.0 + 0.01 * L) * ratio,
        "lifetime_ratio_nfold_standard": ratio,
        "relative_difference_pct": 100.0 * (ratio - 1.0),
        "ratio_ci95_lo": lo,
        "ratio_ci95_hi": hi,
        "equivalence_band_lo": 0.95,
        "equivalence_band_hi": 1.05,
        "ratio_ci_contains_one_8b": lo <= 1.0 <= hi,
        "ratio_ci_band_relation": relation,
        "equivalence_status_8b": status,
    }


def test_8b3_all_sizes_pass_is_robust():
    df = pd.DataFrame([
        _size_record(8, ratio=1.01, lo=0.99, hi=1.03),
        _size_record(16, ratio=1.00, lo=0.99, hi=1.01),
        _size_record(32, ratio=0.998, lo=0.99, hi=1.006),
        _size_record(64, ratio=1.001, lo=0.995, hi=1.007),
    ])
    out = analyze_size_scaling(df)
    row = out.summary.iloc[0]
    assert row["size_robustness_status"] == "ROBUST_ACROSS_TESTED_L"
    assert bool(row["size_robust"])
    assert row["pass_count"] == 4
    assert row["L_values"] == "8;16;32;64"


def test_8b3_inconclusive_size_is_preserved():
    df = pd.DataFrame([
        _size_record(8),
        _size_record(16, status="INCONCLUSIVE", ratio=0.96, lo=0.93, hi=1.01,
                     relation="OVERLAPS_EQUIVALENCE_BOUNDARY"),
    ])
    row = analyze_size_scaling(df).summary.iloc[0]
    assert row["size_robustness_status"] == "INCONCLUSIVE_AT_SOME_L"
    assert not bool(row["size_robust"])


def test_8b3_fail_size_is_discrepancy():
    df = pd.DataFrame([
        _size_record(8),
        _size_record(16, status="FAIL", ratio=1.08, lo=1.06, hi=1.10,
                     relation="OUTSIDE_EQUIVALENCE_BAND"),
    ])
    row = analyze_size_scaling(df).summary.iloc[0]
    assert row["size_robustness_status"] == "DISCREPANCY_AT_SOME_L"


def test_8b3_duplicate_size_point_is_rejected():
    a = _size_record(16)
    b = _size_record(16, ratio=1.01)
    b["comparison_id"] = "cmp_duplicate"
    with pytest.raises(DataContractError, match="duplicate scalability records"):
        analyze_size_scaling(pd.DataFrame([a, b]))


def test_8b3_requires_single_snapshot():
    a = _size_record(8)
    b = _size_record(16, snapshot="snap_other")
    with pytest.raises(DataContractError, match="exactly one analysis_snapshot"):
        analyze_size_scaling(pd.DataFrame([a, b]))

from scripts.analysis.temperature_field_robustness import analyze_temperature_field


def _temp_record(T, *, status="PASS", ratio=1.0, lo=0.98, hi=1.02,
                 relation="INSIDE_EQUIVALENCE_BAND", dynamics="glauber", H=-3.0,
                 L=32, J=1.0, runs=1000, snapshot="snap_test"):
    return {
        "analysis_snapshot": snapshot,
        "comparison_id": f"cmp_{dynamics}_{H}_{T}",
        "experiment_id": f"exp_{dynamics}_{H}_{T}",
        "study": "temperature_sweep", "dynamics": dynamics,
        "L": L, "N": L*L, "T": T, "J": J, "H": H, "runs": runs,
        "mean_tau_standard_mcss": 10.0/T,
        "mean_tau_nfold_mcss": (10.0/T)*ratio,
        "lifetime_ratio_nfold_standard": ratio,
        "ratio_ci95_lo": lo, "ratio_ci95_hi": hi,
        "equivalence_band_lo": 0.95, "equivalence_band_hi": 1.05,
        "ratio_ci_band_relation": relation, "equivalence_status_8b": status,
    }


def test_8b4_all_temperatures_pass_is_robust():
    df = pd.DataFrame([_temp_record(0.8), _temp_record(1.0), _temp_record(1.5)])
    row = analyze_temperature_field(df).summary.iloc[0]
    assert row["temperature_robustness_status"] == "ROBUST_ACROSS_TESTED_T"
    assert row["pass_count"] == 3


def test_8b4_inconclusive_low_temperature_is_preserved():
    df = pd.DataFrame([
        _temp_record(0.8, status="INCONCLUSIVE", ratio=.86, lo=.70, hi=1.06,
                     relation="OVERLAPS_EQUIVALENCE_BOUNDARY", runs=150),
        _temp_record(1.0), _temp_record(1.5),
    ])
    row = analyze_temperature_field(df).summary.iloc[0]
    assert row["temperature_robustness_status"] == "INCONCLUSIVE_AT_SOME_T"
    assert row["inconclusive_T_values"] == "0.8"


def test_8b4_fail_temperature_is_discrepancy():
    df = pd.DataFrame([
        _temp_record(0.8),
        _temp_record(1.0, status="FAIL", ratio=1.08, lo=1.06, hi=1.10,
                     relation="OUTSIDE_EQUIVALENCE_BAND"),
    ])
    assert analyze_temperature_field(df).summary.iloc[0]["temperature_robustness_status"] == "DISCREPANCY_AT_SOME_T"


def test_8b4_duplicate_temperature_is_rejected():
    a=_temp_record(1.0); b=_temp_record(1.0); b["comparison_id"]="dup"
    with pytest.raises(DataContractError, match="duplicate temperature-sweep records"):
        analyze_temperature_field(pd.DataFrame([a,b]))


def test_8b4_requires_single_snapshot():
    a=_temp_record(1.0); b=_temp_record(1.5, snapshot="other")
    with pytest.raises(DataContractError, match="exactly one analysis_snapshot"):
        analyze_temperature_field(pd.DataFrame([a,b]))

from scripts.analysis.dynamics_comparison import analyze_dynamics


def _dyn_record(dynamics, *, study="temperature_sweep", L=32, T=1.5, H=-3.0,
                ratio=1.0, lo=0.98, hi=1.02, status="PASS",
                relation="INSIDE_EQUIVALENCE_BAND", snapshot="snap_test",
                tau_standard=None):
    if tau_standard is None:
        tau_standard = 12.0 if dynamics == "glauber" else 10.0
    return {
        "analysis_snapshot": snapshot,
        "comparison_id": f"cmp_{study}_{dynamics}_{L}_{T}_{H}",
        "experiment_id": f"exp_{study}_{dynamics}_{L}_{T}_{H}",
        "study": study,
        "dynamics": dynamics,
        "L": L, "N": L * L, "T": T, "J": 1.0, "H": H,
        "mean_tau_standard_mcss": tau_standard,
        "mean_tau_nfold_mcss": tau_standard * ratio,
        "lifetime_ratio_nfold_standard": ratio,
        "ratio_ci95_lo": lo, "ratio_ci95_hi": hi,
        "equivalence_band_lo": 0.95, "equivalence_band_hi": 1.05,
        "ratio_ci_band_relation": relation,
        "equivalence_status_8b": status,
    }


def test_8b5_summarizes_dynamics_separately():
    df = pd.DataFrame([
        _dyn_record("glauber", ratio=1.001),
        _dyn_record("metropolis", ratio=0.999),
    ])
    out = analyze_dynamics(df)
    assert set(out.dynamics_summary["dynamics"]) == {"glauber", "metropolis"}
    assert set(out.dynamics_summary["dynamics_equivalence_status"]) == {"ROBUST_IN_TESTED_DOMAIN"}
    assert len(out.matched_pairs) == 1


def test_8b5_inconclusive_is_preserved_as_precision_limit():
    df = pd.DataFrame([
        _dyn_record("glauber", status="INCONCLUSIVE", ratio=.90, lo=.80, hi=1.04,
                    relation="OVERLAPS_EQUIVALENCE_BOUNDARY"),
        _dyn_record("metropolis"),
    ])
    out = analyze_dynamics(df)
    g = out.dynamics_summary.set_index("dynamics").loc["glauber"]
    assert g["dynamics_equivalence_status"] == "NO_DISCREPANCY_WITH_PRECISION_LIMITS"
    assert g["inconclusive_count"] == 1


def test_8b5_fail_is_not_hidden():
    df = pd.DataFrame([
        _dyn_record("glauber", status="FAIL", ratio=1.09, lo=1.06, hi=1.12,
                    relation="OUTSIDE_EQUIVALENCE_BAND"),
        _dyn_record("metropolis"),
    ])
    out = analyze_dynamics(df)
    g = out.dynamics_summary.set_index("dynamics").loc["glauber"]
    assert g["dynamics_equivalence_status"] == "DISCREPANCY_DETECTED"
    assert out.matched_pairs.iloc[0]["matched_pair_status"] == "AT_LEAST_ONE_FAIL"


def test_8b5_dynamic_contrast_is_preserved_descriptively():
    df = pd.DataFrame([
        _dyn_record("glauber", tau_standard=12.0, ratio=1.01),
        _dyn_record("metropolis", tau_standard=10.0, ratio=1.00),
    ])
    pair = analyze_dynamics(df).matched_pairs.iloc[0]
    assert pair["tau_glauber_over_metropolis_standard"] == pytest.approx(1.2)
    assert pair["tau_glauber_over_metropolis_nfold"] == pytest.approx(1.212)
    assert pair["dynamic_contrast_preservation_ratio"] == pytest.approx(1.01)


def test_8b5_requires_matched_dynamics_at_each_campaign_point():
    df = pd.DataFrame([
        _dyn_record("glauber", T=1.0),
        _dyn_record("metropolis", T=1.0),
        _dyn_record("glauber", T=1.5),
    ])
    with pytest.raises(DataContractError, match="matched Glauber/Metropolis"):
        analyze_dynamics(df)


def test_8b5_requires_single_snapshot():
    df = pd.DataFrame([
        _dyn_record("glauber"),
        _dyn_record("metropolis", snapshot="snap_other"),
    ])
    with pytest.raises(DataContractError, match="exactly one analysis_snapshot"):
        analyze_dynamics(df)

from scripts.analysis.physical_synthesis import synthesize_physical_comparison


def _b6_minimal_tables(eq_status="PASS"):
    eq = pd.DataFrame([{
        "analysis_snapshot":"snap_test", "experiment_id":"exp1", "study":"temperature_sweep",
        "dynamics":"glauber", "H":-3.0, "T":1.0, "L":32,
        "lifetime_ratio_nfold_standard":1.0, "ratio_ci95_lo":0.98, "ratio_ci95_hi":1.02,
        "equivalence_status_8b":eq_status,
    }])
    camp = pd.DataFrame([{"analysis_snapshot":"snap_test", "campaign_reproducible":True,
                          "campaign_consistency_status":"CONSISTENT_ACROSS_CAMPAIGNS"}])
    size = pd.DataFrame([{"analysis_snapshot":"snap_test", "size_robust":True,
                          "size_robustness_status":"ROBUST_ACROSS_TESTED_L"}])
    temp = pd.DataFrame([{"analysis_snapshot":"snap_test", "dynamics":"glauber", "H":-3.0,
                          "pass_count":1 if eq_status=="PASS" else 0,
                          "inconclusive_count":1 if eq_status=="INCONCLUSIVE" else 0,
                          "fail_count":1 if eq_status=="FAIL" else 0,
                          "inconclusive_T_values":"1" if eq_status=="INCONCLUSIVE" else "",
                          "temperature_robustness_status":"ROBUST_ACROSS_TESTED_T"}])
    dyn = pd.DataFrame([{"analysis_snapshot":"snap_test", "dynamics":"glauber",
                         "pass_count":1 if eq_status=="PASS" else 0,
                         "inconclusive_count":1 if eq_status=="INCONCLUSIVE" else 0,
                         "fail_count":1 if eq_status=="FAIL" else 0,
                         "dynamics_equivalence_status":"ROBUST_IN_TESTED_DOMAIN"}])
    pairs = pd.DataFrame([{"analysis_snapshot":"snap_test",
                           "dynamic_contrast_preservation_abs_pct":0.5,
                           "matched_pair_status":"BOTH_PASS"}])
    return eq, camp, size, temp, dyn, pairs


def test_8b6_all_pass_is_supported_across_tested_domain():
    out = synthesize_physical_comparison(*_b6_minimal_tables("PASS"))
    assert out.synthesis.iloc[0]["overall_physical_conclusion"] == "SUPPORTED_ACROSS_TESTED_DOMAIN"
    assert out.synthesis.iloc[0]["performance_used_as_equivalence_evidence"] in (False, 0)


def test_8b6_inconclusive_is_preserved_as_precision_limit():
    out = synthesize_physical_comparison(*_b6_minimal_tables("INCONCLUSIVE"))
    assert out.synthesis.iloc[0]["overall_physical_conclusion"] == "SUPPORTED_WITH_PRECISION_LIMITS"
    assert out.limitations.iloc[0]["limitation_type"] == "STATISTICAL_PRECISION"


def test_8b6_fail_is_discrepancy():
    out = synthesize_physical_comparison(*_b6_minimal_tables("FAIL"))
    assert out.synthesis.iloc[0]["overall_physical_conclusion"] == "DISCREPANCY_DETECTED"


def test_8b6_snapshot_mixing_is_rejected():
    tabs = list(_b6_minimal_tables("PASS"))
    tabs[1] = tabs[1].copy(); tabs[1]["analysis_snapshot"] = "other"
    with pytest.raises(DataContractError, match="shared analysis_snapshot"):
        synthesize_physical_comparison(*tabs)


def test_8b6_campaign_and_size_flags_are_carried_forward():
    tabs = list(_b6_minimal_tables("PASS"))
    tabs[1] = tabs[1].copy(); tabs[1]["campaign_reproducible"] = False
    tabs[2] = tabs[2].copy(); tabs[2]["size_robust"] = False
    out = synthesize_physical_comparison(*tabs)
    assert not bool(out.synthesis.iloc[0]["all_repeated_points_reproducible"])
    assert not bool(out.synthesis.iloc[0]["all_size_series_robust"])

from scripts.analysis.performance_analysis import analyze_performance


def _perf_record(study="temperature_sweep", dynamics="glauber", H=-0.75, L=32, T=1.0,
                 speedup=2.0, compression=10.0, std_attempts=1000.0, nf_equiv=1000.0,
                 events=100.0, std_ns=20.0, nf_ns=100.0, acceptance=0.1):
    return {
        "study": study, "dynamics": dynamics, "H": H, "L": L, "N": L*L,
        "T": T, "J": 1.0,
        "cpu_standard_s_per_escape": 1.0,
        "cpu_nfold_s_per_escape": 1.0/speedup,
        "speedup_standard_over_nfold": speedup,
        "mean_standard_attempts_per_escape": std_attempts,
        "mean_nfold_equiv_attempts_per_escape": nf_equiv,
        "mean_nfold_events_per_escape": events,
        "nfold_equiv_attempts_per_event": compression,
        "standard_cpu_ns_per_attempt": std_ns,
        "nfold_cpu_ns_per_event": nf_ns,
        "standard_acceptance_fraction": acceptance,
    }


def test_8c_mechanistic_speedup_decomposition():
    r=_perf_record(speedup=2.0, compression=10.0, std_ns=20.0, nf_ns=100.0)
    out=analyze_performance(pd.DataFrame([r]), "snap_test")
    row=out.records.iloc[0]
    assert row["event_cost_ratio_nfold_over_standard"] == pytest.approx(5.0)
    assert row["break_even_compression"] == pytest.approx(5.0)
    assert row["mechanistic_speedup"] == pytest.approx(2.0)


def test_8c_compression_matches_inverse_acceptance():
    r=_perf_record(compression=10.0, acceptance=0.1)
    out=analyze_performance(pd.DataFrame([r]), "snap_test")
    assert out.records.iloc[0]["compression_over_inverse_acceptance"] == pytest.approx(1.0)


def test_8c_detects_temperature_crossover():
    rows=[
        _perf_record(T=1.0, speedup=4.0, compression=20.0),
        _perf_record(T=2.0, speedup=0.5, compression=2.5),
    ]
    out=analyze_performance(pd.DataFrame(rows), "snap_test")
    s=out.temperature.iloc[0]
    assert s["performance_regime"] == "CROSSOVER_WITHIN_TESTED_T"
    assert 1.0 < s["crossover_T_loglinear"] < 2.0


def test_8c_size_scaling_exponent_is_recovered():
    rows=[]
    for L in [8,16,32,64]:
        r=_perf_record(study="scalability_L", L=L, T=1.5, speedup=2.0,
                       compression=10.0, acceptance=np.nan)
        r["cpu_standard_s_per_escape"]=(L/8)**2
        r["cpu_nfold_s_per_escape"]=0.5*(L/8)**2
        rows.append(r)
    out=analyze_performance(pd.DataFrame(rows), "snap_test")
    s=out.size.iloc[0]
    assert s["standard_cpu_scaling_exponent_vs_L"] == pytest.approx(2.0)
    assert s["nfold_cpu_scaling_exponent_vs_L"] == pytest.approx(2.0)
    assert s["speedup_scaling_exponent_vs_L"] == pytest.approx(0.0, abs=1e-12)


def test_8c_rejects_duplicate_temperature_records():
    a=_perf_record(T=1.0); b=_perf_record(T=1.0)
    with pytest.raises(DataContractError, match="duplicate dynamics/H/T"):
        analyze_performance(pd.DataFrame([a,b]), "snap_test")
