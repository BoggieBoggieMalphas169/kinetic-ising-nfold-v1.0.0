"""Bloque 7: extensión prospectiva de los tres casos inconclusos históricos.

No altera el motor C ni el snapshot P08. Diseños cerrados, sin parada opcional
por significación; resultados SOLO_NUEVOS (primario), HISTORICO y COMBINADO
(secundario) siempre se muestran por separado.

Uso:
 python -m scripts.practica_cierre.inconclusos_b7 generar --perfil piloto
 python -m scripts.practica_cierre.inconclusos_b7 generar --perfil practica
 python -m scripts.practica_cierre.inconclusos_b7 analizar --directorio results/practica_cierre/...
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from .validar_baseline import ROOT, SNAPSHOT, manifest_state, create_run_dir, sha256
from .nivel2 import verify_frozen_integrity
from .barrido_campo_b6 import build_engines, check_run_csv, compute_measured, write_manifest, utc_now

CASES = (
    ('glauber_0p8', 'glauber', 0.8),
    ('glauber_0p9', 'glauber', 0.9),
    ('metropolis_0p8', 'metropolis', 0.8),
)
CASE_BY_NAME = {c[0]:c for c in CASES}
ALGOS = ('standard', 'nfold')
L, J, H = 32, 1., -0.75
HIST_BASE = Path('simulator/results/temperature_sweep/raw')
MARGIN = (.95, 1.05)
REQUIRED_RAW = {'run','L','N','T','J','H','dynamics','algorithm','seed','stream',
                'time_attempts','time_mcss','events','reached_M0','final_M'}


def case_seed(global_seed: int, case: str, algo: str) -> int:
    tag = f'B7|20261115|{global_seed}|{case}|{algo}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(tag).digest()[:8], 'little') & ((1 << 63)-1)


def bootstrap_seed(global_seed: int, case: str, group: str) -> int:
    return case_seed(global_seed, case, f'bootstrap_{group}')


def historical_path(root: Path, case: str, algo: str) -> Path:
    _,dyn,t = CASE_BY_NAME[case]
    tt = 'Tp0p8' if t == .8 else 'Tp0p9'
    return root/HIST_BASE/f'{tt}_{algo}_{dyn}_Hm0p75.csv'


def design(args) -> dict:
    if args.perfil=='piloto':
        cold, warm = 30, 80
    else:
        cold, warm = 3500, 7000
    cold = args.runs_frio if args.runs_frio is not None else cold
    warm = args.runs_templado if args.runs_templado is not None else warm
    cases = [x.strip() for x in args.casos.split(',')]
    spec={'perfil':args.perfil,'cases':cases,'runs_frio':cold,'runs_templado':warm,
          'seed':args.seed,'bootstrap':args.bootstrap,'max_attempts':args.max_attempts,
          'L':L,'J':J,'H':H,'margin':list(MARGIN),
          'analysis_policy':'fixed sample; new-only primary; historic and pooled secondary; no optional stopping'}
    validate_spec(spec)
    return spec


def validate_spec(spec: dict):
    if not spec['cases'] or any(s not in CASE_BY_NAME for s in spec['cases']) or len(set(spec['cases']))!=len(spec['cases']):
        raise ValueError('Selección de casos inválida/repetida')
    if not all(isinstance(spec[k],int) and spec[k]>=2 for k in ('runs_frio','runs_templado')):
        raise ValueError('Se requieren al menos dos réplicas nuevas por algoritmo')
    if spec['seed']<0 or spec['seed']>=2**63:
        raise ValueError('Semilla fuera de rango')
    if spec['bootstrap'] < 200 or spec['bootstrap'] > 25000:
        raise ValueError('Bootstrap debe estar entre 200 y 25000')
    if not 1 <= spec['max_attempts'] <= 2**63-1:
        raise ValueError('Horizonte de intentos inválido')
    if (spec['L'],float(spec['J']),float(spec['H']))!=(L,J,H):
        raise ValueError('No cambiar los parámetros físicos de los casos históricos')
    if list(spec['margin']) != list(MARGIN):
        raise ValueError('El margen de equivalencia no puede alterarse retrospectivamente')


def runs_for(spec:dict,case:str) -> int:
    return spec['runs_templado'] if CASE_BY_NAME[case][2]==.9 else spec['runs_frio']


def verify_historical(root:Path,case:str,algo:str):
    p=historical_path(root,case,algo)
    if not p.is_file():raise FileNotFoundError(f'Datos históricos ausentes: {p}')
    f=pd.read_csv(p)
    if not REQUIRED_RAW.issubset(f.columns):raise ValueError('Columnas históricas no válidas')
    _,dyn,t=CASE_BY_NAME[case]
    for key,value in [('L',L),('N',L**2),('T',t),('J',J),('H',H)]:
        if not np.allclose(f[key],value,rtol=0,atol=1e-12):raise ValueError(f'{p}: parámetro {key} distinto')
    if not ((f['algorithm']==algo)&(f['dynamics']==dyn)).all():raise ValueError('Histórico mal etiquetado')
    if not np.isfinite(f.time_mcss.to_numpy(float)).all() or (f.time_mcss<=0).any():
        raise ValueError('Tiempos históricos inválidos')
    if not np.allclose(f.time_attempts/(L**2),f.time_mcss,rtol=2e-13,atol=1e-12):
        raise ValueError('Reloj histórico inconsistente')
    if not ((f.reached_M0==1)&(f.final_M==0)).all():
        raise ValueError('Histórico tiene censura/escapes inválidos; no se puede combinar sin reanalizar')
    if f.duplicated(['seed','stream']).any() or list(f['run'])!=list(range(len(f))):
        raise ValueError('Streams históricos duplicados')
    return f


def expected(spec):
    return [(case,algo) for case in spec['cases'] for algo in ALGOS]


def collect_source(source:Path,spec:dict,records:list[dict],root:Path):
    if len(records)!=len(expected(spec)) or {(r['case'],r['algorithm']) for r in records}!=set(expected(spec)):
        raise ValueError('Manifest incompleto/repetido')
    raw={}
    historical={}
    for case,algo in expected(spec):
        r=next(q for q in records if (q['case'],q['algorithm'])==(case,algo))
        rel=Path(r['path'])
        if rel.is_absolute() or '..' in rel.parts or len(rel.parts)!=2 or rel.parts[0]!='datos_nuevos' or rel.suffix!='.csv':
            raise ValueError('Ruta de CSV manipulada')
        p=source/rel
        if not p.is_file() or sha256(p)!=r['sha256']:
            raise ValueError(f'Datos nuevos alterados: {p}')
        _,dyn,t=CASE_BY_NAME[case]
        seed=case_seed(spec['seed'],case,algo)
        if r['seed']!=seed or r['runs']!=runs_for(spec,case):raise ValueError('Diseño/seed no coincide')
        b6spec={'L':L,'T':t,'J':J,'H':H,'runs':runs_for(spec,case),'max_attempts':spec['max_attempts']}
        f=check_run_csv(p,b6spec,dyn,H,algo,seed)
        arr,ev=compute_measured(f,b6spec,algo)
        raw[(case,algo)]=(arr,ev,f)
        hf=verify_historical(root,case,algo)
        if seed in set(hf['seed'].astype(int)):raise ValueError('Semilla histórica reutilizada')
        relhist=historical_path(root,case,algo).relative_to(root).as_posix()
        if r['history_sha256']!=sha256(root/relhist):
            raise ValueError('El archivo histórico ha cambiado después de generar la campaña')
        historical[(case,algo)]=hf.time_mcss.to_numpy(float)
    return raw,historical


def ci_ratio(a:np.ndarray,b:np.ndarray,seed:int,nboot:int):
    rng=np.random.default_rng(seed)
    ratio=np.empty(nboot,float)
    start=0
    while start<nboot:
        count=min(24,nboot-start)
        means_a=np.mean(a[rng.integers(0,len(a),size=(count,len(a)))],axis=1)
        means_b=np.mean(b[rng.integers(0,len(b),size=(count,len(b)))],axis=1)
        ratio[start:start+count]=means_b/means_a
        start+=count
    return tuple(float(v) for v in np.quantile(ratio,[.025,.975]))


def kaplan_meier(times:np.ndarray, events:np.ndarray):
    """Kaplan-Meier para censura derecha; empates: eventos antes de censuras."""
    times=np.asarray(times,dtype=float)
    events=np.asarray(events,dtype=bool)
    if times.ndim!=1 or events.shape!=times.shape or not len(times):
        raise ValueError('Muestra Kaplan-Meier vacía o mal alineada')
    if np.any(~np.isfinite(times)) or np.any(times<=0):
        raise ValueError('Tiempos Kaplan-Meier inválidos')
    order=np.argsort(times,kind='stable')
    x=times[order];e=events[order]
    t_unique,idx,count=np.unique(x,return_index=True,return_counts=True)
    s=1.
    vals=[]
    risk=len(x)
    for start,group_size in zip(idx,count):
        d=int(e[start:start+group_size].sum())
        if d:s *= 1.-d/risk
        vals.append(max(0.,s))
        risk-=int(group_size)
    return t_unique,np.asarray(vals)


def decide(low,high):
    if low>=MARGIN[0] and high<=MARGIN[1]:return 'PASS'
    if high<MARGIN[0] or low>MARGIN[1]:return 'FAIL'
    return 'INCONCLUSIVE'


def compare(a,b,bootstrap,seed,allowed=True):
    rec={'n_standard':len(a),'n_nfold':len(b),'mean_standard_mcss':None,
         'mean_nfold_mcss':None,'R_tau':None,'ci95_low':None,'ci95_high':None,
         'status':'CENSURADO_NO_EVALUABLE' if not allowed else 'INCONCLUSIVE',
         'ks_pvalue':None,'ks_statistic':None}
    if not allowed:return rec
    lo,hi=ci_ratio(a,b,seed,bootstrap)
    ks=ks_2samp(a,b,method='asymp')
    rec.update(mean_standard_mcss=float(np.mean(a)),mean_nfold_mcss=float(np.mean(b)),
               R_tau=float(np.mean(b)/np.mean(a)),ci95_low=lo,ci95_high=hi,
               status=decide(lo,hi),ks_pvalue=float(ks.pvalue),ks_statistic=float(ks.statistic))
    return rec


def analyze(source:Path,root:Path,spec:dict,records:list[dict],dest:Path):
    raw,historic=collect_source(source,spec,records,root)
    rows=[];all_data={}
    for case in spec['cases']:
        a,escape_a,_=raw[(case,'standard')];b,escape_b,_=raw[(case,'nfold')]
        old_a=historic[(case,'standard')];old_b=historic[(case,'nfold')]
        all_data[case]={'new_a':a,'new_b':b,'old_a':old_a,'old_b':old_b,
                        'esc_a':escape_a,'esc_b':escape_b}
        complete=bool(np.all(escape_a) and np.all(escape_b))
        for name,x,y,valid in [('HISTORICO',old_a,old_b,True),
                                ('SOLO_NUEVOS',a,b,complete),
                                ('COMBINADO',np.r_[old_a,a],np.r_[old_b,b],complete)]:
            d=compare(x,y,spec['bootstrap'],bootstrap_seed(spec['seed'],case,name),allowed=valid)
            d.update(case=case,rule=CASE_BY_NAME[case][1],T_over_J=CASE_BY_NAME[case][2],
                     H_over_J=H/J,group=name,new_escapes_standard=int(escape_a.sum()),
                     new_escapes_nfold=int(escape_b.sum()),
                     new_censored_standard=int(len(a)-escape_a.sum()),
                     new_censored_nfold=int(len(b)-escape_b.sum()),
                     baseline_snapshot=SNAPSHOT)
            rows.append(d)
    summary=pd.DataFrame(rows)
    # Contraste KS complementario, corrección Holm sólo en 3 pruebas SOLO_NUEVOS completas.
    pvals=summary.loc[(summary.group=='SOLO_NUEVOS') & summary.ks_pvalue.notna(),['case','ks_pvalue']]
    if len(pvals):
        pvals=pvals.sort_values('ks_pvalue')
        m=len(pvals);adjusted=np.maximum.accumulate([min(1.,(m-i)*p) for i,p in enumerate(pvals.ks_pvalue)])
        pm=dict(zip(pvals.case,adjusted));summary['ks_holm_p_new']=summary.apply(
            lambda z:pm.get(z['case'],np.nan) if z['group']=='SOLO_NUEVOS' else np.nan,axis=1)
    else:summary['ks_holm_p_new']=np.nan
    dest.mkdir(parents=True,exist_ok=True)
    summ=dest/'B7_RESUMEN_COMPARACIONES.csv'
    summary.to_csv(summ,index=False)
    figdir=dest/'figuras_b7';figdir.mkdir(exist_ok=False)
    figs=[]
    def save(fig,tag):
        for ext in ['png','pdf']:
            f=figdir/(tag+'.'+ext);fig.savefig(f,bbox_inches='tight',dpi=170);figs.append(f)
        plt.close(fig)
    # Ratio by case and provenance
    fig,ax=plt.subplots(figsize=(10,5.3))
    for j,(label,shift,marker) in enumerate([('HISTORICO',-.20,'s'),('SOLO_NUEVOS',0,'o'),('COMBINADO',.20,'D')]):
        rows0=summary[summary.group==label]
        good=rows0[rows0.ci95_low.notna()]
        xx=np.array([spec['cases'].index(c) for c in good.case])+shift
        yy=good.R_tau.to_numpy(float)
        if len(good):ax.errorbar(xx,yy,yerr=[yy-good.ci95_low.to_numpy(float),good.ci95_high.to_numpy(float)-yy],
                                fmt=marker,capsize=4,label=label)
    ax.axhspan(*MARGIN,color='0.83',alpha=.5,label='Margen [0.95,1.05]')
    ax.axhline(1,color='0.45',ls=':')
    ax.set_xticks(range(len(spec['cases'])),[s.replace('_',' ') for s in spec['cases']])
    ax.set(ylabel='R_tau = media n-fold / media Standard',title='B7: procedencia e incertidumbre de los casos históricos')
    ax.grid(alpha=.18);ax.legend();save(fig,'B7_01_Rtau_comparaciones')
    # Nonparametric survival, ECDF and log hist for complete ensembles; censor mark explicit.
    for case in spec['cases']:
        z=all_data[case]
        fig,axes=plt.subplots(1,2,figsize=(11.8,4.7))
        for arr,events,key,col in [(z['old_a'],np.ones(len(z['old_a']),bool),'Hist Standard','C0'),
                                    (z['old_b'],np.ones(len(z['old_b']),bool),'Hist n-fold','C1'),
                                    (z['new_a'],z['esc_a'],'Nuevo Standard','C2'),
                                    (z['new_b'],z['esc_b'],'Nuevo n-fold','C3')]:
            vv,surv=kaplan_meier(arr,events)
            axes[0].step(vv,surv,where='post',label=key,color=col,lw=1.2)
            axes[1].step(vv,1.-surv,where='post',label=key,color=col,lw=1.2)
        axes[0].set(xlabel='t (MCSS)',ylabel='S(t) Kaplan-Meier',ylim=(-.02,1.02),title='Supervivencia')
        axes[1].set(xlabel='t (MCSS)',ylabel='1 - S(t) Kaplan-Meier',ylim=(-.02,1.02),title='ECDF')
        for ax in axes:ax.set_xscale('log');ax.grid(alpha=.2);ax.legend(fontsize=8)
        if not (z['esc_a'].all() and z['esc_b'].all()):
            fig.suptitle('Nuevas trayectorias censuradas: estimador Kaplan-Meier; no se estiman medias')
        fig.tight_layout();save(fig,'B7_02_supervivencia_ECDF_'+case)
        fig,ax=plt.subplots(figsize=(8,4.8))
        for key,arr,esc in [('Standard',z['new_a'],z['esc_a']),('n-fold',z['new_b'],z['esc_b'])]:
            vals=arr[esc]
            if len(vals):ax.hist(np.log10(vals),bins=28,alpha=.45,density=True,
                                 label=key+(' (solo escapes observados)' if not esc.all() else ''))
        ax.set(xlabel='log10(t/MCSS)',ylabel='Densidad (muestra nueva)',title='B7: distribuciones de vidas - '+case)
        ax.legend();ax.grid(alpha=.2);save(fig,'B7_03_hist_logtau_'+case)
        # Sensitivity of ratio to prefixes (visual diagnostic, not inference)
        fig,ax=plt.subplots(figsize=(8,4.8))
        aa=z['new_a'];bb=z['new_b'];n=min(len(aa),len(bb))
        if z['esc_a'].all() and z['esc_b'].all():
            indices=np.unique(np.linspace(2,n,min(130,max(2,n-1)),dtype=int))
            ratios=np.cumsum(bb)[:n][indices-1]/np.cumsum(aa)[:n][indices-1]
            ax.plot(indices,ratios,linewidth=1.3)
        else:
            ax.text(.5,.5,'Medias no estimables con censura; se omite el diagnóstico',
                    ha='center',va='center',transform=ax.transAxes)
        ax.axhline(1,color='black',alpha=.5,ls=':')
        ax.axhspan(*MARGIN,color='0.83',alpha=.5)
        ax.set(xlabel='Número acumulado de realizaciones nuevas por algoritmo',ylabel='Razón acumulada de medias',
               title=f'B7: estabilidad descriptiva - {case} (no usar para detener campaña)')
        ax.grid(alpha=.2);save(fig,'B7_04_estabilidad_'+case)
    report=dest/'B7_INFORME.md'
    with report.open('w',encoding='utf-8') as f:
        f.write('# Bloque 7 — Extensión de las comparaciones inconclusas\n\n')
        f.write(f'**Snapshot histórico inmutable:** `{SNAPSHOT}`.\n\n')
        f.write(f'**Datos nuevos:** `{source.name}`. El tamaño de muestra y horizonte se fijaron antes de ejecutar, no en función de PASS/FAIL.\n\n')
        f.write(f'**Diseño:** {json.dumps(spec,ensure_ascii=False)}.\n\n')
        f.write('El criterio de equivalencia es que TODO el IC bootstrap 95% de la razón de medias esté dentro de [0.95,1.05]. '
                'Los tests KS son complementarios y no demuestran identidad de distribuciones. '
                'Los datos censurados se conservan: no se interpretan medias de vidas de escapes condicionados como medias incondicionales.\n\n')
        f.write('## Conclusiones por condición\n\n')
        f.write('| Caso | Fuente | n Standard/n-fold | R_tau | IC 95% | Estado |\n|---|---|---:|---:|---|---|\n')
        for row in summary.itertuples():
            fmt=lambda x: '—' if pd.isna(x) else f'{x:.5f}'
            f.write(f'| {row.case} | {row.group} | {row.n_standard}/{row.n_nfold} | {fmt(row.R_tau)} | [{fmt(row.ci95_low)}, {fmt(row.ci95_high)}] | {row.status} |\n')
        f.write('\n**Lectura:** el contraste SOLO_NUEVOS es el resultado prospectivo primario; COMBINADO es un análisis de mayor potencia, '
                'pero depende de que los flujos aleatorios sean independientes y del mismo protocolo físico.\n')
        f.write('\n**Censura:** si existe, la comparación de medias se deja NO EVALUABLE; las gráficas ECDF/S con censura son solo descripciones brutas y no sustituyen Kaplan–Meier.\n')
        f.write('\n**Límite del criterio:** obtener PASS no demuestra igualdad matemática ni equivalencia de colas; obtener INCONCLUSIVE tampoco demuestra diferencia física.\n')
    files=[summ,report]+figs
    write_manifest(dest,files)
    return summary,figs


def generate(args,root:Path):
    spec=design(args)
    before=manifest_state(root);verify_frozen_integrity(root,before)
    run=create_run_dir(root,'inconclusos_b7')
    (run/'datos_nuevos').mkdir(exist_ok=False)
    (run/'B7_DISENO_PREVIO.json').write_text(json.dumps({'created_utc':utc_now(),'spec':spec,
                                     'platform':platform.platform(),'python':sys.version},indent=2,ensure_ascii=False),encoding='utf-8')
    print('B7 directorio:',run,flush=True)
    records=[]
    try:
        engines=build_engines(root,run,run/'logs'/'compilacion_b7.log')
        for case,algo in expected(spec):
            _,dyn,t=CASE_BY_NAME[case]
            runs=runs_for(spec,case)
            seed=case_seed(spec['seed'],case,algo)
            hist=verify_historical(root,case,algo)
            if seed in set(hist.seed.astype(int)):raise ValueError('Seed histórica reusada')
            dst=run/'datos_nuevos'/f'{case}_{algo}.csv'
            flags=['--max-attempts' if algo=='standard' else '--max-time-attempts',str(spec['max_attempts'])]
            cmd=[str(engines[algo]),'--L',str(L),'--T',str(t),'--J',str(J),'--H',str(H),
                 '--runs',str(runs),'--seed',str(seed),'--dynamics',dyn,'--output',dst.relative_to(run).as_posix(),*flags]
            print(f' {case:17s} {algo:8s} runs={runs}',flush=True)
            log=run/'logs'/f'{case}_{algo}.log'
            tick=time.perf_counter()
            with log.open('w',encoding='utf-8') as handle:
                handle.write('$ '+' '.join(cmd)+'\n');handle.flush()
                result=subprocess.run(cmd,cwd=run,stdout=handle,stderr=subprocess.STDOUT)
            if result.returncode:raise RuntimeError(f'Simulador falló: {log}')
            b6spec={'L':L,'T':t,'J':J,'H':H,'runs':runs,'max_attempts':spec['max_attempts']}
            check_run_csv(dst,b6spec,dyn,H,algo,seed)
            r={'case':case,'algorithm':algo,'path':dst.relative_to(run).as_posix(),
               'sha256':sha256(dst),'history_path':historical_path(root,case,algo).relative_to(root).as_posix(),
               'history_sha256':sha256(historical_path(root,case,algo)),
               'runs':runs,'seed':seed,'elapsed_seconds':round(time.perf_counter()-tick,4)}
            records.append(r)
            (run/'B7_MANIFEST_DATOS.json').write_text(json.dumps({'spec':spec,'records':records},indent=2),encoding='utf-8')
        summary,figs=analyze(run,root,spec,records,run)
        if manifest_state(root)!=before:raise ValueError('Integridad histórica alterada')
        (run/'B7_ESTADO.json').write_text(json.dumps({'status':'PASS','completed_utc':utc_now(),
                'new_rows':sum(r['runs'] for r in records),'figures':len(figs)//2,
                'status_primary':dict(zip(summary[summary.group=='SOLO_NUEVOS'].case,
                                           summary[summary.group=='SOLO_NUEVOS'].status))},indent=2),encoding='utf-8')
        print('B7 PASS:',run,flush=True)
        return 0
    except Exception as exc:
        (run/'ERROR_B7.log').write_text(traceback.format_exc(),encoding='utf-8')
        print(f'B7 ERROR: {exc}, detalles: {run}/ERROR_B7.log',file=sys.stderr,flush=True)
        return 1


def reanalyze(args,root:Path):
    source=Path(args.directorio).resolve()
    allowed=(root/'results'/'practica_cierre').resolve()
    if not source.is_relative_to(allowed) or not source.is_dir():
        raise ValueError('Solo se permiten carpetas de results/practica_cierre')
    data=json.loads((source/'B7_MANIFEST_DATOS.json').read_text(encoding='utf-8'))
    spec=data['spec'];validate_spec(spec)
    before=manifest_state(root);verify_frozen_integrity(root,before)
    output=create_run_dir(root,'reanalisis_b7')
    try:
        summary,figs=analyze(source,root,spec,data['records'],output)
        if manifest_state(root)!=before:raise ValueError('Integridad histórica alterada')
        (output/'B7_ESTADO.json').write_text(json.dumps({'status':'PASS','original':str(source),
                         'figures':len(figs)//2},indent=2),encoding='utf-8')
        print('B7 ANALISIS PASS:',output,flush=True)
        return 0
    except Exception:
        (output/'ERROR_B7.log').write_text(traceback.format_exc(),encoding='utf-8')
        raise


def main(argv=None,root:Path=ROOT):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='accion',required=True)
    gen=sub.add_parser('generar',help='Simula más muestras independientes, SIN tocar release')
    gen.add_argument('--perfil',choices=['piloto','practica'],default='piloto')
    gen.add_argument('--runs-frio',type=int,default=None)
    gen.add_argument('--runs-templado',type=int,default=None)
    gen.add_argument('--casos',default=','.join(CASE_BY_NAME))
    gen.add_argument('--seed',type=int,default=2026111507)
    gen.add_argument('--bootstrap',type=int,default=1800)
    gen.add_argument('--max-attempts',type=int,default=100000000)
    ana=sub.add_parser('analizar',help='Reproduce figuras/tablas desde CSV B7, verificando hashes')
    ana.add_argument('--directorio',required=True)
    args=parser.parse_args(argv)
    root=Path(root).resolve()
    if args.accion=='generar':return generate(args,root)
    return reanalyze(args,root)

if __name__=='__main__':
    raise SystemExit(main())
