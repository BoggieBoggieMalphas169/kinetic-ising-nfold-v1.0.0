"""Pruebas de validacion independiente del formato de trazas B3."""
import csv
import json
from pathlib import Path

import pytest

from scripts.practica_cierre.trazas_b3 import close, energy, spin_decode, validate_pair


def test_energy_periodic_counts_bonds_once():
    assert energy([1] * 16, 4, 1, -3) == 16
    s = [1] * 16
    s[0] = -1
    assert energy(s, 4, 1, -3) == 18


def test_spin_decoding_strict():
    assert spin_decode('1010' * 4, 4) == [1, -1, 1, -1] * 4
    for bad in ('111', 'x' * 16, '2' * 16):
        with pytest.raises(ValueError):
            spin_decode(bad, 4)


def test_comparison_float_nonfinite():
    assert close(0.25, 0.25)
    assert not close(float('nan'), 0)


def _write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sample(tmp_path: Path, *, bad_bits=False, bad_energy=False, tail=False):
    frames_path = tmp_path / 'ex_frames.csv'
    events_path = tmp_path / 'ex_events.csv'
    summary_path = tmp_path / 'summary.csv'
    base = dict(run=0, algorithm='standard', dynamics='glauber', L=4, T=1.5, J=1,
                H=-3, seed=1234, stream=1)
    frames = [dict(frame=0, **base, attempts=0, time_mcss=0, events=0, M=16, E=16, spin_bits='1' * 16)]
    final_bits = '0' + '1' * 15
    last = dict(frame=1, **base, attempts=2, time_mcss=2 / 16, events=1,
                M=14, E=20 if bad_energy else 18,
                spin_bits='0' * 16 if bad_bits else final_bits)
    frames.append(last)
    events = [dict(event=1, run=0, attempts=2, wait_attempts=2, time_mcss=2 / 16,
                   site=0, spin_after=0, M=14, E=18)]
    attempts = 2
    if tail:
        attempts = 5
        frames.append(dict(frame=2, **base, attempts=5, time_mcss=5 / 16,
                           events=1, M=14, E=18, spin_bits=final_bits))
    summary = [dict(run=0, L=4, N=16, T=1.5, J=1, H=-3, dynamics='glauber',
                    algorithm='standard', seed=1234, stream=1, attempts=attempts,
                    time_attempts=attempts, time_mcss=attempts/16, accepted=1, events=1,
                    acceptance_rate=1/attempts, final_M=14, final_E=18, reached_M0=0,
                    cpu_seconds=0.01)]
    _write_csv(frames_path, frames)
    _write_csv(events_path, events)
    _write_csv(summary_path, summary)
    return tmp_path / 'ex', summary_path


def test_validated_event_reconstructs_frames(tmp_path):
    prefix, summary = _sample(tmp_path)
    x = validate_pair(prefix, summary, every=1)
    assert x['events'] == 1 and x['frames'] == 2


def test_terminal_rejected_attempts_are_recorded(tmp_path):
    prefix, summary = _sample(tmp_path, tail=True)
    result = validate_pair(prefix, summary, every=1)
    assert result['attempts'] == 5 and result['frames'] == 3


def test_corrupt_configuration_is_caught(tmp_path):
    prefix, summary = _sample(tmp_path, bad_bits=True)
    with pytest.raises(ValueError, match='Fotograma incompatible'):
        validate_pair(prefix, summary, every=1)


def test_corrupt_energy_is_caught(tmp_path):
    prefix, summary = _sample(tmp_path, bad_energy=True)
    with pytest.raises(ValueError, match='Energia'):
        validate_pair(prefix, summary, every=1)
