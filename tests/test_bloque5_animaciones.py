"""B5: invariantes de tiempo discreto, reconstruccion de spins y archivos GIF/MP4."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest

from scripts.practica_cierre.animaciones_b5 import (
    ROOT, load_case, replay_at_attempts, select_source, select_b5,
    targets_at_attempts, validate_output, source_hashes, gif_durations_ms
)


def _case(name='standard_glauber'):
    return load_case(select_source(ROOT,None)/name)


def test_time_grid_matches_terminal_attempts_exactly():
    assert targets_at_attempts(10,6)==[0,2,4,6,8,10]
    assert targets_at_attempts(3,7)==[0,0,1,1,2,2,3]
    assert targets_at_attempts(0,4)==[0,0,0,0]
    with pytest.raises(ValueError): targets_at_attempts(-1,3)
    with pytest.raises(ValueError): targets_at_attempts(5,1)


def test_gif_duration_quantization_cumulative_error():
    for fps in (3,8,10,12,15,24,30):
        times=gif_durations_ms(64,fps)
        assert len(times)==64 and all(x>=20 and x%10==0 for x in times)
        assert abs(sum(times)-64000/fps)<=5.1


def test_replay_matches_each_original_B3_snapshot():
    case=_case('nfold_metropolis')
    attempts=[int(f['attempts']) for f in case['frames']]
    for original, s in zip(case['frames'],replay_at_attempts(case,attempts)):
        actual=''.join('1' if v==1 else '0' for v in s['spins'].ravel())
        assert actual==original['spin_bits']
        assert s['M']==int(original['M'])
        assert s['E']==pytest.approx(float(original['E']))
        assert s['target_mcss']==pytest.approx(float(original['time_mcss']))


@pytest.mark.parametrize('name',['standard_glauber','standard_metropolis','nfold_glauber','nfold_metropolis'])
def test_all_real_traces_reach_actual_terminal_spins(name):
    case=_case(name)
    r=case['report']
    snaps=list(replay_at_attempts(case,[0,r['attempts']//2,r['attempts']]))
    assert np.array_equal(snaps[0]['spins'],np.ones((r['L'],r['L']),dtype=np.int8))
    assert snaps[-1]['M']==r['final_M']==0
    assert snaps[-1]['event_count']==r['events']
    assert snaps[-1]['terminal']
    assert not snaps[-1]['censored']
    assert np.all(np.isin(snaps[-1]['spins'],[-1,1]))
    bits=case['frames'][-1]['spin_bits']
    assert snaps[-1]['spin_sha256']==hashlib.sha256(bits.encode('ascii')).hexdigest()


def test_rejections_hold_state_until_next_accepted_flip():
    case=_case()
    events=case['events']
    first=int(events[0]['attempts'])
    assert first>=2
    snaps=list(replay_at_attempts(case,[0,first-1,first,first]))
    assert snaps[0]['spin_sha256']==snaps[1]['spin_sha256']
    assert snaps[0]['M']==snaps[1]['M']==case['report']['L']**2
    assert snaps[2]['spin_sha256']!=snaps[0]['spin_sha256']
    assert snaps[2]['spin_sha256']==snaps[3]['spin_sha256']
    assert snaps[2]['event_count']==1


def test_replay_rejects_out_of_order_or_out_of_range_times():
    case=_case()
    with pytest.raises(ValueError):list(replay_at_attempts(case,[3,2]))
    with pytest.raises(ValueError):list(replay_at_attempts(case,[-1]))
    with pytest.raises(ValueError):list(replay_at_attempts(case,[case['report']['attempts']+1]))


def test_censored_zero_events_holds_final_state():
    case={'report':{'L':4,'attempts':12},'frames':[{'spin_bits':'1'*16,'M':'16','E':'16'}],
          'events':[],'censored':True}
    snaps=list(replay_at_attempts(case,[0,1,4,12]))
    assert all(s['event_count']==0 and s['M']==16 and s['censored'] for s in snaps)
    assert all(s['spin_sha256']==snaps[0]['spin_sha256'] for s in snaps)
    assert snaps[-1]['terminal']
    assert snaps[-1]['target_mcss']==.75


def test_source_b3_hashes_and_release_intact():
    source=select_source(ROOT,None)
    hashes=source_hashes(source)
    assert 'MANIFEST_B3.json' in hashes
    assert any(k.endswith('trayectoria_events.csv') for k in hashes)


def test_real_B5_output_and_multimedia_decoding_when_present():
    folder=sorted((ROOT/'results/practica_cierre').glob('*_animaciones_b5_*'))
    if not folder:pytest.skip('GIF/MP4 se generan en la prueba de integracion')
    actual=validate_output(ROOT,select_b5(ROOT,folder[-1]))
    assert actual['status']=='PASS'
    assert actual['clips']==6
    import imageio.v2 as imageio
    from PIL import Image
    out=Path(actual['output_directory'])/'animaciones'
    gif=out/'B5_01_standard_glauber.gif'
    mp4=out/'B5_01_standard_glauber.mp4'
    if gif.exists():
        with Image.open(gif) as im:
            assert im.n_frames>=2
            im.seek(1)
            assert im.info.get('duration',0)>0, 'GIF debe respetar fps y no durar cero'
    if mp4.exists():
        reader=imageio.get_reader(mp4)
        try:
            frame=reader.get_data(0)
            assert frame.ndim==3 and frame.shape[-1]==3
        finally:reader.close()
