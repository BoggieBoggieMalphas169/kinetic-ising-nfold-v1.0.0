from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_final_readmes_exist_and_lock_snapshot():
    readme = ROOT / "README.md"
    readme_es = ROOT / "README_ES.md"
    assert readme.is_file()
    assert readme_es.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "snap_0cc46433731097c4" in text
    assert "49 PASS" in text
    assert "3 INCONCLUSIVE" in text
    assert "0 FAIL" in text


def test_documentation_set_is_complete():
    required = [
        "scientific_background.md",
        "methodology.md",
        "validation.md",
        "performance.md",
        "reproducibility.md",
        "results_and_limitations.md",
        "figures_and_tables.md",
        "repository_layout.md",
        "integration_with_simulator.md",
        "references.md",
        "README.md",
    ]
    for name in required:
        assert (ROOT / "docs" / name).is_file(), name


def test_root_markdown_relative_links_resolve():
    # Validate repository-local Markdown links in the two public READMEs.
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for source in [ROOT / "README.md", ROOT / "README_ES.md"]:
        text = source.read_text(encoding="utf-8")
        for target in pattern.findall(text):
            if "://" in target or target.startswith("#"):
                continue
            path = (source.parent / target).resolve()
            assert path.exists(), f"Broken link in {source.name}: {target}"


def test_prompt_history_is_not_cluttering_repository_root():
    assert not list(ROOT.glob("README_PROMPT*.md"))
    history = ROOT / "docs" / "development_history"
    assert history.is_dir()
    assert len(list(history.glob("README_PROMPT*.md"))) >= 10


def test_readme_declares_integrated_simulator_and_analysis_scope():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "validated" in text and "simulation engine" in text
    assert "python analysis/reproducibility layer" in text
    assert "simulator/" in text
    assert "snap_0cc46433731097c4" in text
