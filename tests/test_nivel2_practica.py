"""Tests de contratos de los CSV y de las distribuciones de nivel 2."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.practica_cierre.nivel2 import (
    bootstrap_log_mean_ci,ecdf_difference,empirical_cdf,load_runs,select_pair,survival,verify_frozen_integrity,
)


def _write_pair(raw:Path, *, censored=False):
    raw.mkdir(parents=True,exist_ok=True)
    for algo in ['standard','nfold']:
        df=pd.DataFrame([{'run':i,'L':8,'T':1.5,'J':1,'H':-0.75,
                          'dynamics':'glauber','algorithm':algo,'time_mcss':float(i+1),
                          'reached_M0':0 if (censored and i==1) else 1,
                          'cpu_seconds':0.002,'seed':42,'stream':i+1} for i in range(3)])
        df.to_csv(raw/f'{algo}.csv',index=False)


def test_ecdf_monotonic_and_exact_difference():
    a=np.array([1,2,2,4.]); b=np.array([2,3,3,5.])
    xs,fs=empirical_cdf(a)
    assert np.all(np.diff(xs)>0)
    assert np.all(np.diff(fs)>=0)
    np.testing.assert_allclose(fs,[.25,.75,1.])
    grid,diff=ecdf_difference(a,b)
    assert diff[np.where(grid==1)[0][0]]==pytest.approx(-.25)
    np.testing.assert_allclose(diff[-1],0)
    tx,s=survival(a)
    assert s[0]==1 and s[-1]==0 and np.all(np.diff(s)<=0)


def test_csv_groups_pair(tmp_path):
    _write_pair(tmp_path)
    loaded,sources=load_runs(tmp_path)
    a,b=select_pair(loaded,'glauber',-.75,1.5,L=8)
    np.testing.assert_allclose(a,b)
    assert len(sources)==2


def test_censored_fail_closed(tmp_path):
    _write_pair(tmp_path,censored=True)
    with pytest.raises(ValueError,match='Kaplan-Meier'):
        load_runs(tmp_path)


def test_duplicate_group_fail_closed(tmp_path):
    _write_pair(tmp_path)
    (tmp_path/'copy.csv').write_bytes((tmp_path/'standard.csv').read_bytes())
    with pytest.raises(ValueError,match='Duplicidad'):
        load_runs(tmp_path)


def test_bootstrap_repeatable_and_positive():
    v=np.array([2.,5.,7.,8.,10.,11.])
    a=bootstrap_log_mean_ci(v,seed=2026,replicates=128)
    assert a==bootstrap_log_mean_ci(v,seed=2026,replicates=128)
    assert a[0]<np.log(v.mean())<a[1]


def test_incorrect_historical_hash_detected(tmp_path):
    import csv
    from scripts.practica_cierre.validar_baseline import manifest_state,sha256
    (tmp_path/'release').mkdir()
    (tmp_path/'original.csv').write_text('a,b\n1,2\n')
    with (tmp_path/'release/release_manifest.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['path','size_bytes','sha256'])
        w.writerow(['original.csv',4,sha256(tmp_path/'original.csv')])
    state=manifest_state(tmp_path)
    verify_frozen_integrity(tmp_path,state)
    (tmp_path/'original.csv').write_text('a,b\n1,3\n')
    with pytest.raises(ValueError,match='Fuente historica alterada'):
        verify_frozen_integrity(tmp_path,manifest_state(tmp_path))
