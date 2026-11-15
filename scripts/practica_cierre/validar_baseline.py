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
        # CMake sin -G puede elegir NMake en PowerShell incluso cuando solo hay GCC.
        # Para Windows, usar un generador detectado en PATH y aislar su cache CMake.
        generator = None
        if os.name == "nt":
            preferred = os.environ.get("CMAKE_GENERATOR", "").strip()
            supported = {"Ninja": "ninja", "MinGW Makefiles": "mingw32-make"}
            if preferred in supported and shutil.which(supported[preferred]):
                generator = preferred
            elif shutil.which("ninja"):
                generator = "Ninja"
            elif shutil.which("mingw32-make") and shutil.which("gcc"):
                generator = "MinGW Makefiles"
        build_tag = ("_" + generator.lower().replace(" ", "_")) if generator else ""
        build_dir = root / "build" / ("practica_b1" + build_tag)
        cmake_flags = (["-G", generator] if generator else [])
        if generator and shutil.which("gcc"):
            cmake_flags.append(f"-DCMAKE_C_COMPILER={shutil.which('gcc')}")
        commands = [
            ("integridad_release", [sys.executable, "scripts/release_check.py", "--verify-frozen"]),
            ("snapshot", [sys.executable, "-m", "scripts.analysis.build_quality_snapshot", "--verify",
                          f"results/snapshots/{SNAPSHOT}"]),
            ("cmake_configurar", ["cmake", "-S", ".", "-B", str(build_dir),
                                  *cmake_flags,
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


def _normalized_lines(path: Path) -> bytes:
    """Texto con EOL canonico: evita falsos negativos LF vs CRLF en Windows."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _csv_same_content(reference: Path, candidate: Path) -> tuple[bool, str]:
    """Valida estructura, cadenas y valores numericos, no formato del fichero.

    Tolerancia estricta solo para serializacion float entre versiones de pandas.
    No cambia ningun dato cientifico ni la fuente congelada.
    """
    import math

    with reference.open(encoding="utf-8-sig", newline="") as a, candidate.open(encoding="utf-8-sig", newline="") as b:
        arows, brows = list(csv.reader(a)), list(csv.reader(b))
    if len(arows) != len(brows):
        return False, f"numero de filas distinto: {len(arows)} != {len(brows)}"
    if not arows or arows[0] != brows[0]:
        return False, "cabeceras distintas"
    for rowno, (left, right) in enumerate(zip(arows[1:], brows[1:]), start=2):
        if len(left) != len(right):
            return False, f"numero de columnas distinto en fila {rowno}"
        for col, (x, y) in enumerate(zip(left, right), start=1):
            if x == y:
                continue
            try:
                xx, yy = float(x), float(y)
            except (ValueError, TypeError):
                return False, f"texto distinto en fila {rowno}, columna {col}: {x!r} vs {y!r}"
            if not (math.isfinite(xx) and math.isfinite(yy) and math.isclose(xx, yy, rel_tol=1e-12, abs_tol=1e-12)):
                return False, f"valor numerico distinto en fila {rowno}, columna {col}: {x!r} vs {y!r}"
    return True, "estructura y numeros compatibles (rtol=atol=1e-12)"


def _png_visual_similarity(reference: Path, candidate: Path) -> tuple[bool, str]:
    """Comparacion diagnostica de PNG: no confundir hash con aspecto visual.

    Los PNG se producen desde CSV ya congelados; esta prueba solo descarta
    cambios visuales grandes (p. ej., grafica ausente o configuracion distinta).
    """
    try:
        import numpy as np
        from PIL import Image
        with Image.open(reference) as aa, Image.open(candidate) as bb:
            a = aa.convert("RGB")
            b = bb.convert("RGB")
            ratio = max(a.width/b.width, b.width/a.width, a.height/b.height, b.height/a.height)
            if ratio > 1.05:
                return False, f"tamano de imagen muy diferente: {a.size} vs {b.size}"
            b = b.resize(a.size, Image.Resampling.LANCZOS) if a.size != b.size else b
            score = float(np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16)).mean() / 255.0)
            return score <= 0.025, f"diferencia media normalizada={score:.6f} (umbral visual 0.025)"
    except (ImportError, OSError, ValueError) as exc:
        return False, f"no fue posible verificar PNG: {type(exc).__name__}: {exc}"


def reproduce(root: Path) -> int:
    """Reproduccion aislada, comparacion estricta Y comprobacion portable.

    Conserva la auditoria SHA-256 por fichero. Si solo cambian saltos de linea,
    serializacion de floats o rasterizado entre plataformas, exige equivalencia
    numerica CSV y semejanza visual PNG; indica explicitamente que NO existe
    identidad binaria. Los artefactos nuevos se conservan en el informe.
    """
    report = Report(root, "reproducir_8D")
    scratch_parent: Path | None = None
    try:
        protected_before = manifest_state(root)
        scratch_parent = Path(tempfile.mkdtemp(prefix="ising_8D_copia_"))
        scratch = scratch_parent / "repo"
        print("Preparando copia temporal externa a la release ...", flush=True)
        shutil.copytree(root, scratch, ignore=scratch_ignore_factory(root))
        generated_ok = report.run("reproducir_figuras_tablas", [sys.executable, "-m", "scripts.reproduce_8D"], cwd=scratch)
        verified = generated_ok
        differences: list[dict[str, str]] = []
        if generated_ok:
            originals = artifacts(root)
            regenerated = artifacts(scratch)
            if originals != regenerated or len(originals) != 37:
                report.notes.append(f"Artefactos esperados: 37; originales={len(originals)}, regenerados={len(regenerated)}")
                verified = False

            # Conservar las nuevas figuras para uso en la presentacion, sin
            # tocar los 374 ficheros del manifiesto historico.
            savedir = report.directory / "artefactos_regenerados"
            for rel in regenerated:
                src, dst = scratch / rel, savedir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            report.details["regenerated_artifacts"] = str(savedir.relative_to(report.directory))

            csv_verified = 0
            png_verified = 0
            eol_only = 0
            formatting_only = 0
            for rel in originals:
                original = root / rel
                new = scratch / rel
                record = {"archivo": rel.as_posix(), "formato": rel.suffix,
                          "identico": "NO_GENERADO", "sha_original": sha256(original),
                          "sha_generado": "", "comprobacion_portable": "FALTA", "detalle": ""}
                if not new.is_file():
                    verified = False
                    differences.append(record)
                    continue
                a, b = record["sha_original"], sha256(new)
                record["sha_generado"] = b
                record["identico"] = "SI" if a == b else "NO"
                if a == b:
                    record["comprobacion_portable"] = "IDENTICO"
                elif rel.suffix in {".csv", ".md", ".tex"} and _normalized_lines(original) == _normalized_lines(new):
                    record["comprobacion_portable"] = "SOLO_EOL"
                    eol_only += 1
                elif rel.suffix == ".csv":
                    same, detail = _csv_same_content(original, new)
                    record["comprobacion_portable"] = "NUMEROS_COMPATIBLES" if same else "DATOS_DIFERENTES"
                    record["detalle"] = detail
                    if not same:
                        verified = False
                elif rel.suffix == ".png":
                    same, detail = _png_visual_similarity(original, new)
                    record["comprobacion_portable"] = "VISUAL_COMPATIBLE" if same else "VISUAL_DIFERENTE"
                    record["detalle"] = detail
                    if not same:
                        verified = False
                elif rel.suffix in {".md", ".tex"}:
                    # Las tablas MD y LaTeX se crean del mismo DataFrame que
                    # los CSV. No se consideran binarias iguales; sus datos se
                    # contrastan explicitamente en el CSV correspondiente.
                    record["comprobacion_portable"] = "REPRESENTACION_DISTINTA"
                    formatting_only += 1
                    if not (original.with_suffix(".csv").is_file() and new.with_suffix(".csv").is_file()):
                        verified = False
                elif rel.suffix == ".pdf":
                    png1, png2 = original.with_suffix(".png"), new.with_suffix(".png")
                    if png1.is_file() and png2.is_file():
                        same, detail = _png_visual_similarity(png1, png2)
                        record["comprobacion_portable"] = "PDF_CON_PNG_COMPATIBLE" if same else "PDF_CON_PNG_DIFERENTE"
                        record["detalle"] = "Se comprueba PNG emparejado, no identidad PDF. " + detail
                        if not same:
                            verified = False
                    else:
                        record["comprobacion_portable"] = "PDF_SIN_PNG"
                        verified = False
                else:
                    record["comprobacion_portable"] = "NO_COMPROBADO"
                    verified = False
                if rel.suffix == ".csv" and record["comprobacion_portable"] in {"IDENTICO", "SOLO_EOL", "NUMEROS_COMPATIBLES"}:
                    csv_verified += 1
                if rel.suffix == ".png" and record["comprobacion_portable"] in {"IDENTICO", "VISUAL_COMPATIBLE"}:
                    png_verified += 1
                differences.append(record)

            # Refuerzo: verificar CSV siempre, aunque solo difieran los EOL.
            for rel in originals:
                if rel.suffix == ".csv" and (scratch / rel).is_file():
                    same, detail = _csv_same_content(root / rel, scratch / rel)
                    if not same:
                        verified = False
                        report.notes.append(f"DIVERGENCIA NUMERICA {rel}: {detail}")
            if csv_verified != 7 or png_verified != 8:
                verified = False
                report.notes.append(f"Validacion insuficiente: CSV={csv_verified}/7 PNG={png_verified}/8")
            with (report.directory / "comparacion_8D.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["archivo", "formato", "identico", "sha_original",
                                                       "sha_generado", "comprobacion_portable", "detalle"])
                writer.writeheader()
                writer.writerows(differences)
            strict = sum(r["identico"] == "SI" for r in differences)
            report.details.update({"artifacts_checked": len(differences), "sha256_identical": strict,
                                   "csv_verified": csv_verified, "png_verified": png_verified,
                                   "only_line_endings": eol_only, "text_format_changed": formatting_only,
                                   "bitwise_identical": strict == 37})
            if strict != 37:
                report.notes.append("REPRODUCCION NO IDENTICA EN BYTES; ver comparacion_8D.csv.")
                report.notes.append("Se han exigido CSV numericamente compatibles y PNG visualmente semejantes; NO equivale a hashes iguales.")
            if formatting_only:
                report.notes.append(f"Hay {formatting_only} tablas MD/LaTeX con diferencias de formato que conviene revisar visualmente.")
            report.notes.append("Los 37 artefactos regenerados se guardan en artefactos_regenerados/ para la presentacion.")

        protected_after = manifest_state(root)
        if protected_before != protected_after:
            report.notes.append("ERROR: algun archivo historico congelado ha cambiado.")
            verified = False
        else:
            report.notes.append("Los archivos historicos protegidos no se han modificado.")
        report.result = "passed" if verified else "failed"
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
