"""Prueba de contrato B7 sintético sin necesitar simuladores pesados."""
import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from scripts.practica_cierre import inconclusos_b7 as b
from scripts.practica_cierre.validar_baseline import sha256


def test_contrato_archivos_hash_y_analysis(tmp_path):
    case='glauber_0p8'
    spec={'cases':[case],'runs_frio':5,'runs_templado':5,'seed':2026111507,
          'bootstrap':240,'max_attempts':100000000,'L':32,'J':1.,'H':-.75,
          'margin':[.95,1.05],'perfil':'test'}
    source=tmp_path/'source';(source/'datos_nuevos').mkdir(parents=True)
    records=[]
    for algo in b.ALGOS:
        seed=b.case_seed(spec['seed'],case,algo)
        data=b.verify_historical(b.ROOT,case,algo).iloc[:5].copy()
        data['seed']=seed
        data['stream']=np.arange(1,6)
        data['run']=np.arange(5)
        p=source/'datos_nuevos'/f'{case}_{algo}.csv'
        data.to_csv(p,index=False)
        records.append({'case':case,'algorithm':algo,
                        'path':p.relative_to(source).as_posix(),
                        'sha256':sha256(p),
                        'history_sha256':sha256(b.historical_path(b.ROOT,case,algo)),
                        'seed':seed,'runs':5})
    out=tmp_path/'output'
    summ,figs=b.analyze(source,b.ROOT,spec,records,out)
    assert len(summ)==3
    assert len(figs)==8
    assert (out/'B7_INFORME.md').is_file()
    assert set(summ.group)=={'HISTORICO','SOLO_NUEVOS','COMBINADO'}
    # Ni una regeneración admite manipulación de hashes.
    records[0]['sha256']='0'*64
    with pytest.raises(ValueError,match='alterados'):
        b.collect_source(source,spec,records,b.ROOT)
    # Ni una regeneración admite rutas que escapen de la campaña.
    records[0]['sha256']=sha256(source/records[0]['path'])
    records[0]['path']='datos_nuevos/../../secreto.csv'
    with pytest.raises(ValueError,match='Ruta'):
        b.collect_source(source,spec,records,b.ROOT)
