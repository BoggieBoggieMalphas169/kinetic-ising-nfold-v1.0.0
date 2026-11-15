"""Criterios de análisis B7, propiedades estadísticas y salvaguardas."""
import numpy as np
import pytest
from pathlib import Path
from scripts.practica_cierre import inconclusos_b7 as b


def test_historicos_reales():
    for case in b.CASE_BY_NAME:
        for algo in b.ALGOS:
            f=b.verify_historical(b.ROOT,case,algo)
            assert len(f)==(4000 if case=='glauber_0p9' else 150)
            assert (f.reached_M0==1).all()


def test_semillas_distintas_de_la_referencia():
    for case in b.CASE_BY_NAME:
        for algo in b.ALGOS:
            x=b.case_seed(2026111507,case,algo)
            assert x not in (30260948,50260986)
            assert x!=b.case_seed(2026111508,case,algo)
    assert b.case_seed(4,'glauber_0p8','standard')!=b.case_seed(4,'glauber_0p8','nfold')


def test_decision_equivalencia_nunca_por_centro():
    assert b.decide(.97,1.03)=='PASS'
    assert b.decide(.93,1.04)=='INCONCLUSIVE'
    assert b.decide(1.06,1.08)=='FAIL'
    assert b.decide(.84,.94)=='FAIL'
    assert b.decide(.96,1.06)=='INCONCLUSIVE'


def test_bootstrap_reproducible_y_razon():
    a=np.full(300,3.)
    lo,hi=b.ci_ratio(a,a.copy(),123,700)
    assert lo<=1<=hi
    assert (lo,hi)==b.ci_ratio(a,a.copy(),123,700)
    o=b.compare(a,a,700,123)
    assert o['R_tau']==pytest.approx(1)
    assert o['status']=='PASS'


def test_censura_no_determina_media():
    a=np.array([1.,2.,3.]); bb=np.array([1.,2.,3.])
    row=b.compare(a,bb,400,123,allowed=False)
    assert row['status']=='CENSURADO_NO_EVALUABLE'
    assert row['R_tau'] is None


def test_diseno_inmutable_y_casos_invalidos():
    p={'cases':['glauber_0p8'],'runs_frio':2,'runs_templado':2,'seed':3,
       'bootstrap':200,'max_attempts':100,'L':32,'J':1.,'H':-.75,'margin':[.95,1.05]}
    b.validate_spec(p)
    for k,v in [('L',16),('H',-3.),('margin',[.90,1.10]),('runs_frio',1),
                ('bootstrap',50),('cases',['glauber_0p8','glauber_0p8'])]:
        invalid={**p,k:v}
        with pytest.raises(ValueError):b.validate_spec(invalid)


def test_rutas_historicas_solo_originales():
    for case in b.CASE_BY_NAME:
        for algo in b.ALGOS:
            assert b.historical_path(b.ROOT,case,algo).exists()


def test_acepta_tiempos_independientes_en_mcss():
    assert b.L==32 and b.H==-0.75
    assert b.CASE_BY_NAME['metropolis_0p8'][1:] == ('metropolis',.8)


def test_kaplan_meier_con_censura_y_empates():
    tt,ss=b.kaplan_meier(np.array([1.,2.,2.,3.]),np.array([1,1,0,0],bool))
    assert np.allclose(tt,[1.,2.,3.])
    assert np.allclose(ss,[.75,.5,.5])
    xx,yy=b.kaplan_meier(np.array([1.,2.,3.]),np.array([1,1,1],bool))
    assert np.allclose(yy,[2/3,1/3,0])
    with pytest.raises(ValueError):b.kaplan_meier(np.array([1.,2.]),np.array([True]))
