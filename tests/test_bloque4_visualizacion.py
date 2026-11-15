"""Pruebas de B4, incluyendo configuraciones reales en la campana B3."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.practica_cierre.visualizacion_b4 import (
    ROOT, load_case, select_frames_by_time, select_source, _same_physics,
    select_b4, validate_output,
)


def _b3() -> Path:
    return select_source(ROOT, None)


def test_source_b3_detected_without_recompiling():
    p = _b3()
    assert (p / 'MANIFEST_B3.json').exists()


def test_series_from_actual_events_and_time():
    a = load_case(_b3() / 'standard_glauber')
    assert a['series'][0]['time_mcss'] == 0
    assert a['series'][0]['m_per_spin'] == 1
    assert len(a['series']) == len(a['events'])+1
    assert a['series'][-1]['M'] == 0
    assert a['series'][-1]['time_mcss'] == pytest.approx(a['report']['time_mcss'])
    assert all(b['attempts'] > x['attempts'] for x,b in zip(a['series'],a['series'][1:]))


def test_magnetization_energy_reported_per_spin():
    b=load_case(_b3() / 'nfold_metropolis')
    N=b['report']['L']**2
    for item in b['series']:
        assert item['m_per_spin'] == pytest.approx(item['M']/N)
        assert item['e_per_spin'] == pytest.approx(item['E']/N)


def test_frame_select_no_interpolation_or_false_equal_spacing():
    frames=[{'frame':str(i),'time_mcss':str(t)} for i,t in enumerate((0,.01, .1, 3.5, 10))]
    selected=select_frames_by_time(frames,5)
    assert selected[0]['frame']=='0'
    assert selected[-1]['frame']=='4'
    assert all(f in frames for f in selected)
    assert len(selected)<=5


def test_frame_selection_rejects_bad_time():
    frames=[{'time_mcss':v} for v in ('0','3','2')]
    with pytest.raises(ValueError,match='monotono'):
        select_frames_by_time(frames,4)


def test_equal_physics_not_identical_trajectories():
    a=load_case(_b3() / 'standard_glauber')
    b=load_case(_b3() / 'nfold_glauber')
    c=load_case(_b3() / 'standard_metropolis')
    assert _same_physics(a,b)
    assert not _same_physics(a,c)
    assert a['frames'][-1]['spin_bits'] != b['frames'][-1]['spin_bits']


def test_reject_sources_outside_practica(tmp_path):
    with pytest.raises(ValueError,match='dentro'):
        select_source(ROOT,tmp_path)


def test_real_b4_output_verifies_if_built():
    parent=ROOT/'results/practica_cierre'
    folders=list(parent.glob('*_visualizacion_b4_*'))
    if not folders:
        pytest.skip('Los productos B4 se generan en CI de forma independiente')
    d=select_b4(ROOT,str(sorted(folders)[-1]))
    result=validate_output(ROOT,d)
    assert result['status']=='PASS'
    assert result['figures']>=8


def test_censored_zero_events_preserves_rejection_wait(tmp_path):
    """Sin flips el sistema sigue en +1, pero transcurren MCSS."""
    source = tmp_path / 'no_events'
    frames = [
        dict(frame=0, run=0, algorithm='standard', dynamics='glauber', L=4, T=1.5,
             J=1, H=-3, seed=1234, stream=1, attempts=0, time_mcss=0,
             events=0, M=16, E=16, spin_bits='1'*16),
        dict(frame=1, run=0, algorithm='standard', dynamics='glauber', L=4, T=1.5,
             J=1, H=-3, seed=1234, stream=1, attempts=3, time_mcss=3/16,
             events=0, M=16, E=16, spin_bits='1'*16),
    ]
    with (tmp_path/'no_events_frames.csv').open('w',newline='',encoding='utf-8') as handle:
        w=csv.DictWriter(handle,fieldnames=list(frames[0]));w.writeheader();w.writerows(frames)
    with (tmp_path/'no_events_events.csv').open('w',newline='',encoding='utf-8') as handle:
        handle.write('event,run,attempts,wait_attempts,time_mcss,site,spin_after,M,E\n')
    summary = dict(run=0,L=4,N=16,T=1.5,J=1,H=-3,dynamics='glauber',
                   algorithm='standard',seed=1234,stream=1,attempts=3,time_attempts=3,
                   time_mcss=3/16,accepted=0,events=0,acceptance_rate=0,
                   final_M=16,final_E=16,reached_M0=0,cpu_seconds=0.1)
    with (tmp_path/'resumen_trazado.csv').open('w',newline='',encoding='utf-8') as handle:
        w=csv.DictWriter(handle,fieldnames=list(summary));w.writeheader();w.writerow(summary)
    # load_case espera el prefijo trayectoria_{frames,events}.csv
    (tmp_path/'trayectoria_frames.csv').write_bytes((tmp_path/'no_events_frames.csv').read_bytes())
    (tmp_path/'trayectoria_events.csv').write_bytes((tmp_path/'no_events_events.csv').read_bytes())
    result=load_case(tmp_path)
    assert result['censored']
    assert len(result['events'])==0
    assert len(result['series'])==2
    assert result['series'][-1]['source']=='terminal_no_flip'
    assert result['series'][-1]['time_mcss']==pytest.approx(3/16)
    assert result['series'][-1]['m_per_spin']==1
