from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
SNAPSHOT = "snap_0cc46433731097c4"


def test_release_metadata_and_version_agree():
    assert (ROOT / "VERSION").read_text().strip() == VERSION
    meta = json.loads((ROOT / "release/release_metadata.json").read_text(encoding="utf-8"))
    assert meta["version"] == VERSION
    assert meta["analysis_snapshot"] == SNAPSHOT
    assert meta["simulator_core_included"] is True


def test_release_governance_files_exist():
    for name in ["LICENSE", "CITATION.cff", "CHANGELOG.md", "RELEASE_NOTES.md", "CONTRIBUTING.md"]:
        assert (ROOT / name).is_file(), name
    assert (ROOT / ".github/workflows/full-ci.yml").is_file()
    assert (ROOT / "scripts/release_check.py").is_file()


def test_ci_runs_c_and_python_validation():
    text = (ROOT / ".github/workflows/full-ci.yml").read_text(encoding="utf-8")
    assert "cmake -S . -B build" in text
    assert "ctest --test-dir build" in text
    assert "pytest -q" in text
    assert "release_check.py --verify-frozen" in text
    assert "python -m scripts.reproduce_8D" in text


def test_citation_is_scoped_and_versioned():
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f'version: "{VERSION}"' in text
    assert "n-fold way" in text
    assert "license: MIT" in text
    assert "Integrated C simulation" in text


def test_release_readme_links_resolve():
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for source in [ROOT / "README.md", ROOT / "README_ES.md"]:
        for target in pattern.findall(source.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            assert (source.parent / target).resolve().exists(), (source.name, target)


def test_release_scope_includes_c_core():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "validated" in text and "simulation engine" in text
    assert (ROOT / "simulator/src/standard_mc.c").is_file()
    assert (ROOT / "simulator/src/nfold.c").is_file()
    status = (ROOT / "release/INTEGRATION_STATUS.md").read_text(encoding="utf-8").lower()
    assert "included in v1.0.0" in status
    assert "prompt-6 standard monte carlo c source" in status


def test_final_artifact_counts_match_release_contract():
    assert len(list((ROOT / "figures/final").glob("*.png"))) == 6
    assert len(list((ROOT / "figures/final").glob("*.pdf"))) == 6
    assert len(list((ROOT / "figures/supplementary").glob("*.png"))) == 2
    assert len(list((ROOT / "figures/supplementary").glob("*.pdf"))) == 2
    assert len(list((ROOT / "results/final_tables").glob("*.csv"))) == 7


def test_runtime_cache_and_build_patterns_are_ignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in text
    assert ".pytest_cache/" in text
    assert "build/" in text


def test_release_bundle_builder_exists():
    assert (ROOT / "scripts/build_release_bundle.py").is_file()
