"""B6: campaña reproducible de campo H del Ising cinético Standard/n-fold.

Ejemplo:
 python -m scripts.practica_cierre.barrido_campo_b6 generar --perfil piloto
 python -m scripts.practica_cierre.barrido_campo_b6 analizar --directorio results/practica_cierre/ID_barrido_H_b6

La release v1.0.0 y sus ensembles son de solo lectura. Las salidas se guardan
siempre en nuevas carpetas de practica. El motor original NO se modifica.
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

from .validar_baseline import ROOT, SNAPSHOT, sha256, manifest_state, create_run_dir
from .nivel2 import verify_frozen_integrity

PRESETS = {
    'piloto': {'L': 16, 'T': 1.5, 'J': 1.0, 'runs': 40, 'fields': [-3., -2.5, -2., -1.5, -1.0, -.75],
               'max_attempts': 2000000, 'dynamics': ['glauber', 'metropolis']},
    'practica': {'L': 32, 'T': 1.5, 'J': 1.0, 'runs': 500, 'fields': [-3., -2.5, -2., -1.5, -1.0, -.75],
                 'max_attempts': 30000000, 'dynamics': ['glauber', 'metropolis']},
}
REQUIRED = {'run','L','N','T','J','H','dynamics','algorithm','seed','stream',
            'time_attempts','time_mcss','events','final_M','reached_M0','cpu_seconds'}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def stable_seed(base: int, dyn: str, algo: str, field: float) -> int:
    """Se mantiene un flujo distinto por (campo, regla, algoritmo)."""
    tag = f'B6|{base}|{dyn}|{algo}|{float(field):.17g}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(tag).digest()[:8], 'little') & ((1 << 63) - 1)


def validate_design(spec: dict):
    if spec['L'] < 4 or spec['L'] % 2:
        raise ValueError('L debe ser par y >= 4 (el criterio M=0 exige N par)')
    if not all(math.isfinite(float(spec[k])) for k in ('T','J')) or spec['T'] <= 0 or spec['J'] <= 0:
        raise ValueError('T y J deben ser positivos y finitos')
    if spec['runs'] < 2 or spec['max_attempts'] < 1 or spec['bootstrap'] < 100:
        raise ValueError('Se exigen >=2 runs, >=1 intentos y >=100 replicas bootstrap')
    fields = spec['fields']
    if len(fields) < 2 or len(set(fields)) != len(fields):
        raise ValueError('Se necesitan al menos dos campos distintos y no repetidos')
    if not all(math.isfinite(h) and h < 0 for h in fields):
        raise ValueError('Todos los campos H deben ser finitos y estrictamente negativos')
    if any(d not in ('glauber','metropolis') for d in spec['dynamics']) or not spec['dynamics']:
        raise ValueError('Dinámica no válida')
    if spec['seed'] < 0:
        raise ValueError('Semilla global no negativa')


def new_spec(args):
    base=PRESETS[args.perfil]
    fields=base['fields'] if args.campos is None else [float(v.strip()) for v in args.campos.split(',')]
    ds=base['dynamics'] if args.dinamicas == 'ambas' else [args.dinamicas]
    spec={'perfil':args.perfil, 'L':args.L if args.L is not None else base['L'], 'T':args.T if args.T is not None else base['T'],
          'J':args.J if args.J is not None else base['J'], 'runs':args.runs if args.runs is not None else base['runs'],
          'fields':fields, 'max_attempts':args.max_attempts if args.max_attempts is not None else base['max_attempts'],
          'dynamics':ds, 'seed':args.seed, 'bootstrap':args.bootstrap,
          'note':'Campo H<0, todos los espines inicialmente +1, absorcion M=0, tiempo en MCSS'}
    validate_design(spec)
    return spec


def build_engines(root:Path, run:Path, log:Path):
    build=run/'build_b6'
    commands=[['cmake','-S',str(root),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release'],
              ['cmake','--build',str(build),'--config','Release','--target','ising_standard','ising_nfold','test_physics','test_nfold'],
              ['ctest','--test-dir',str(build),'--output-on-failure']]
    for c in commands:
        with log.open('a',encoding='utf-8') as fh:
            fh.write('$ '+' '.join(c)+'\n')
            res=subprocess.run(c, cwd=root, stdout=fh, stderr=subprocess.STDOUT, check=False)
        if res.returncode:
            raise RuntimeError(f'Compilacion fallo (exit {res.returncode}), ver {log}')
    paths={}
    for algo in ('standard','nfold'):
        suffix='.exe' if os.name=='nt' else ''
        candidate=[p for p in build.rglob('ising_'+algo+suffix) if p.is_file()]
        if not candidate:
            raise FileNotFoundError(f'No se encontro ising_{algo} tras compilar')
        ranked=sorted(candidate,key=lambda p:(0 if 'Release' in p.parts else 1,len(p.parts)))
        paths[algo]=ranked[0]
    return paths


def expected_cases(spec):
    return [(dyn,float(h),algo) for dyn in spec['dynamics'] for h in spec['fields']
            for algo in ('standard','nfold')]


def file_tag(dyn,h,algo):
    return f'{dyn}_H'+str(abs(h)).replace('.','p')+'_'+algo


def check_run_csv(path:Path, spec:dict, dyn:str, h:float, algo:str, seed:int):
    frame=pd.read_csv(path)
    if not REQUIRED.issubset(frame.columns):
        raise ValueError(f'{path.name}: faltan columnas: {sorted(REQUIRED-set(frame.columns))}')
    if len(frame)!=spec['runs'] or list(frame['run']) != list(range(spec['runs'])):
        raise ValueError(f'{path.name}: número de runs/índices incorrecto')
    for name,expected in [('L',spec['L']),('N',spec['L']**2),('T',spec['T']),('J',spec['J']),('H',h)]:
        if not np.allclose(frame[name].to_numpy(dtype=float),expected,atol=1e-10,rtol=0):
            raise ValueError(f'{path.name}: parámetro inconsistente {name}')
    for name,expected in [('dynamics',dyn),('algorithm',algo),('seed',seed)]:
        if not (frame[name].astype(str) == str(expected)).all():
            raise ValueError(f'{path.name}: {name} inconsistente')
    if list(frame['stream'].astype(int)) != list(range(1,spec['runs']+1)):
        raise ValueError('Streams incorrectos')
    for name in ('time_attempts','time_mcss','events','cpu_seconds'):
        v=frame[name].to_numpy(float)
        if not np.isfinite(v).all() or np.any(v < 0):
            raise ValueError(f'{path.name}: valores invalidos en {name}')
    if not np.allclose(frame.time_attempts.to_numpy(float)/spec['L']**2,
                       frame.time_mcss.to_numpy(float),rtol=2e-13,atol=1e-12):
        raise ValueError(f'{path.name}: inconsistencia reloj/MCSS')
    if not frame['reached_M0'].isin([0,1]).all():
        raise ValueError('Valor reached_M0 no binario')
    if ((frame.reached_M0 == 1) & (frame.final_M != 0)).any():
        raise ValueError('Escape declarado sin magnetizacion nula')
    if (frame['events'] > frame['time_attempts']).any():
        raise ValueError('Mas eventos aceptados que intentos equivalentes')
    if algo=='standard' and (frame.time_attempts > spec['max_attempts']).any():
        raise ValueError('Standard excede max-attempts')
    return frame


def compute_measured(frame:pd.DataFrame, spec:dict, algo:str):
    """N-fold puede sobrepasar el limite al ejecutar su ultimo salto.

    Censuramos al horizonte predefinido; un flip que suceda despues del horizonte
    NO es un evento observado dentro de él, aunque reached_M0=1 en el raw.
    """
    capped=frame.time_attempts.to_numpy(np.float64)>spec['max_attempts']
    escaped=(frame.reached_M0.to_numpy(int)==1) & ~capped
    horizon=float(spec['max_attempts']) / (spec['L']**2)
    observed=np.minimum(frame.time_mcss.to_numpy(float),horizon)
    if np.any(escaped & (observed<=0)):
        raise ValueError('Escape en t<=0 no permitido')
    return observed, escaped


def boot_stats(a:np.ndarray,b:np.ndarray,seed:int,nboot:int):
    rng=np.random.default_rng(seed)
    means_a=[];means_b=[];ratios=[]
    for start in range(0,nboot,64):
        rep=min(64,nboot-start)
        x=np.mean(a[rng.integers(len(a),size=(rep,len(a)))],axis=1)
        y=np.mean(b[rng.integers(len(b),size=(rep,len(b)))],axis=1)
        means_a.extend(x);means_b.extend(y);ratios.extend(y/x)
    def ci(v): return tuple(float(x) for x in np.quantile(v,[0.025,0.975]))
    return ci(means_a),ci(means_b),ci(ratios)


def analyze_records(raw_dir:Path,spec:dict,records:list[dict]):
    by_key={}
    for record in records:
        algo,dyn,h=record['algorithm'],record['dynamics'],float(record['H'])
        if (dyn,h,algo) in by_key:
            raise ValueError('Grupo repetido en manifiesto')
        # Los manifiestos guardan rutas POSIX, pero Path en Windows usa barras invertidas.
        # Validar por componentes evita falsos negativos y mantiene la seguridad.
        rel=Path(str(record['path']).replace('\\', '/'))
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0] != 'datos_nuevos':
            raise ValueError('Ruta de datos no permitida')
        f=(raw_dir/rel).resolve()
        if not f.is_relative_to(raw_dir.resolve()):
            raise ValueError('Ruta de datos no permitida')
        if not f.is_file() or sha256(f)!=record['sha256']:
            raise ValueError(f'Archivo ausente/alterado {rel}')
        seed=stable_seed(spec['seed'],dyn,algo,h)
        if record['seed']!=seed:
            raise ValueError('Semilla en manifiesto incorrecta')
        by_key[(dyn,h,algo)]=check_run_csv(f,spec,dyn,h,algo,seed)
    if set(by_key)!=set(expected_cases(spec)):
        raise ValueError('Faltan/sobran pares Standard-nfold en el barrido')
    rows=[]
    for dyn in spec['dynamics']:
        for h in sorted(spec['fields'],key=abs):
            fs=by_key[(dyn,h,'standard')];fn=by_key[(dyn,h,'nfold')]
            a,escape_a=compute_measured(fs,spec,'standard')
            b,escape_b=compute_measured(fn,spec,'nfold')
            n_a=int(np.sum(escape_a)); n_b=int(np.sum(escape_b))
            complete=n_a==len(a) and n_b==len(b)
            rec={'L':spec['L'],'T':spec['T'],'J':spec['J'],'H':h,'abs_H_over_J':abs(h/spec['J']),
                 'dynamics':dyn,'n_standard':len(a),'n_nfold':len(b),
                 'escaped_standard':n_a,'escaped_nfold':n_b,
                 'censored_standard':len(a)-n_a,'censored_nfold':len(b)-n_b,
                 'horizon_mcss':spec['max_attempts']/spec['L']**2,
                 'mean_standard_mcss':float(np.mean(a)) if complete else None,
                 'mean_nfold_mcss':float(np.mean(b)) if complete else None,
                 'ratio_nfold_standard':float(np.mean(b)/np.mean(a)) if complete else None,
                 'mean_standard_ci_low':None,'mean_standard_ci_high':None,
                 'mean_nfold_ci_low':None,'mean_nfold_ci_high':None,
                 'ratio_ci_low':None,'ratio_ci_high':None,
                 'equivalence_status':'CENSURADO_NO_EVALUABLE' if not complete else 'INCONCLUSIVE',
                 'cpu_standard_seconds':float(fs.cpu_seconds.sum()),
                 'cpu_nfold_seconds':float(fn.cpu_seconds.sum()),
                 'speedup_cpu_exploratory':float(fs.cpu_seconds.sum()/fn.cpu_seconds.sum()) if fn.cpu_seconds.sum()>0 else None}
            if complete:
                seed=stable_seed(spec['seed'],'bootstrap_'+dyn,'both',h)
                (al,ah),(bl,bh),(rl,rh)=boot_stats(a,b,seed,spec['bootstrap'])
                rec.update(mean_standard_ci_low=al,mean_standard_ci_high=ah,
                           mean_nfold_ci_low=bl,mean_nfold_ci_high=bh,ratio_ci_low=rl,ratio_ci_high=rh)
                rec['equivalence_status']=('PASS' if rl>=.95 and rh<=1.05 else
                                          'FAIL' if rh<.95 or rl>1.05 else 'INCONCLUSIVE')
            rows.append(rec)
    return pd.DataFrame(rows)


def render(summary:pd.DataFrame,out:Path, spec:dict):
    out.mkdir(parents=True,exist_ok=False)
    files=[]
    def save(fig,stem):
        for ext in ('png','pdf'):
            f=out/(stem+'.'+ext)
            fig.savefig(f,dpi=170,bbox_inches='tight')
            files.append(f)
        plt.close(fig)
    for dyn,data in summary.groupby('dynamics'):
        data=data.sort_values('abs_H_over_J')
        good=data[data.censored_standard.eq(0)&data.censored_nfold.eq(0)]
        fig,ax=plt.subplots(figsize=(8.8,5.2))
        for algo,label in [('standard','Standard'),('nfold','n-fold')]:
            if len(good):
                x=good.abs_H_over_J.to_numpy(float)
                y=good['mean_'+algo+'_mcss'].to_numpy(float)
                lo=y-good['mean_'+algo+'_ci_low'].to_numpy(float)
                hi=good['mean_'+algo+'_ci_high'].to_numpy(float)-y
                ax.errorbar(x,y,yerr=[lo,hi],fmt='o-',capsize=3,label=label)
        if not len(good):
            ax.text(.5,.5,'No hay campos con escape completo\n(no se representan medias sesgadas)',
                    ha='center',va='center',transform=ax.transAxes)
        ax.set(xlabel='|H| / J',ylabel='Vida media de escape <tau> (MCSS)',
               title=f'N2.09 - Vida vs campo | {dyn.capitalize()}, L={spec["L"]}, T/J={spec["T"]/spec["J"]:g}')
        if len(good):
            ax.set_yscale('log');ax.legend()
        ax.grid(alpha=.25)
        save(fig,f'N2_09_vida_vs_campo_{dyn}')
        fig,axes=plt.subplots(2,1,figsize=(8.6,7),sharex=True)
        if len(good):
            x=good.abs_H_over_J.to_numpy(float)
            y=good.ratio_nfold_standard.to_numpy(float)
            axes[0].errorbar(x,y,yerr=[y-good.ratio_ci_low.to_numpy(float),good.ratio_ci_high.to_numpy(float)-y],
                             fmt='o-',capsize=3,label='n-fold / Standard')
        axes[0].axhspan(.95,1.05,color='gray',alpha=.13,label='Margen +/- 5%')
        axes[0].axhline(1,linestyle=':',color='gray')
        axes[0].set(ylabel='R_tau',title=f'Equivalencia y censura | {dyn.capitalize()}')
        axes[0].legend()
        axes[1].plot(data.abs_H_over_J,data.escaped_standard/data.n_standard,'o-',label='Standard')
        axes[1].plot(data.abs_H_over_J,data.escaped_nfold/data.n_nfold,'s--',label='n-fold')
        axes[1].set(xlabel='|H| / J',ylabel='Fraccion de escapes hasta el horizonte',ylim=(-.04,1.04))
        axes[1].legend()
        for ax in axes:ax.grid(alpha=.2)
        fig.tight_layout();save(fig,f'N2_10_equivalencia_censura_{dyn}')
    return files


def write_manifest(output:Path, paths:list[Path]):
    manifest=[]
    for p in sorted(paths):
        if p.is_file():
            manifest.append({'path':p.relative_to(output).as_posix(),'sha256':sha256(p),'bytes':p.stat().st_size})
    with (output/'MANIFEST_B6_SALIDAS.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['path','sha256','bytes']);writer.writeheader();writer.writerows(manifest)
    return manifest


def report(output:Path, source:Path, spec:dict, summary:pd.DataFrame, raw_count:int, files:list[Path]):
    complete=int(((summary.censored_standard==0)&(summary.censored_nfold==0)).sum())
    with (output/'RESUMEN.md').open('w',encoding='utf-8') as f:
        f.write('# Bloque 6 - Barrido de campo H\n\n')
        f.write(f'**Estado: PASS (analisis de datos)** | Fuente: `{source.name}`\n\n')
        f.write(f'- Perfil: `{spec["perfil"]}`; L={spec["L"]}, T/J={spec["T"]/spec["J"]:.4g}, J={spec["J"]}.\n')
        f.write(f'- Realizaciones por punto y algoritmo: {spec["runs"]}; total CSV: {raw_count}.\n')
        f.write(f'- Campos H: {spec["fields"]}; dinamicas: {spec["dynamics"]}.\n')
        f.write(f'- Horizonte: {spec["max_attempts"]} intentos equivalentes ({spec["max_attempts"]/spec["L"]**2:g} MCSS).\n')
        f.write(f'- Pares de campos sin censura: **{complete}/{len(summary)}**.\n')
        f.write('- Medias y bootstrap 95% solo para pares de muestras SIN censura. No se descartan vidas no escapadas.\n')
        f.write('- El salto n-fold que sobrepasa el horizonte se considera censurado al horizonte, incluso si el flip posterior alcanza M=0.\n')
        f.write('- El margen +/-5% es una convencion practica y la clasificacion bootstrap es exploratoria, sobre todo en el piloto.\n')
        f.write('- Los tiempos de CPU son exploratorios; no sustituyen benchmarks con repeticion P07D/E.\n')
        f.write('- La curva muestra observaciones, NO un ajuste universal de nucleacion o exponentes criticos.\n\n')
        f.write('## Productos\n\n')
        for p in files:
            f.write(f'- `{p.relative_to(output).as_posix()}`\n')
        f.write('\n## Tabla de resultados\n\n')
        f.write('| Dinamica | H/J | Escapes Standard | Escapes n-fold | Media Standard | Media n-fold | R_tau | Estado |\n')
        f.write('|---|---:|---:|---:|---:|---:|---:|---|\n')
        for r in summary.itertuples():
            v=lambda n: ('- ' if pd.isna(getattr(r,n)) else f'{getattr(r,n):.5g}')
            f.write(f'| {r.dynamics} | {r.H/r.J:g} | {r.escaped_standard}/{r.n_standard} | {r.escaped_nfold}/{r.n_nfold} | '
                    f'{v("mean_standard_mcss")} | {v("mean_nfold_mcss")} | {v("ratio_nfold_standard")} | {r.equivalence_status} |\n')


def do_analysis(root:Path,source:Path, spec:dict,records:list[dict],dest:Path):
    data=analyze_records(source,spec,records)
    fig_dir=dest/'figuras_b6'
    files=render(data,fig_dir,spec)
    summ=dest/'resumen_barrido_H.csv';data.to_csv(summ,index=False)
    files=[summ]+files
    report(dest,source,spec,data,len(records),files)
    manifest=write_manifest(dest,files+[dest/'RESUMEN.md'])
    return data,manifest


def run_campaign(args,root:Path):
    spec=new_spec(args)
    initial=manifest_state(root);verify_frozen_integrity(root,initial)
    run=create_run_dir(root,'barrido_H_b6')
    (run/'datos_nuevos'/'barrido_H').mkdir(parents=True)
    (run/'DISENO.json').write_text(json.dumps({'spec':spec,'baseline':SNAPSHOT,'created_utc':utc_now(),
                         'platform':platform.platform(),'python':sys.version},indent=2,ensure_ascii=False),encoding='utf-8')
    print('B6 directorio:',run,flush=True)
    records=[]
    try:
        binaries=build_engines(root,run,run/'logs'/'compilacion.log')
        for dyn,h,algo in expected_cases(spec):
            seed=stable_seed(spec['seed'],dyn,algo,h)
            dst=run/'datos_nuevos'/'barrido_H'/(file_tag(dyn,h,algo)+'.csv')
            cmd=[str(binaries[algo]),'--L',str(spec['L']),'--T',str(spec['T']),
                 '--J',str(spec['J']),'--H',str(h),'--runs',str(spec['runs']),
                 '--seed',str(seed),'--dynamics',dyn,'--output',dst.relative_to(run).as_posix()]
            cmd += ['--max-attempts' if algo=='standard' else '--max-time-attempts',str(spec['max_attempts'])]
            log=run/'logs'/(file_tag(dyn,h,algo)+'.log')
            print(f'  {dyn:10} H={h:5g} {algo:8} | runs={spec["runs"]}',flush=True)
            tic=time.perf_counter()
            with log.open('w',encoding='utf-8') as f:
                f.write('$ '+' '.join(cmd)+'\n');f.flush()
                proc=subprocess.run(cmd,cwd=run,stdout=f,stderr=subprocess.STDOUT,check=False)
            if proc.returncode:
                raise RuntimeError(f'Fallo de simulador ({proc.returncode}): {log}')
            check_run_csv(dst,spec,dyn,h,algo,seed)
            records.append({'dynamics':dyn,'H':h,'algorithm':algo,'seed':seed,'path':dst.relative_to(run).as_posix(),
                            'sha256':sha256(dst),'wall_seconds':round(time.perf_counter()-tic,4),
                            'command_flags':{'L':spec['L'],'T':spec['T'],'J':spec['J'],'H':h,
                                             'runs':spec['runs'],'dynamics':dyn,'max_time_attempts':spec['max_attempts']}})
        (run/'MANIFEST_DATOS_B6.json').write_text(json.dumps({'spec':spec,'records':records},indent=2),encoding='utf-8')
        summary,manifest=do_analysis(root,run,spec,records,run)
        if manifest_state(root)!=initial:
            raise ValueError('Se modificaron archivos protegidos: abortar')
        (run/'ESTADO.json').write_text(json.dumps({'status':'PASS','created_utc':utc_now(),
                 'total_raw_files':len(records),'total_figures':len([r for r in manifest if r['path'].endswith('.png')]),
                 'complete_pairs':int(((summary.censored_standard==0)&(summary.censored_nfold==0)).sum()),
                 'total_pairs':len(summary)},indent=2),encoding='utf-8')
        print('B6 PASS:',run,flush=True)
        return 0
    except Exception as exc:
        (run/'ERROR_B6.log').write_text(traceback.format_exc(),encoding='utf-8')
        print(f'B6 FAIL: {exc} (ver {run / "ERROR_B6.log"})',file=sys.stderr)
        return 1


def reanalyze(args,root:Path):
    source=Path(args.directorio).resolve()
    trusted=(root/'results'/'practica_cierre').resolve()
    if not source.is_relative_to(trusted) or not source.is_dir():
        raise ValueError('Se requiere una carpeta B6 de results/practica_cierre')
    data=json.loads((source/'MANIFEST_DATOS_B6.json').read_text(encoding='utf-8'))
    spec=data['spec'];records=data['records'];validate_design(spec)
    initial=manifest_state(root);verify_frozen_integrity(root,initial)
    dest=create_run_dir(root,'analisis_b6')
    try:
        _,manifest=do_analysis(root,source,spec,records,dest)
        if manifest_state(root)!=initial:
            raise ValueError('Integridad del baseline perdida')
        (dest/'ESTADO.json').write_text(json.dumps({'status':'PASS','source':str(source),
            'total_figures':len([v for v in manifest if v['path'].endswith('.png')])},indent=2),encoding='utf-8')
        print('B6 analisis PASS:',dest)
        return 0
    except Exception:
        (dest/'ERROR_B6.log').write_text(traceback.format_exc(),encoding='utf-8')
        raise


def main(argv=None,root:Path=ROOT):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='accion',required=True)
    gen=sub.add_parser('generar',help='Compila motores existentes y ejecuta campaña nueva')
    gen.add_argument('--perfil',choices=list(PRESETS),default='piloto')
    gen.add_argument('--L',type=int,default=None)
    gen.add_argument('--T',type=float,default=None)
    gen.add_argument('--J',type=float,default=None)
    gen.add_argument('--runs',type=int,default=None)
    gen.add_argument('--campos',type=str,default=None,help='CSV de negativos, usar --campos=-3,-2,-1.5,-1')
    gen.add_argument('--dinamicas',choices=['ambas','glauber','metropolis'],default='ambas')
    gen.add_argument('--max-attempts',type=int,default=None)
    gen.add_argument('--seed',type=int,default=20261115)
    gen.add_argument('--bootstrap',type=int,default=800)
    ana=sub.add_parser('analizar',help='Regenera figuras desde campaña B6; datos originales inmutables')
    ana.add_argument('--directorio',required=True)
    opts=p.parse_args(argv)
    root=Path(root).resolve()
    if opts.accion=='generar':return run_campaign(opts,root)
    return reanalyze(opts,root)

if __name__=='__main__':
    raise SystemExit(main())
