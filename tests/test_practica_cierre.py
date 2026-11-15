"""Regresion de proteccion de datos para el bloque de automatizacion C0/C1."""

import csv
from pathlib import Path

import pytest

from scripts.practica_cierre.validar_baseline import (
    create_run_dir,
    manifest_state,
    scratch_ignore_factory,
    sha256,
)


def _make_manifest(root: Path):
    (root / "release").mkdir()
    (root / "simulator" / "results").mkdir(parents=True)
    source = root / "simulator" / "results" / "original.csv"
    source.write_bytes(b"run,time_mcss\n1,4\n")
    with (root / "release" / "release_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "size_bytes", "sha256"])
        w.writerow(["simulator/results/original.csv", source.stat().st_size, sha256(source)])
    return source


def test_manifest_hash_detects_mutation(tmp_path):
    source = _make_manifest(tmp_path)
    a = manifest_state(tmp_path)
    source.write_bytes(b"changed")
    b = manifest_state(tmp_path)
    assert a != b
    assert a["simulator/results/original.csv"] != b["simulator/results/original.csv"]


def test_manifest_rejects_escape_from_repo(tmp_path):
    _make_manifest(tmp_path)
    f = tmp_path / "release" / "release_manifest.csv"
    with f.open("a", encoding="utf-8") as h:
        h.write("../../secret.csv,3,abc\n")
    with pytest.raises(ValueError):
        manifest_state(tmp_path)


def test_new_results_never_overwrite_prior_run(tmp_path):
    (tmp_path / "results").mkdir()
    a = create_run_dir(tmp_path, "validar")
    (a / "marker.txt").write_text("keep", encoding="utf-8")
    b = create_run_dir(tmp_path, "validar")
    assert a != b
    assert (a / "marker.txt").read_text(encoding="utf-8") == "keep"
    assert not (b / "marker.txt").exists()


def test_scratch_copy_omits_local_runs(tmp_path):
    root = tmp_path / "repo"
    (root / "results").mkdir(parents=True)
    ign = scratch_ignore_factory(root)
    assert "practica_cierre" in ign(str(root / "results"), ["practica_cierre", "snapshots"])
    assert "snapshots" not in ign(str(root / "results"), ["practica_cierre", "snapshots"])
    assert "build" in ign(str(root), ["build", "simulator"])
    assert "simulator" not in ign(str(root), ["build", "simulator"])
