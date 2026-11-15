"""Prueba externa sin dependencias del proyecto: compara motor trazado y sin trazado."""
from __future__ import annotations
import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.practica_cierre.trazas_b3 import validate_pair


def rows(path: Path):
    with path.open(newline='', encoding='utf-8') as f:
        return [{k: v for k, v in row.items() if k != 'cpu_seconds'} for row in csv.DictReader(f)]


def run(exe: Path, algo: str, dyn: str, folder: Path) -> None:
    args = [str(exe), '--L', '8', '--T', '1.5', '--J', '1', '--H', '-3',
            '--runs', '2', '--seed', '3849', '--dynamics', dyn]
    trace = folder / 'traj'
    with_trace = folder / 'with.csv'
    without = folder / 'without.csv'
    subprocess.run(args + ['--trace-prefix', str(trace), '--trace-run', '1',
                           '--trace-every', '3', '--output', str(with_trace)], check=True)
    subprocess.run(args + ['--output', str(without)], check=True)
    if rows(with_trace) != rows(without):
        raise AssertionError('Trace recording altered simulated results')
    result = validate_pair(trace, with_trace, expected_algorithm=algo,
                           expected_dynamics=dyn, every=3, expected_run=1)
    if not result['reached_M0']:
        raise AssertionError('Expected reached M0')
    # The exclusive-create contract prevents overwriting previously recorded trajectories.
    reject = subprocess.run(args + ['--trace-prefix', str(trace), '--trace-run', '1',
                                    '--trace-every', '3', '--output', str(folder / 'reuse.csv')],
                            capture_output=True)
    if reject.returncode == 0:
        raise AssertionError('Trace destination was overwritten unexpectedly')
    print(f"PASS: {algo}/{dyn}, events={result['events']} frames={result['frames']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--standard', type=Path, required=True)
    parser.add_argument('--nfold', type=Path, required=True)
    opt = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ising_b3_trace_ctest_') as td:
        root = Path(td)
        for algo, executable in [('standard',opt.standard),('nfold',opt.nfold)]:
            for dyn in ('glauber','metropolis'):
                dest = root / f'{algo}_{dyn}'
                dest.mkdir()
                run(executable, algo, dyn, dest)
    # Limites de ejecucion: el ultimo frame debe existir aunque no haya flips.
    with tempfile.TemporaryDirectory(prefix='ising_b3_edges_') as td:
        d = Path(td)
        p = d / 'standard'
        summary = d / 'std.csv'
        subprocess.run([str(opt.standard), '--L','8', '--T','0.8', '--H','-0.75',
                        '--max-attempts','1', '--trace-prefix',str(p),
                        '--output',str(summary)], check=True)
        result = validate_pair(p, summary, expected_algorithm='standard', every=1)
        if result['events'] != 0 or result['attempts'] != 1:
            raise AssertionError('Unexpected standard edge result')
        p = d / 'nfold'
        summary = d / 'nf.csv'
        subprocess.run([str(opt.nfold), '--L','8', '--T','0.8', '--H','-0.75',
                        '--max-events','1', '--max-time-attempts','1',
                        '--trace-prefix',str(p), '--output',str(summary)], check=True)
        result = validate_pair(p, summary, expected_algorithm='nfold', every=1)
        if result['events'] != 1:
            raise AssertionError('Unexpected nfold edge result')
        print('PASS: early stops, including geometric waiting beyond cap')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
