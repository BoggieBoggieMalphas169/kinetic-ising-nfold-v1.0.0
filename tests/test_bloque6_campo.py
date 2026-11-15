"""B6: entradas, estadistica, censura y trazabilidad de la campaña de campo."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.practica_cierre.barrido_campo_b6 import (
    ROOT, PRESETS, stable_seed, validate_design, compute_measured, boot_stats,
    analyze_records, expected_cases, check_run_csv, reanalyze, main
)


def spec(**kw):
    s={'perfil':'piloto','L':16,'T':1.5,'J':1.,'runs':3,'fields':[-3.,-1.],
       'max_attempts':100,'dynamics':['glauber'],'seed':123,'bootstrap':100}
    s.update(kw)
    return s


def dataframe(alg='standard',h=-3.,s=None):
    s=s or spec()
    seed=stable_seed(s['seed'],'glauber',alg,h)
    return pd.DataFrame([{
        'run':i,'L':s['L'],'N':s['L']**2,'T':s['T'],'J':s['J'],'H':h,
        'dynamics':'glauber','algorithm':alg,'seed':seed,'stream':i+1,
        'time_attempts':(i+1)*10,'time_mcss':(i+1)*10/s['L']**2,
        'events':i+1,'final_M':0,'reached_M0':1,'cpu_seconds':0.01
    } for i in range(s['runs'])])


def test_seed_is_reproducible_and_distinct():
    assert stable_seed(23,'glauber','standard',-1.)==stable_seed(23,'glauber','standard',-1.)
    assert len({stable_seed(23,d,a,h) for d in ('glauber','metropolis')
                for a in ('standard','nfold') for h in (-3.,-1.)})==8


@pytest.mark.parametrize('bad',[
    {'L':15}, {'fields':[-3.]}, {'fields':[-1.,-1.]}, {'fields':[-3.,1.]},
    {'max_attempts':0}, {'T':0}, {'J':-1}, {'runs':1}, {'bootstrap':99},
])
def test_invalid_experimental_design_is_rejected(bad):
    with pytest.raises(ValueError):validate_design(spec(**bad))


def test_censoring_caps_nfold_even_if_spin_flipped_after_horizon():
    s=spec(max_attempts=100)
    f=dataframe('nfold',s=s)
    f.loc[0,['time_attempts','time_mcss']]=[140,140/256]
    f.loc[0,'reached_M0']=1
    f.loc[1,'reached_M0']=0
    t,events=compute_measured(f,s,'nfold')
    assert list(events)==[False,False,True]
    assert t[0]==pytest.approx(100/256)
    assert t[1]==pytest.approx(20/256)
    assert t[2]==pytest.approx(30/256)


def test_independent_bootstrap_deterministic_and_sharply_identical():
    a=np.array([5.,5.,5.,5.])
    ci_a,ci_b,ci_ratio=boot_stats(a,a,seed=456,nboot=200)
    assert ci_ratio==(1.,1.)
    assert ci_a==(5.,5.)
    assert ci_b==(5.,5.)


def test_missing_pair_and_tamper_rejected(tmp_path):
    s=spec()
    p=tmp_path/'datos_nuevos'/'barrido_H'
    p.mkdir(parents=True)
    records=[]
    for d,h,a in expected_cases(s):
        f=p/(a+str(abs(h))+'.csv')
        dataframe(a,h,s).to_csv(f,index=False)
        from scripts.practica_cierre.validar_baseline import sha256
        records.append({'path':f.relative_to(tmp_path).as_posix(), 'sha256':sha256(f),
                        'dynamics':d,'H':h,'algorithm':a,'seed':stable_seed(s['seed'],d,a,h)})
    summary=analyze_records(tmp_path,s,records)
    assert len(summary)==2
    assert summary.equivalence_status.tolist()==['INCONCLUSIVE','INCONCLUSIVE']
    with pytest.raises(ValueError,match='Faltan/sobran'):
        analyze_records(tmp_path,s,records[:-1])
    (p/'standard3.0.csv').write_text('tampered',encoding='utf-8')
    with pytest.raises(ValueError,match='alterado'):
        analyze_records(tmp_path,s,records)


def test_invalid_mcss_rejected(tmp_path):
    s=spec()
    df=dataframe(s=s)
    df.loc[1,'time_mcss']=12
    p=tmp_path/'x.csv'
    df.to_csv(p,index=False)
    with pytest.raises(ValueError,match='reloj'):
        check_run_csv(p,s,'glauber',-3.,'standard',stable_seed(s['seed'],'glauber','standard',-3.))


def test_b6_integrated_campaign_is_complete_and_untampered():
    parent=ROOT/'results'/'practica_cierre'
    campaigns=sorted(parent.glob('*_barrido_H_b6_*'))
    if not campaigns:
        pytest.skip('No se adjunto una campaña B6 en el paquete')
    for f in campaigns:
        assert json.loads((f/'ESTADO.json').read_text())['status']=='PASS'
        meta=json.loads((f/'MANIFEST_DATOS_B6.json').read_text())
        assert len(meta['records'])==2*len(meta['spec']['fields'])*len(meta['spec']['dynamics'])
        assert len(analyze_records(f,meta['spec'],meta['records']))==len(meta['spec']['fields'])*len(meta['spec']['dynamics'])


def test_all_censored_generates_diagnostics_but_not_misleading_means(tmp_path):
    from scripts.practica_cierre.barrido_campo_b6 import render
    s=spec()
    rows=[]
    for h in s['fields']:
        rows.append({'dynamics':'glauber','H':h,'J':1.,'abs_H_over_J':abs(h),
                     'censored_standard':3,'censored_nfold':3,'escaped_standard':0,'escaped_nfold':0,
                     'n_standard':3,'n_nfold':3, 'mean_standard_mcss':None,'mean_nfold_mcss':None,
                     'mean_standard_ci_low':None,'mean_standard_ci_high':None,
                     'mean_nfold_ci_low':None,'mean_nfold_ci_high':None,
                     'ratio_nfold_standard':None,'ratio_ci_low':None,'ratio_ci_high':None})
    imgs=render(pd.DataFrame(rows),tmp_path/'figures',s)
    assert len(imgs)==4
    assert all(f.is_file() and f.stat().st_size>0 for f in imgs)


def test_manifest_rejects_path_traversal(tmp_path):
    s=spec()
    records=[{'dynamics':'glauber','H':-3.,'algorithm':'standard','seed':stable_seed(123,'glauber','standard',-3.),
              'path':'datos_nuevos/../../release/release_manifest.csv','sha256':'INVALID'}]
    with pytest.raises(ValueError,match='Ruta de datos no permitida'):
        analyze_records(tmp_path,s,records)
