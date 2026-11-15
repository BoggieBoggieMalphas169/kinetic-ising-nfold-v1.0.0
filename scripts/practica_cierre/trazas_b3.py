"""Bloque 3: ejecucion y auditoria de trazas reales de Ising.

- La release original sigue congelada.
- Compila un motor instrumentado como overlay separado.
- Cada salida se guarda en un directorio nuevo (nunca sobrescribe las medidas).
- Las configuraciones se validan reproduciendo eventos uno a uno.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validar_baseline import ROOT, create_run_dir, manifest_state


def energy(spins: list[int], L: int, J: float, H: float) -> float:
    """Suma cada enlace una sola vez: derecho + inferior, CC periodicas."""
    N = L * L
    if len(spins) != N or any(s not in (-1, 1) for s in spins):
        raise ValueError("Configuracion de espines incorrecta")
    interaction = 0
    for y in range(L):
        for x in range(L):
            i = y * L + x
            interaction += spins[i] * (spins[y * L + (x + 1) % L] +
                                       spins[((y + 1) % L) * L + x])
    return -J * interaction - H * sum(spins)


def spin_decode(bits: str, L: int) -> list[int]:
    if len(bits) != L * L or set(bits) - {"0", "1"}:
        raise ValueError("spin_bits invalido: no se permite truncamiento")
    return [1 if bit == "1" else -1 for bit in bits]


def close(a: float, b: float, *, atol: float = 1e-9) -> bool:
    return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-11, abs_tol=atol)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_pair(prefix: Path, summary_csv: Path, *, expected_algorithm: str | None = None,
                  expected_dynamics: str | None = None, every: int | None = None,
                  expected_run: int = 0) -> dict[str, Any]:
    """Verifica cadena de eventos, consistencia termodinamica y cierre frente a CSV."""
    frames = _read_csv(Path(str(prefix) + "_frames.csv"))
    events = _read_csv(Path(str(prefix) + "_events.csv"))
    summary = _read_csv(summary_csv)
    if not frames or not summary:
        raise ValueError("Trazas o resumen vacios")
    matching = [r for r in summary if int(r["run"]) == expected_run]
    if len(matching) != 1:
        raise ValueError("La realizacion seleccionada no aparece una sola vez en el CSV")
    result = matching[0]
    algo = result["algorithm"]
    dyn = result["dynamics"]
    if expected_algorithm is not None and algo != expected_algorithm:
        raise ValueError("Algoritmo distinto del esperado")
    if expected_dynamics is not None and dyn != expected_dynamics:
        raise ValueError("Dinamica distinta de la esperada")
    if algo not in {"standard", "nfold"} or dyn not in {"glauber", "metropolis"}:
        raise ValueError("Etiqueta de motor o dinamica desconocida")
    L = int(result["L"])
    if L < 3 or L % 2 or int(result["N"]) != L * L:
        raise ValueError("Red invalida")
    J, H, T = (float(result[x]) for x in ("J", "H", "T"))
    seed, stream = int(result["seed"]), int(result["stream"])
    if not close(T, float(frames[0]["T"])):
        raise ValueError("Temperatura inconsistente")
    if len({int(f["frame"]) for f in frames}) != len(frames):
        raise ValueError("Indices de frame duplicados")

    # Se reconstruye la trayectoria desde +1 y cada flip realmente aceptado,
    # independientemente de los snapshots (una comprobacion distinta del motor C).
    spins = [1] * (L * L)
    current_M = L * L
    current_E = energy(spins, L, J, H)
    previous_attempts = 0
    prev_event = 0
    frame_ptr = 0

    def check_frame(row: dict[str, str], at_event: int, at_attempt: int) -> None:
        nonlocal frame_ptr
        if int(row["frame"]) != frame_ptr or int(row["run"]) != expected_run:
            raise ValueError("Numeracion de fotogramas incorrecta")
        if row["algorithm"] != algo or row["dynamics"] != dyn:
            raise ValueError("Metadatos de fotogramas inconsistentes")
        if int(row["L"]) != L or int(row["seed"]) != seed or int(row["stream"]) != stream:
            raise ValueError("Metadatos de red o RNG inconsistentes")
        if not all(close(float(row[k]), value) for k, value in (("J", J), ("H", H), ("T", T))):
            raise ValueError("Metadatos de parametros inconsistentes")
        if int(row["events"]) != at_event or int(row["attempts"]) != at_attempt:
            raise ValueError("Frame no coincide con el evento/instante reconstruido")
        if not close(float(row["time_mcss"]), at_attempt / (L * L)):
            raise ValueError("MCSS del frame incorrecto")
        if spin_decode(row["spin_bits"], L) != spins:
            raise ValueError("Fotograma incompatible con secuencia de flips")
        if int(row["M"]) != sum(spins) or not close(float(row["E"]), energy(spins, L, J, H)):
            raise ValueError("Energia o magnetizacion del frame incorrecta")
        frame_ptr += 1

    check_frame(frames[0], 0, 0)
    for event_row in events:
        seq = int(event_row["event"])
        if seq != prev_event + 1:
            raise ValueError("Saltos/duplicados en la numeracion de eventos")
        if int(event_row["run"]) != expected_run:
            raise ValueError("Run incorrecto en eventos")
        attempts = int(event_row["attempts"])
        wait = int(event_row["wait_attempts"])
        if wait <= 0 or attempts <= previous_attempts or attempts - previous_attempts != wait:
            raise ValueError("Reloj de intentos incompatible con esperas")
        if not close(float(event_row["time_mcss"]), attempts / (L * L)):
            raise ValueError("Reloj MCSS incorrecto en eventos")
        site = int(event_row["site"])
        if not 0 <= site < L * L:
            raise ValueError("Indice de sitio invalido")
        old_spin = spins[site]
        x, y = site % L, site // L
        neighbours = (spins[y * L + (x + 1) % L] + spins[y * L + (x - 1) % L]
                      + spins[((y + 1) % L) * L + x] + spins[((y - 1) % L) * L + x])
        current_E += 2.0 * old_spin * (J * neighbours + H)
        current_M -= 2 * old_spin
        spins[site] = -old_spin
        if int(event_row["spin_after"]) != (1 if spins[site] > 0 else 0):
            raise ValueError("Orientacion del spin tras evento incorrecta")
        if int(event_row["M"]) != current_M or not close(float(event_row["E"]), current_E):
            raise ValueError("Energia o magnetizacion incremental inconsistente tras evento")
        previous_attempts = attempts
        prev_event = seq
        if frame_ptr < len(frames) and int(frames[frame_ptr]["events"]) == seq:
            # Una instantanea intermedia o el estado final, exactamente en un evento.
            check_frame(frames[frame_ptr], seq, attempts)

    n_events = int(result["events"])
    total_attempts = int(result["attempts"] if algo == "standard" else result["equivalent_attempts"])
    if n_events != prev_event:
        raise ValueError("Eventos de la traza no coinciden con resultado final")
    if total_attempts < previous_attempts:
        raise ValueError("Intentos totales menores que el ultimo flip")
    if algo == "standard" and n_events != int(result["accepted"]):
        raise ValueError("Aceptaciones no coinciden con cantidad de eventos")
    if not close(float(result["time_mcss"]), total_attempts / (L * L)):
        raise ValueError("Tiempo final incorrecto")
    if int(result["final_M"]) != current_M or not close(float(result["final_E"]), energy(spins, L, J, H)):
        raise ValueError("Resultado final distinto de reconstruccion")
    if bool(int(result["reached_M0"])) != (sum(spins) == 0):
        raise ValueError("Bandera reached_M0 invalida")

    # Tras el ultimo evento puede haber intentos rechazados si se alcanzó un limite.
    if frame_ptr < len(frames):
        if frame_ptr != len(frames) - 1:
            raise ValueError("Frames extra no justificados")
        check_frame(frames[frame_ptr], n_events, total_attempts)
    if frame_ptr != len(frames) or not frames:
        raise ValueError("No se guardo el estado final")
    last = frames[-1]
    if int(last["attempts"]) != total_attempts or int(last["events"]) != n_events:
        raise ValueError("Ultima instantanea no es el estado final")
    if every is not None:
        if every < 1:
            raise ValueError("Stride invalido")
        for f in frames[1:-1]:
            if int(f["events"]) % every != 0:
                raise ValueError("Fotograma intermedio no respeta muestreo")
    return {
        "status": "PASS", "algorithm": algo, "dynamics": dyn, "L": L, "run": expected_run,
        "T": T, "J": J, "H": H, "seed": seed, "stream": stream,
        "frames": len(frames), "events": len(events), "attempts": total_attempts,
        "time_mcss": total_attempts / (L * L), "final_M": sum(spins),
        "reached_M0": sum(spins) == 0,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def _exe(build: Path, algo: str) -> Path:
    name = f"ising_{algo}_trace"
    for candidate in [build / name, build / (name + ".exe"), build / "Release" / (name + ".exe"),
                      build / "Release" / name, build / "Debug" / (name + ".exe")]:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Ejecutable de Bloque 3 ausente para {algo} en {build}")


def _original_exe(build: Path, algo: str) -> Path:
    name = f"ising_{algo}"
    for candidate in [build / "simulator" / name,
                      build / "simulator" / (name + ".exe"),
                      build / "simulator" / "Release" / (name + ".exe"),
                      build / "simulator" / "Release" / name]:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Motor original no localizado: {name} en {build}")


def _run(args: list[str], *, cwd: Path, log: Path) -> None:
    start = time.perf_counter()
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    log.write_text("$ " + " ".join(args) + "\n" + proc.stdout + "\n[stderr]\n" + proc.stderr +
                   f"\nreturn_code={proc.returncode} duration={time.perf_counter()-start:.3f}s\n", encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"Fallo la ejecucion {args[0]} ({proc.returncode}). Log: {log}")


def _science_rows_equal(control: Path, traced: Path) -> bool:
    a, b = _read_csv(control), _read_csv(traced)
    if len(a) != len(b):
        return False
    for left, right in zip(a, b):
        if {k: v for k, v in left.items() if k != "cpu_seconds"} != \
           {k: v for k, v in right.items() if k != "cpu_seconds"}:
            return False
    return True


def generate(root: Path, opts: argparse.Namespace) -> Path:
    before = manifest_state(root)
    # Baseline must already match release_manifest; otherwise fail BEFORE producing data.
    with (root / "release/release_manifest.csv").open(newline="", encoding="utf-8") as f:
        invalid = [r["path"] for r in csv.DictReader(f) if before[r["path"]] != r["sha256"]]
    if invalid:
        raise ValueError(f"Release historica alterada ({invalid[:3]})")
    directory = create_run_dir(root, "trazas_b3")
    logs = directory / "logs"
    status = "FAIL"
    reports: list[dict[str, Any]] = []
    try:
        build = root / "build" / "practica_b3"
        if not opts.no_build:
            _run(["cmake", "-S", str(root / "simulator" / "tracing"), "-B", str(build),
                  "-DCMAKE_BUILD_TYPE=Release", f"-DPython3_EXECUTABLE={sys.executable}"],
                 cwd=root, log=logs / "01_cmake_configure.log")
            _run(["cmake", "--build", str(build), "--config", "Release"],
                 cwd=root, log=logs / "02_cmake_build.log")
            _run(["ctest", "--test-dir", str(build), "--output-on-failure", "-C", "Release"],
                 cwd=root, log=logs / "03_ctest_tracing.log")
        # Segunda compilacion completamente historica: el resultado numerico del
        # ejecutable trazado tambien debe coincidir con la release v1.0.0 original.
        build_original = root / "build" / "practica_b3_original"
        if not opts.no_build:
            _run(["cmake", "-S", str(root), "-B", str(build_original),
                  "-DCMAKE_BUILD_TYPE=Release", f"-DPython3_EXECUTABLE={sys.executable}"],
                 cwd=root, log=logs / "04_original_configure.log")
            _run(["cmake", "--build", str(build_original), "--config", "Release"],
                 cwd=root, log=logs / "05_original_build.log")
            _run(["ctest", "--test-dir", str(build_original), "--output-on-failure", "-C", "Release"],
                 cwd=root, log=logs / "06_original_ctest.log")
        for algo in (['standard', 'nfold'] if opts.algoritmos == 'ambos' else [opts.algoritmos]):
            for dyn in (['glauber', 'metropolis'] if opts.dinamicas == 'ambas' else [opts.dinamicas]):
                case = directory / f"{algo}_{dyn}"
                case.mkdir()
                binary = _exe(build, algo)
                common = [str(binary), "--L", str(opts.L), "--T", str(opts.T),
                          "--J", str(opts.J), "--H", str(opts.H), "--runs", str(opts.runs),
                          "--seed", str(opts.seed), "--dynamics", dyn]
                if algo == 'standard':
                    common += ["--max-attempts", str(opts.max_attempts)]
                else:
                    common += ["--max-events", str(opts.max_events),
                               "--max-time-attempts", str(opts.max_attempts)]
                prefix = case / "trayectoria"
                traced_csv = case / "resumen_trazado.csv"
                control_csv = case / "resumen_control.csv"
                original_csv = case / "resumen_original.csv"
                # C fopen() may use the Windows ANSI codepage. Relative ASCII paths
                # avoid encoding issues when the project root contains "4º" etc.
                rel = lambda p: p.relative_to(root).as_posix()
                _run(common + ["--trace-prefix", rel(prefix), "--trace-run", str(opts.trace_run),
                               "--trace-every", str(opts.stride), "--output", rel(traced_csv)],
                     cwd=root, log=logs / f"ejecucion_{algo}_{dyn}.log")
                _run(common + ["--output", rel(control_csv)],
                     cwd=root, log=logs / f"control_{algo}_{dyn}.log")
                if not _science_rows_equal(control_csv, traced_csv):
                    raise ValueError(f"REGRESION: traza activa cambia resultados de {algo}/{dyn}")
                original_binary = _original_exe(build_original, algo)
                _run([str(original_binary)] + common[1:] + ["--output", rel(original_csv)],
                     cwd=root, log=logs / f"original_{algo}_{dyn}.log")
                if not _science_rows_equal(original_csv, traced_csv):
                    raise ValueError(f"REGRESION: B3 no coincide con release original {algo}/{dyn}")
                checked = validate_pair(prefix, traced_csv, expected_algorithm=algo,
                                        expected_dynamics=dyn, every=opts.stride,
                                        expected_run=opts.trace_run)
                checked["regression_off_vs_on"] = "IDENTICAL_EXCEPT_CPU_SECONDS"
                checked["regression_original_vs_trace"] = "IDENTICAL_EXCEPT_CPU_SECONDS"
                (case / "validacion_traza.json").write_text(json.dumps(checked, indent=2), encoding="utf-8")
                reports.append(checked)
                print(f"{algo:8s} {dyn:10s} : PASS  {checked['events']} eventos, {checked['frames']} frames")
        status = "PASS"
        return directory
    finally:
        unchanged = manifest_state(root) == before
        if not unchanged:
            status = "FAIL"
        meta = {
            "status": status, "created_utc": datetime.now(timezone.utc).isoformat(),
            "source": "Ising B2 + B3 traced overlay", "snapshot": "snap_0cc46433731097c4",
            "python": sys.version.splitlines()[0], "platform": platform.platform(),
            "historical_manifest_unchanged": unchanged, "arguments": vars(opts), "cases": reports,
        }
        (directory / "MANIFEST_B3.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = ["# Bloque 3: trazas cineticas", "", f"**Estado: {status}**", "",
                 "| Algoritmo | Dinamica | Eventos | Fotogramas | Equivalencia on/off |",
                 "|---|---|---:|---:|---|"]
        for r in reports:
            lines.append(f"| {r['algorithm']} | {r['dynamics']} | {r['events']} | {r['frames']} | Identica salvo CPU |")
        lines += ["", "Cada directorio contiene `resumen_trazado.csv`, `resumen_control.csv`,",
                  "`resumen_original.csv`, `trayectoria_frames.csv`, `trayectoria_events.csv`",
            "y `validacion_traza.json`.",
                  "", "No son animaciones: las trazas son las entradas cientificas para Bloque 4/5.",
                  "", f"Manifiesto historico intacto: {unchanged}"]
        (directory / "RESUMEN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        filehashes = []
        for p in sorted(directory.rglob('*')):
            if p.is_file() and p.name != 'SHA256_NUEVAS_SALIDAS.csv':
                filehashes.append((p.relative_to(directory).as_posix(), sha256(p)))
        with (directory / 'SHA256_NUEVAS_SALIDAS.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f); writer.writerow(['path', 'sha256']); writer.writerows(filehashes)
        print(f"Reporte de trazas: {directory} (status {status})")
        if not unchanged:
            raise ValueError("La generacion ha modificado archivos historicos: ver manifiesto")


def validate_directory(path: Path) -> list[dict[str, Any]]:
    # Check new output provenance before physics reconstruction.
    hashes = _read_csv(path / 'SHA256_NUEVAS_SALIDAS.csv')
    if not hashes:
        raise ValueError('Manifiesto SHA-256 de trazas vacio')
    for record in hashes:
        target = (path / record['path']).resolve()
        if not target.is_relative_to(path.resolve()) or not target.is_file():
            raise ValueError(f"Ruta de hashes invalida: {record['path']}")
        if sha256(target) != record['sha256']:
            raise ValueError(f"Hash de trazas alterado: {record['path']}")
    manifest = json.loads((path / "MANIFEST_B3.json").read_text(encoding="utf-8"))
    if manifest.get('status') != 'PASS':
        raise ValueError("Ejecucion no completada: status != PASS")
    reports = []
    for case in manifest["cases"]:
        directory = path / f"{case['algorithm']}_{case['dynamics']}"
        result = validate_pair(directory / 'trayectoria', directory / 'resumen_trazado.csv',
                               expected_algorithm=case['algorithm'], expected_dynamics=case['dynamics'],
                               expected_run=case['run'])
        if result['frames'] != case['frames'] or result['events'] != case['events']:
            raise ValueError("Registros de validacion no coinciden")
        if not _science_rows_equal(directory / 'resumen_control.csv', directory / 'resumen_trazado.csv'):
            raise ValueError("Diferencia entre control y traza")
        if not _science_rows_equal(directory / 'resumen_original.csv', directory / 'resumen_trazado.csv'):
            raise ValueError("Diferencia entre release original y traza")
        reports.append(result)
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generacion reproducible y validacion de trazas Ising B3")
    sub = parser.add_subparsers(dest="accion", required=True)
    gen = sub.add_parser("generar")
    gen.add_argument('--L', type=int, default=16)
    gen.add_argument('--T', type=float, default=1.5)
    gen.add_argument('--J', type=float, default=1.)
    gen.add_argument('--H', type=float, default=-3.)
    gen.add_argument('--runs', type=int, default=1)
    gen.add_argument('--trace-run', type=int, default=0)
    gen.add_argument('--seed', type=int, default=1234)
    gen.add_argument('--stride', type=int, default=8)
    gen.add_argument('--algoritmos', choices=['ambos','standard','nfold'], default='ambos')
    gen.add_argument('--dinamicas', choices=['ambas','glauber','metropolis'], default='ambas')
    gen.add_argument('--max-attempts', type=int, default=2000000)
    gen.add_argument('--max-events', type=int, default=100000)
    gen.add_argument('--no-build', action='store_true')
    val = sub.add_parser("validar")
    val.add_argument('--directorio', type=Path)
    try:
        opts = parser.parse_args(argv)
        if opts.accion == 'generar':
            if opts.L < 4 or opts.L % 2 or opts.T <= 0 or opts.J <= 0 or not all(math.isfinite(x) for x in [opts.T, opts.H, opts.J]):
                parser.error('L debe ser par >= 4, T y J positivos y parametros finitos')
            if min(opts.runs, opts.stride, opts.max_attempts, opts.max_events) < 1 or opts.seed < 0 or opts.trace_run < 0 or opts.trace_run >= opts.runs:
                parser.error('runs/stride/limites deben ser positivos; 0 <= trace-run < runs')
            generate(ROOT, opts)
            return 0
        parent = ROOT / 'results' / 'practica_cierre'
        if opts.directorio is None:
            matches = sorted(parent.glob('*_trazas_b3_*'))
            if not matches:
                raise FileNotFoundError('Todavia no hay ejecuciones B3')
            target = matches[-1]
        else:
            target = opts.directorio.resolve()
        for result in validate_directory(target):
            print(f"PASS {result['algorithm']} {result['dynamics']}: {result['events']} eventos")
        print('Todas las trazas validadas:', target)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR B3: {exc}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
