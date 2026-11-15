"""Bloque 8: auditoria de la practica y sintesis cientifica, sin simular ni editar originales.

Uso: python -m scripts.practica_cierre.cierre_b8 [--tests]
Las nuevas salidas van a results/practica_cierre/<ID>_cierre_b8_*/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .validar_baseline import ROOT, SNAPSHOT, create_run_dir, manifest_state, sha256

B6_NAME = '20261115T184817220253Z_barrido_H_b6_6faf2686'
B7_NAME = '20261115T190914332062Z_inconclusos_b7_5e580c44'
B2_NAME = '20261115T173651042286Z_nivel2_d666373c'
B4_NAME = '20261115T181308575882Z_visualizacion_b4_f5e65aa6'
B5_NAME = '20261115T183332938803Z_animaciones_b5_1d4a204d'


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def close(a: float, b: float, message: str, *, atol=1.e-7, rtol=1.e-8):
    require(bool(np.isclose(a, b, atol=atol, rtol=rtol)), f'{message}: {a} != {b}')


def safe_record_path(parent: Path, rel: str) -> Path:
    path = (parent / rel).resolve()
    require(path.is_relative_to(parent.resolve()) and path.is_file(), f'Ruta invalida: {rel}')
    return path


def check_rows(rows: list[dict], *, algo: str, dyn: str, T: float, H: float, L: int, seed: int | None = None):
    seen = set()
    require(rows, 'No se encontraron realizaciones')
    times = []
    cens = 0
    for i, x in enumerate(rows):
        require(x['algorithm'] == algo and x['dynamics'] == dyn, f'Algoritmo/dinamica no coinciden: fila {i}')
        require(int(x['L']) == L and int(x['N']) == L*L, f'Tamano de red incorrecto fila {i}')
        close(float(x['T']), T, 'Temperatura CSV')
        close(float(x['H']), H, 'Campo CSV')
        close(float(x['J']), 1., 'Acoplo CSV')
        if seed is not None:
            require(int(x['seed']) == seed, 'Semilla incoherente con manifiesto')
        attempt = float(x['time_attempts'])
        tm = float(x['time_mcss'])
        close(attempt/(L*L), tm, 'MCSS != intentos/N', atol=1e-9)
        require(attempt >= 0 and np.isfinite(tm), 'Tiempo negativo/no finito')
        key = (int(x['seed']), int(x['stream']))
        require(key not in seen, f'Semilla y stream duplicados: {key}')
        seen.add(key)
        reached = int(x['reached_M0']) == 1
        if reached:
            require(int(x['final_M']) == 0, 'Escape notificado sin M=0')
        else:
            cens += 1
        times.append(tm)
    return {'n':len(rows), 'censored':cens,'mean':float(np.mean(times)),'times':np.array(times)}


def collect_b6(root: Path):
    folder = root/'results'/'practica_cierre'/B6_NAME
    manifest = json.loads((folder/'MANIFEST_DATOS_B6.json').read_text(encoding='utf-8'))
    spec = manifest['spec']
    require(len(manifest['records']) == 24, 'B6 no contiene 24 CSV')
    data = {}
    for r in manifest['records']:
        f = safe_record_path(folder, r['path'])
        require(sha256(f) == r['sha256'], f'Hash B6 no coincide: {f.name}')
        d = check_rows(read_csv(f), algo=r['algorithm'], dyn=r['dynamics'], T=spec['T'], H=float(r['H']), L=spec['L'], seed=int(r['seed']))
        require(d['n'] == spec['runs'], 'N realizaciones B6 incorrecto')
        key = (r['dynamics'], float(r['H']), r['algorithm'])
        require(key not in data,'Registro B6 duplicado')
        data[key] = d
    summary = read_csv(folder/'resumen_barrido_H.csv')
    require(len(summary) == 12,'B6 no tiene 12 comparaciones')
    for row in summary:
        key = (row['dynamics'],float(row['H']))
        a,b = (data[key+(alg,)] for alg in ('standard','nfold'))
        require(a['censored'] == int(row['censored_standard']) and b['censored'] == int(row['censored_nfold']), 'Censura B6 no coincide')
        require(a['n'] == int(row['n_standard']) and b['n'] == int(row['n_nfold']), 'Conteo B6 no coincide')
        if a['censored'] == b['censored'] == 0:
            close(a['mean'],float(row['mean_standard_mcss']),'Media B6 Standard')
            close(b['mean'],float(row['mean_nfold_mcss']),'Media B6 n-fold')
            close(b['mean']/a['mean'],float(row['ratio_nfold_standard']),'R B6')
        require(row['equivalence_status'] == 'PASS' and float(row['ratio_ci_low']) >= .95 and float(row['ratio_ci_high']) <= 1.05, 'Criterio B6 no PASS')
    return spec, summary, data


def collect_b7(root: Path):
    folder = root/'results'/'practica_cierre'/B7_NAME
    manifest = json.loads((folder/'B7_MANIFEST_DATOS.json').read_text(encoding='utf-8'))
    spec = manifest['spec']
    require(len(manifest['records']) == 6, 'B7 no tiene seis CSV')
    require(spec['margin'] == [0.95,1.05], 'Margen B7 alterado')
    data={}
    for record in manifest['records']:
        f=safe_record_path(folder,record['path'])
        require(sha256(f)==record['sha256'],f'Hash B7 no coincide: {f.name}')
        dyn,Tlabel=record['case'].split('_')
        T=float(Tlabel.replace('p','.'))
        r=check_rows(read_csv(f),algo=record['algorithm'],dyn=dyn,T=T,H=spec['H'],L=spec['L'],seed=int(record['seed']))
        require(r['n']==record['runs'],'N realizaciones B7 incorrecto')
        require(r['censored']==0,'Censura inesperada B7, revisar medias')
        key=(record['case'],record['algorithm'])
        data[key]=r
        historic = safe_record_path(root,record['history_path'])
        require(sha256(historic)==record['history_sha256'],f'Historial B7 alterado: {historic.name}')
    table = read_csv(folder/'B7_RESUMEN_COMPARACIONES.csv')
    require(len(table)==9,'B7 no contiene 9 comparaciones')
    expected={'glauber_0p8':'PASS','glauber_0p9':'PASS','metropolis_0p8':'INCONCLUSIVE'}
    for case,status in expected.items():
        row=next(x for x in table if x['case']==case and x['group']=='SOLO_NUEVOS')
        a=data[(case,'standard')]
        b=data[(case,'nfold')]
        require(int(row['n_standard'])==a['n'] and int(row['n_nfold'])==b['n'],'N B7 no coincide')
        close(a['mean'],float(row['mean_standard_mcss']),'Media B7 Standard')
        close(b['mean'],float(row['mean_nfold_mcss']),'Media B7 n-fold')
        close(b['mean']/a['mean'],float(row['R_tau']),'R B7')
        lo,hi=float(row['ci95_low']),float(row['ci95_high'])
        in_margin = lo>=.95 and hi<=1.05
        require(row['status']==status and (in_margin==(status=='PASS')),'Clasificacion B7 incorrecta')
    return spec,table,data


def png_pdf(fig, path:Path):
    fig.savefig(path.with_suffix('.png'),dpi=185,bbox_inches='tight')
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight')
    plt.close(fig)


def make_figures(out:Path,b6_rows:list[dict],b7_rows:list[dict],b7_data:dict):
    dest=out/'figuras_b8';dest.mkdir()
    # Figure 1: B7 three new-only ratios with uncertainty
    cases=['glauber_0p8','glauber_0p9','metropolis_0p8']
    rows=[next(x for x in b7_rows if x['case']==c and x['group']=='SOLO_NUEVOS') for c in cases]
    means=[float(x['R_tau']) for x in rows]
    lows=[float(x['ci95_low']) for x in rows]; highs=[float(x['ci95_high']) for x in rows]
    fig,ax=plt.subplots(figsize=(8,4.4)); ys=np.arange(3)[::-1]
    ax.axvspan(.95,1.05,alpha=.11,label='Margen de equivalencia')
    ax.axvline(1,ls=':',color='gray')
    ax.errorbar(means,ys,xerr=[np.array(means)-lows,np.array(highs)-means],fmt='o',capsize=4,color='#23527c')
    ax.set_yticks(ys,['Glauber, T/J=0.8','Glauber, T/J=0.9','Metropolis, T/J=0.8'])
    ax.set_xlabel('R = tiempo medio n-fold / Standard (IC bootstrap 95 %)')
    ax.set_title('B7: extension de los puntos historicamente inconclusos')
    ax.grid(axis='x',alpha=.25); ax.legend(loc='lower right')
    fig.tight_layout(); png_pdf(fig,dest/'B8_F01_equivalencia_B7')
    # Figure 2: B6, two dynamics; averages per field
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.4),sharey=True)
    for ax,dyn in zip(axes,('glauber','metropolis')):
        rows=sorted((x for x in b6_rows if x['dynamics']==dyn),key=lambda x:float(x['abs_H_over_J']))
        x=[float(z['abs_H_over_J']) for z in rows]
        for alg,caption in [('standard','Standard'),('nfold','n-fold')]:
            vals=[float(z[f'mean_{alg}_mcss']) for z in rows]
            lo=[float(z[f'mean_{alg}_ci_low']) for z in rows]
            hi=[float(z[f'mean_{alg}_ci_high']) for z in rows]
            ax.errorbar(x,vals,yerr=[np.array(vals)-lo,np.array(hi)-vals],fmt='o-',capsize=2,label=caption)
        ax.set_yscale('log');ax.set_title(dyn.capitalize());ax.set_xlabel('|H|/J');ax.grid(alpha=.25);ax.legend()
    axes[0].set_ylabel('Tiempo medio de escape (MCSS)')
    fig.suptitle('B6: efecto del campo, L=32 y T/J=1.5');fig.tight_layout();png_pdf(fig,dest/'B8_F02_tiempo_escape_campo_B6')
    # Figure 3: survival/ECDF Metropolis new-only, clearly independent realisations
    a=b7_data[('metropolis_0p8','standard')]['times'];b=b7_data[('metropolis_0p8','nfold')]['times']
    fig,ax=plt.subplots(figsize=(8.5,4.8))
    for sample,label in [(a,'Standard - Metropolis'),(b,'n-fold - Metropolis')]:
        xs=np.sort(sample);s=1-np.arange(1,len(xs)+1)/len(xs)
        ax.step(xs,s,where='post',label=label)
    ax.set_xscale('log');ax.set_yscale('linear');ax.set_xlabel('Tiempo de escape (MCSS, escala log)');ax.set_ylabel('Supervivencia empirica')
    ax.set_title('B7: caso inconcluso Metropolis, T/J=0.8, H/J=-0.75')
    ax.grid(alpha=.25);ax.legend();fig.tight_layout();png_pdf(fig,dest/'B8_F03_supervivencia_metropolis')
    return sorted(dest.iterdir())


def external_check(root:Path, out:Path, name:str, command:list[str],cwd:Path|None=None):
    completed=subprocess.run(command,cwd=cwd or root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','MPLBACKEND':'Agg'},check=False)
    (out/'logs').mkdir(exist_ok=True)
    log=(out/'logs'/f'{name}.log');log.write_text(completed.stdout,encoding='utf-8')
    if completed.returncode != 0:
        raise RuntimeError(f'{name} FALLÓ (exit={completed.returncode}). Ultimas lineas:\n'+ '\n'.join(completed.stdout.splitlines()[-20:]))
    return {'status':'PASS','exit_code':completed.returncode,'log':str(log.relative_to(out))}


def audit(root:Path, *, run_tests:bool):
    out=create_run_dir(root,'cierre_b8')
    status={'status':'failed','timestamp_utc':datetime.now(timezone.utc).isoformat(),'snapshot':SNAPSHOT,'checks':{},'statistics':{},'artifacts':[],'limitations':[],'tests_executed':bool(run_tests)}
    try:
        before=manifest_state(root)
        require(len(before)==375,'Manifest historico no tiene 374 entradas + fichero manifiesto')
        status['checks']['original_manifest_file_count'] = len(before)-1
        status['checks']['release'] = external_check(root,out,'release_check',[sys.executable,'scripts/release_check.py','--verify-frozen'])
        status['checks']['snapshot'] = external_check(root,out,'snapshot_check',[sys.executable,'-m','scripts.analysis.build_quality_snapshot','--verify',f'results/snapshots/{SNAPSHOT}'])
        b6_spec,b6_rows,b6_data=collect_b6(root)
        b7_spec,b7_rows,b7_data=collect_b7(root)
        status['checks']['b6_24_raw_csv'] = 'PASS (SHA256, schema, time, means and ratios)'
        status['checks']['b7_6_raw_csv'] = 'PASS (SHA256, schema, time, means and ratios)'
        status['statistics']['b6']={'runs':sum(v['n'] for v in b6_data.values()),'pairs':len(b6_rows),'pass':sum(r['equivalence_status']=='PASS' for r in b6_rows),'censored':sum(v['censored'] for v in b6_data.values())}
        status['statistics']['b7']={'new_runs':sum(v['n'] for v in b7_data.values()),'primary_pass':sum(r['status']=='PASS' for r in b7_rows if r['group']=='SOLO_NUEVOS'),'primary_inconclusive':sum(r['status']=='INCONCLUSIVE' for r in b7_rows if r['group']=='SOLO_NUEVOS'),'censored':sum(v['censored'] for v in b7_data.values())}
        coverage={
            'historic_figures':len(list((root/'figures/final').glob('*.png'))),
            'level2_figures':len(list((root/'results/practica_cierre'/B2_NAME).rglob('*.png'))),
            'b4_figures':len(list((root/'results/practica_cierre'/B4_NAME).rglob('*.png'))),
            'b5_mp4':len(list((root/'results/practica_cierre'/B5_NAME).rglob('*.mp4'))),
            'b5_gif':len(list((root/'results/practica_cierre'/B5_NAME).rglob('*.gif'))),
        }
        require(coverage['historic_figures']==6 and coverage['level2_figures']==22 and coverage['b4_figures']==11,'Numero de figuras B2/B4/historico inesperado')
        require(coverage['b5_mp4']==6 and coverage['b5_gif']==6,'No se encontraron los seis pares GIF/MP4')
        status['statistics']['coverage']=coverage
        status['checks']['figure_media_inventory']='PASS'
        if run_tests:
            import tempfile
            with tempfile.TemporaryDirectory(prefix='ising_b8_cmake_') as build:
                status['checks']['cmake'] = external_check(root,out,'cmake',[ 'cmake','-S',str(root),'-B',build,'-DCMAKE_BUILD_TYPE=Release'])
                status['checks']['build'] = external_check(root,out,'build',['cmake','--build',build,'--config','Release','-j','2'])
                status['checks']['ctest'] = external_check(root,out,'ctest',['ctest','--test-dir',build,'--output-on-failure'])
            with tempfile.TemporaryDirectory(prefix='ising_b8_tracing_') as tracing_build:
                status['checks']['cmake_tracing'] = external_check(root,out,'cmake_tracing',['cmake','-S',str(root/'simulator'/'tracing'),'-B',tracing_build,'-DCMAKE_BUILD_TYPE=Release'])
                status['checks']['build_tracing'] = external_check(root,out,'build_tracing',['cmake','--build',tracing_build,'--config','Release','-j','2'])
                status['checks']['ctest_tracing'] = external_check(root,out,'ctest_tracing',['ctest','--test-dir',tracing_build,'--output-on-failure'])
            status['checks']['pytest'] = external_check(root,out,'pytest',[sys.executable,'-m','pytest','-q','-p','no:cacheprovider'])
        files=make_figures(out,b6_rows,b7_rows,b7_data)
        status['artifacts']=[str(p.relative_to(out)) for p in files]
        after=manifest_state(root)
        require(before==after,'El proceso ha alterado un archivo historico')
        status['checks']['historic_hashes_unchanged']='PASS'
        status['status']='passed'
        status['limitations']=['Metropolis T/J=0.8 permanece INCONCLUSIVE; no forzar PASS.',
         'KS no rechazar no demuestra identidad distribucional.',
         'La validacion local de PowerShell en Windows queda pendiente.',
         'Benchmarks exploratorios B6 no sustituyen un perfilado de CPU P07D/E.',
         'Los GIF presentan trayectorias individuales, no equivalencia punto a punto.']
    except Exception as exc:
        status['error']=str(exc)
    finally:
        (out/'ESTADO_B8.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
        doc=['# Bloque 8 - Auditoria reproducible','',f"**Estado de la auditoria:** `{status['status']}`",f"**Tests completos ejecutados:** `{status['tests_executed']}`",f"**Snapshot:** `{SNAPSHOT}`",'',
             '## Comprobaciones']
        for k,v in status['checks'].items():doc.append(f'- **{k}**: {v if isinstance(v,str) else (v.get("status") if isinstance(v,dict) else str(v))}')
        doc+=['','## Resultados']
        for k,v in status['statistics'].items():doc.append(f'- **{k}**: `{json.dumps(v,ensure_ascii=False)}`')
        doc+=['','## Restricciones y advertencias']+[f'- {x}' for x in status['limitations']]
        doc+=['','La etiqueta PASS de la auditoria significa consistencia documental y tecnica; NO equivale a que todas las comparaciones fisicas tengan PASS.','']
        if status.get('error'):doc+=['## ERROR',status['error']]
        (out/'INFORME_AUDITORIA_B8.md').write_text('\n'.join(doc)+'\n',encoding='utf-8')
    print(json.dumps({'status':status['status'],'folder':str(out),'checks':status['checks'],'stats':status['statistics'],'error':status.get('error')},indent=2,ensure_ascii=False))
    return 0 if status['status']=='passed' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tests',action='store_true',help='Ejecutar CMake/CTest y pytest (ademas de hashes y cifras)')
    args=p.parse_args()
    return audit(ROOT,run_tests=args.tests)


if __name__=='__main__':
    raise SystemExit(main())
