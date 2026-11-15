"""Validacion C0 y reproduccion 8D en copia aislada.

No edita los CSV, snapshots, figuras ni scripts historicos de la release 1.0.0.
Las salidas se crean en resultados de practica con identificador unico.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = "snap_0cc46433731097c4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_state(root: Path) -> dict[str, str]:
    """Huella de todos los archivos que la release v1.0.0 declara inmutables."""
    manifest = root / "release" / "release_manifest.csv"
    if not manifest.is_file():
        raise FileNotFoundError(f"No existe manifiesto historico: {manifest}")
    files: dict[str, str] = {"release/release_manifest.csv": sha256(manifest)}
    with manifest.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            relative = record["path"]
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(f"Ruta ausente o invalida en manifiesto: {relative}")
            files[relative] = sha256(path)
    return files


def create_run_dir(root: Path, operation: str) -> Path:
    parent = root / "results" / "practica_cierre"
    parent.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        label = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                 + "_" + operation + "_" + uuid.uuid4().hex[:8])
        target = parent / label
        try:
            target.mkdir(exist_ok=False)
            (target / "logs").mkdir()
            return target
        except FileExistsError:
            continue
    raise FileExistsError("Imposible reservar un nombre unico de ejecucion")


def scratch_ignore_factory(source: Path):
    def ignore(directory: str, names: list[str]) -> set[str]:
        path = Path(directory).resolve()
        ignored = {name for name in names if name in {
            ".git", ".venv", ".venv_ising", ".pytest_cache", "__pycache__",
            "build", "dist", ".mypy_cache", ".ruff_cache"
        } or name.startswith("build-")}
        if path == (source / "results").resolve() and "practica_cierre" in names:
            ignored.add("practica_cierre")
        return ignored
    return ignore


@dataclass
class Step:
    name: str
    command: list[str]
    status: str
    exit_code: int
    seconds: float
    log: str


class Report:
    def __init__(self, root: Path, action: str):
        self.root = root
        self.action = action
        self.directory = create_run_dir(root, action)
        self.steps: list[Step] = []
        self.notes: list[str] = []
        self.result = "failed"
        self.details: dict[str, object] = {}

    def run(self, name: str, command: list[str], *, cwd: Path | None = None) -> bool:
        target = self.directory / "logs" / f"{len(self.steps) + 1:02d}_{name}.log"
        print(f"[{len(self.steps)+1:02d}] {name}: iniciando", flush=True)
        begin = time.perf_counter()
        try:
            completed = subprocess.run(command, cwd=cwd or self.root,
                                       capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", check=False)
            output = (completed.stdout or "") + ("\n[stderr]\n" + completed.stderr if completed.stderr else "")
            code = completed.returncode
        except (OSError, ValueError) as exc:
            output = f"Error al ejecutar: {type(exc).__name__}: {exc}\n"
            code = 127
        target.write_text(output, encoding="utf-8")
        elapsed = round(time.perf_counter() - begin, 3)
        ok = code == 0
        self.steps.append(Step(name, command, "PASS" if ok else "FAIL", code, elapsed,
                               target.relative_to(self.directory).as_posix()))
        print(f"      {'PASS' if ok else 'FAIL'} ({elapsed:.2f} s) -> {target.name}", flush=True)
        if not ok:
            print("      Ultimas lineas de error:")
            print("\n".join(output.splitlines()[-12:]))
        return ok

    def save(self) -> None:
        data = {
            "action": self.action,
            "status": self.result,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_release": "v1.0.0",
            "analysis_snapshot": SNAPSHOT,
            "project_root": str(self.root),
            "python": sys.executable,
            "platform": platform.platform(),
            "steps": [vars(item) for item in self.steps],
            "notes": self.notes,
            "details": self.details,
        }
        (self.directory / "validation.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [f"# Resultado del bloque 1: {self.action}", "",
                 f"**Estado: {self.result.upper()}**", "",
                 f"Snapshot de referencia: `{SNAPSHOT}`", "",
                 "| Paso | Estado | Tiempo (s) | Log |", "|---|---|---:|---|"]
        for step in self.steps:
            lines.append(f"| {step.name} | {step.status} | {step.seconds:.3f} | `{step.log}` |")
        if self.notes:
            lines.extend(["", "## Observaciones", ""])
            lines.extend(f"- {note}" for note in self.notes)
        lines.append("")
        (self.directory / "RESUMEN.md").write_text("\n".join(lines), encoding="utf-8")
        print("\nInforme guardado en:", self.directory, flush=True)


def collect_versions() -> dict[str, str | None]:
    versions = {"python": sys.version.splitlines()[0]}
    for name, cmd in [("cmake", ["cmake", "--version"]),
                      ("ctest", ["ctest", "--version"]),
                      ("gcc", ["gcc", "--version"]),
                      ("clang", ["clang", "--version"]),
                      ("git", ["git", "--version"])]:
        try:
            run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6)
            versions[name] = run.stdout.splitlines()[0] if run.returncode == 0 and run.stdout else None
        except (OSError, subprocess.TimeoutExpired):
            versions[name] = None
    return versions


def run_validation(root: Path) -> int:
    report = Report(root, "validar")
    initial = None
    try:
        initial = manifest_state(root)
        report.details["protected_files"] = len(initial)
        report.details["versions"] = collect_versions()
        build_dir = root / "build" / "practica_b1"
        commands = [
            ("integridad_release", [sys.executable, "scripts/release_check.py", "--verify-frozen"]),
            ("snapshot", [sys.executable, "-m", "scripts.analysis.build_quality_snapshot", "--verify",
                          f"results/snapshots/{SNAPSHOT}"]),
            ("cmake_configurar", ["cmake", "-S", ".", "-B", str(build_dir),
                                  "-DCMAKE_BUILD_TYPE=Release", f"-DPython3_EXECUTABLE={sys.executable}"]),
            ("cmake_compilar", ["cmake", "--build", str(build_dir), "--config", "Release"]),
            ("ctest", ["ctest", "--test-dir", str(build_dir), "--output-on-failure", "-C", "Release"]),
            ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ]
        ok = True
        for name, command in commands:
            if not report.run(name, command):
                ok = False
                break
        current = manifest_state(root)
        altered = sorted(key for key in initial if current.get(key) != initial[key])
        report.details["protected_files_modified"] = altered
        if altered:
            report.notes.append("ERROR: se han modificado archivos protegidos: " + ", ".join(altered[:10]))
            ok = False
        else:
            report.notes.append("Ningun archivo de la release congelada ha sido modificado.")
        report.result = "passed" if ok else "failed"
    except Exception as exc:
        report.notes.append(f"ERROR: {type(exc).__name__}: {exc}")
        report.result = "failed"
    finally:
        report.save()
    return 0 if report.result == "passed" else 1


def artifacts(root: Path) -> list[Path]:
    return sorted(p.relative_to(root) for d in (
        "figures/final", "figures/supplementary", "results/final_tables")
        for p in (root / d).iterdir() if p.is_file())



def compare_pdf_pixels(original: Path, generated: Path) -> bool | None:
    """Control visual opcional, NO necesario para usar el bloque con requirements.txt.

    PyMuPDF no forma parte de las dependencias historicas. Si no esta instalado,
    la verificacion pixel a pixel queda registrada como NO_VERIFICADA.
    """
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        with fitz.open(original) as left, fitz.open(generated) as right:
            if len(left) != len(right):
                return False
            for a, b in zip(left, right):
                if a.rect != b.rect:
                    return False
                if a.get_pixmap(alpha=False).samples != b.get_pixmap(alpha=False).samples:
                    return False
            return True
    except (RuntimeError, ValueError):
        return False


def reproduce(root: Path) -> int:
    report = Report(root, "reproducir_8D")
    scratch_parent: Path | None = None
    try:
        protected_before = manifest_state(root)
        scratch_parent = Path(tempfile.mkdtemp(prefix="ising_8D_copia_"))
        scratch = scratch_parent / "repo"
        print("Preparando copia temporal externa a la release ...", flush=True)
        shutil.copytree(root, scratch, ignore=scratch_ignore_factory(root))
        ok = report.run("reproducir_figuras_tablas", [sys.executable, "-m", "scripts.reproduce_8D"], cwd=scratch)
        differences: list[dict[str, str]] = []
        if ok:
            original_artifacts = artifacts(root)
            generated_artifacts = artifacts(scratch)
            if original_artifacts != generated_artifacts:
                ok = False
                report.notes.append("Diferencias en los nombres de artefactos del P08.")
            pdf_visual = {"identical": 0, "not_identical": 0, "not_checked": 0}
            for rel in original_artifacts:
                original = root / rel
                new = scratch / rel
                if not new.is_file():
                    ok = False
                    differences.append({"archivo": rel.as_posix(), "formato": rel.suffix,
                                        "identico": "NO_GENERADO", "sha_original": sha256(original), "sha_generado": ""})
                    continue
                a, b = sha256(original), sha256(new)
                same = a == b
                differences.append({"archivo": rel.as_posix(), "formato": rel.suffix,
                                    "identico": "SI" if same else "NO", "sha_original": a, "sha_generado": b})
                if not same and original.suffix != ".pdf":
                    ok = False
                if not same and original.suffix == ".pdf":
                    visually_equal = compare_pdf_pixels(original, new)
                    if visually_equal is None:
                        pdf_visual["not_checked"] += 1
                    elif visually_equal:
                        pdf_visual["identical"] += 1
                    else:
                        pdf_visual["not_identical"] += 1
                        ok = False
            if len(differences) != 37:
                report.notes.append(f"Se esperaban 37 artefactos, encontrados {len(differences)}")
                ok = False
            with (report.directory / "comparacion_8D.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["archivo", "formato", "identico", "sha_original", "sha_generado"])
                writer.writeheader()
                writer.writerows(differences)
            report.details["artifacts_checked"] = len(differences)
            report.details["pdf_visual_comparison"] = pdf_visual
            report.details["sha256_identical"] = sum(x["identico"] == "SI" for x in differences)
            report.details["pdf_different_sha256"] = sum(x["formato"] == ".pdf" and x["identico"] == "NO" for x in differences)
            if report.details["pdf_different_sha256"]:
                report.notes.append("Algunos PDF cambiaron SHA-256; puede deberse a su fecha de creacion.")
                if pdf_visual["identical"]:
                    report.notes.append(f"Comparacion de raster PDF con PyMuPDF: {pdf_visual['identical']} coinciden visualmente.")
                if pdf_visual["not_checked"]:
                    report.notes.append(f"PDF no verificados pixel a pixel: {pdf_visual['not_checked']} (PyMuPDF opcional no instalado).")
        protected_after = manifest_state(root)
        if protected_before != protected_after:
            report.notes.append("ERROR: algun archivo congelado ha cambiado.")
            ok = False
        else:
            report.notes.append("Los artefactos historicos de la carpeta de trabajo no se han sobrescrito.")
        report.result = "passed" if ok else "failed"
    except Exception as exc:
        report.notes.append(f"ERROR: {type(exc).__name__}: {exc}")
        report.result = "failed"
    finally:
        if scratch_parent is not None:
            shutil.rmtree(scratch_parent, ignore_errors=True)
        report.save()
    return 0 if report.result == "passed" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="C0 - Validar/reproducir v1.0.0 sin alterar resultados historicos")
    ap.add_argument("action", choices=("validar", "reproducir"))
    args = ap.parse_args()
    if not (ROOT / "release" / "release_manifest.csv").is_file():
        ap.error("No se encuentra la release v1.0.0 integra")
    return run_validation(ROOT) if args.action == "validar" else reproduce(ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
