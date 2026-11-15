"""Tests del bloque 8. No crean datos de simulacion ni cambian el baseline."""
import json
import pytest
from pathlib import Path
from scripts.practica_cierre.cierre_b8 import (
    ROOT, B6_NAME, B7_NAME, collect_b6, collect_b7, check_rows,
    safe_record_path, read_csv, require,
)


def test_b6_contrato_y_8400_trayectorias():
    spec, summary, data=collect_b6(ROOT)
    assert spec['L']==32 and spec['T']==1.5
    assert len(summary)==12 and len(data)==24
    assert sum(x['n'] for x in data.values())==8400
    assert sum(x['censored'] for x in data.values())==0


def test_b7_contrato_y_28000_trayectorias():
    spec, summary, data=collect_b7(ROOT)
    assert spec['margin']==[.95,1.05]
    assert len(data)==6 and len(summary)==9
    assert sum(x['n'] for x in data.values())==28000


def test_b7_conclusion_fisica_no_forzada():
    _,summary,_=collect_b7(ROOT)
    actual={x['case']:x['status'] for x in summary if x['group']=='SOLO_NUEVOS'}
    assert actual=={'glauber_0p8':'PASS','glauber_0p9':'PASS','metropolis_0p8':'INCONCLUSIVE'}


def test_registro_fuera_de_directorio_rechazado(tmp_path):
    f=tmp_path.parent/'externo.csv'
    f.write_text('algo\n',encoding='utf-8')
    try:
        with pytest.raises(ValueError,match='Ruta invalida'):
            safe_record_path(tmp_path,'../externo.csv')
    finally: f.unlink()


def test_csv_mcss_no_coherente_rechazado():
    d=ROOT/'results'/'practica_cierre'/B7_NAME/'datos_nuevos/glauber_0p8_standard.csv'
    rows=read_csv(d)
    bad=dict(rows[0]);bad['time_mcss']='-42'
    with pytest.raises(ValueError,match='MCSS'):
        check_rows([bad],algo='standard',dyn='glauber',T=.8,H=-.75,L=32,seed=int(bad['seed']))


def test_csv_semilla_stream_duplicados_rechazado():
    d=ROOT/'results'/'practica_cierre'/B7_NAME/'datos_nuevos/glauber_0p8_standard.csv'
    rows=read_csv(d)
    with pytest.raises(ValueError,match='duplicados'):
        check_rows([rows[0],rows[0]],algo='standard',dyn='glauber',T=.8,H=-.75,L=32,seed=int(rows[0]['seed']))


def test_b7_manifiesto_de_datos_precargado():
    d=ROOT/'results'/'practica_cierre'/B7_NAME
    meta=json.loads((d/'B7_MANIFEST_DATOS.json').read_text(encoding='utf-8'))
    assert meta['spec']['runs_frio']==3500
    assert meta['spec']['runs_templado']==7000
    assert meta['spec']['analysis_policy'].startswith('fixed sample')
