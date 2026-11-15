"""Bloque 2 de la practica Ising: nuevas figuras a partir de datos P06 congelados.

No invoca motores C ni cambia la release P08. Los PNG/PDF y CSV derivados
se guardan exclusivamente en una carpeta unica results/practica_cierre/<id>/.
Uso: python -m scripts.practica_cierre.nivel2 [--solo all|distribuciones|rendimiento].
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from .validar_baseline import ROOT, SNAPSHOT, create_run_dir, manifest_state, sha256

CASES = (
    ('glauber', -0.75, 0.8, 'inconcluso'),
    ('glauber', -0.75, 0.9, 'inconcluso'),
    ('metropolis', -0.75, 0.8, 'inconcluso'),
    ('glauber', -3.0, 0.8, 'control'),
)
LABELS = {'standard': 'Standard', 'nfold': 'n-fold'}


def case_tag(dyn: str, field: float, temp: float) -> str:
    def number(v):
        return (('m' if v < 0 else '') + f'{abs(v):g}'.replace('.', 'p'))
    return f'{dyn}_H{number(field)}_T{number(temp)}'


def group_key(frame: pd.DataFrame) -> tuple:
    fields = ['L', 'T', 'J', 'H', 'dynamics', 'algorithm']
    if frame.empty or any(k not in frame for k in fields):
        raise ValueError('Datos vacios o sin parametros fisicos: ' + ', '.join(fields))
    row = frame.iloc[0]
    key = (int(row['L']), float(row['T']), float(row['J']), float(row['H']), str(row['dynamics']), str(row['algorithm']))
    for f, v in zip(fields, key):
        if f in ('T', 'J', 'H'):
            if not np.allclose(frame[f].to_numpy(dtype=float), v, rtol=0, atol=1e-10):
                raise ValueError(f'CSV con parametros heterogeneos: {f}')
        elif not (frame[f] == v).all():
            raise ValueError(f'CSV con parametros heterogeneos: {f}')
    return key


def verify_frozen_integrity(root: Path, state: dict[str,str]) -> None:
    """Ademas de no alterar el original, exige que sus hashes coincidan con la release."""
    with (root / 'release' / 'release_manifest.csv').open(newline='', encoding='utf-8') as f:
        for item in csv.DictReader(f):
            if state.get(item['path']) != item['sha256']:
                raise ValueError('Fuente historica alterada respecto al manifiesto: ' + item['path'])


def load_runs(raw_dir: Path, *, required_algorithms=('standard','nfold')) -> tuple[dict[tuple, np.ndarray], list[dict]]:
    """CSV por realizacion; rechaza censura no gestionada y duplicados de parametros."""
    if not raw_dir.is_dir():
        raise FileNotFoundError(f'No existe carpeta original: {raw_dir}')
    result = {}
    sources = []
    files = sorted(raw_dir.glob('*.csv'))
    if not files:
        raise ValueError(f'No hay CSV por realizacion en {raw_dir}')
    for file in files:
        df = pd.read_csv(file)
        key = group_key(df)
        if key in result:
            raise ValueError(f'Duplicidad de grupo fisico en {raw_dir}: {key}')
        if key[5] not in required_algorithms:
            raise ValueError(f'Algoritmo no esperado: {key[5]}')
        required = {'run', 'time_mcss', 'reached_M0', 'cpu_seconds'}
        if not required.issubset(df.columns):
            raise ValueError(f'CSV incompleto {file.name}: {required - set(df.columns)}')
        if df['run'].duplicated().any():
            raise ValueError(f'Identificador run duplicado: {file.name}')
        if (df['reached_M0'] != 1).any():
            raise ValueError(f'{file.name}: hay trayectorias censuradas. No aplicar ECDF ingenua; usar Kaplan-Meier.')
        tau = pd.to_numeric(df['time_mcss'], errors='raise').to_numpy(float)
        if not np.all(np.isfinite(tau)) or np.any(tau <= 0):
            raise ValueError(f'Tiempos no validos en {file.name}')
        result[key] = tau
        sources.append({'path': file.as_posix(), 'sha256': sha256(file), 'n': len(tau), 'key': key})
    for key in list(result):
        partner = (*key[:-1], 'nfold' if key[-1] == 'standard' else 'standard')
        if partner not in result:
            raise ValueError(f'Falta comparacion Standard / n-fold: {key}')
    return result, sources


def select_pair(groups: dict, dyn: str, field: float, temp: float, L: int=32, J: float=1) -> tuple[np.ndarray, np.ndarray]:
    k = (L, temp, J, field, dyn)
    try:
        return groups[(*k, 'standard')], groups[(*k, 'nfold')]
    except KeyError as e:
        raise ValueError(f'No existe el par fisico {k}') from e


def empirical_cdf(values: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    x, count = np.unique(np.sort(np.asarray(values, dtype=float)), return_counts=True)
    return x, np.cumsum(count) / len(values)


def survival(values: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    x, f = empirical_cdf(values)
    return np.r_[0.0, x], np.r_[1.0, 1.0 - f]


def ecdf_difference(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    grid = np.unique(np.r_[x, y])
    xs = np.sort(x); ys = np.sort(y)
    return grid, np.searchsorted(ys, grid, side='right')/len(y) - np.searchsorted(xs, grid, side='right')/len(x)


def bootstrap_log_mean_ci(values: np.ndarray, *, seed: int, replicates: int=400) -> tuple[float,float]:
    if len(values) < 2:
        raise ValueError('Se requieren al menos dos escapes para un bootstrap')
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, replicates, 32):
        n = min(32, replicates - start)
        indices = rng.integers(len(values), size=(n, len(values)))
        means.extend(np.log(np.mean(values[indices], axis=1)).tolist())
    return tuple(float(v) for v in np.quantile(means, [0.025, 0.975]))


def add_header(ax, dyn, field, temp, nstd=None, nnf=None):
    subtitle = f'{dyn.capitalize()}  |  H/J={field:g}, T/J={temp:g}, L=32'
    if nstd is not None:
        subtitle += f'  |  n={nstd}/{nnf}'
    ax.set_title(subtitle, fontsize=10)


def save_figure(fig, out: Path, stem: str, registered: list[dict]):
    paths = []
    for fmt in ('png','pdf'):
        target = out / f'{stem}.{fmt}'
        fig.savefig(target, dpi=170, bbox_inches='tight', metadata=({'Title': stem} if fmt=='pdf' else None))
        registered.append({'name': stem, 'kind': fmt, 'path': target.relative_to(out.parent).as_posix(), 'sha256': sha256(target)})
        paths.append(target)
    plt.close(fig)
    return paths


def write_rows(path: Path, rows: list[dict]):
    if not rows:
        raise ValueError(f'Sin datos para {path}')
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def plot_distributions(groups, out: Path, registered):
    diagnostics = []
    for dyn, h, t, status in CASES:
        std, nf = select_pair(groups,dyn,h,t)
        tag = case_tag(dyn,h,t)
        ks = ks_2samp(std, nf, method='auto')
        grid, delta = ecdf_difference(std, nf)
        diagnostics.append({'dynamics':dyn, 'H':h, 'T':t, 'L':32, 'condition':status,
                            'n_standard':len(std),'n_nfold':len(nf),
                            'mean_standard_mcss':float(np.mean(std)), 'mean_nfold_mcss':float(np.mean(nf)),
                            'ratio_nfold_standard':float(np.mean(nf)/np.mean(std)),
                            'ks_D_exploratory':float(ks.statistic), 'ks_p_uncorrected':float(ks.pvalue),
                            'max_abs_delta_F':float(np.max(np.abs(delta)))})
        # N2.1 survival - two views of the same original escape samples
        fig, axes=plt.subplots(1,2,figsize=(11.2,4.1))
        for sample, label in [(std,'Standard'),(nf,'n-fold')]:
            x,y=survival(sample)
            axes[0].step(x,y,where='post',label=label)
            good=(x>0)&(y>0)
            axes[1].step(x[good],y[good],where='post',label=label)
        for ax in axes:
            ax.set_xlabel('Tiempo de primer paso (MCSS)')
            ax.set_ylabel('Supervivencia S(t)')
            ax.grid(alpha=.24)
            ax.legend()
        axes[0].set_title('Escala lineal'); axes[0].set_ylim(0,1.02)
        axes[1].set_title('Cola de supervivencia (semilog)');axes[1].set_yscale('log')
        fig.suptitle(f'N2.1 — {dyn.capitalize()}, H/J={h:g}, T/J={t:g} | n={len(std)}/{len(nf)}')
        fig.tight_layout();save_figure(fig,out,'N2_01_supervivencia_'+tag,registered)
        # N2.2 ECDF
        fig,axes=plt.subplots(2,1,figsize=(8.4,7.4),sharex=True,gridspec_kw={'height_ratios':[2,1]})
        for sample,label in [(std,'Standard'),(nf,'n-fold')]:
            x,y=empirical_cdf(sample)
            axes[0].step(x,y,where='post',label=label)
        axes[0].set_ylabel('F(t)');axes[0].legend()
        axes[1].step(grid, delta,where='post')
        axes[1].axhline(0,linestyle=':',linewidth=.9)
        axes[1].set_ylabel('F_nfold - F_Standard')
        axes[1].set_xlabel('Tiempo de primer paso (MCSS)')
        for ax in axes: ax.set_xscale('log');ax.grid(alpha=.23)
        fig.suptitle(f'N2.2 — {dyn.capitalize()}, H/J={h:g}, T/J={t:g} | KS D={ks.statistic:.4f} (exploratorio)')
        fig.tight_layout();save_figure(fig,out,'N2_02_ecdf_diferencia_'+tag,registered)
        # N2.3 log10(tau): same bin edges for both algorithms
        a = np.log10(std); b = np.log10(nf)
        q = np.r_[a,b]
        edges = np.histogram_bin_edges(q, bins='fd')
        if len(edges)<7 or len(edges)>65:
            edges=np.linspace(float(np.min(q)),float(np.max(q))+1e-10,max(7,min(65,len(edges))))
        fig,ax=plt.subplots(figsize=(8.4,4.6))
        ax.hist(a,bins=edges,density=True,histtype='step',linewidth=1.75,label=f'Standard (n={len(std)})')
        ax.hist(b,bins=edges,density=True,histtype='step',linewidth=1.75,label=f'n-fold (n={len(nf)})')
        ax.set_xlabel('log10(tau / MCSS)');ax.set_ylabel('Densidad por unidad log10')
        ax.set_title(f'N2.3 — {dyn.capitalize()}, H/J={h:g}, T/J={t:g}')
        ax.legend();ax.grid(alpha=.22)
        fig.tight_layout();save_figure(fig,out,'N2_03_logtau_'+tag,registered)
    write_rows(out/'N2_01_03_diagnosticos.csv',diagnostics)
    return len(diagnostics)


def plot_thermal(groups, summary: pd.DataFrame, out: Path, registered):
    details=[]
    for (dyn,h), subs in summary.groupby(['dynamics','H'],sort=True):
        subs=subs.sort_values('invT')
        fig,ax=plt.subplots(figsize=(8.4,5.2))
        for algo in ('standard','nfold'):
            x=[];ym=[];lo=[];hi=[]
            for record in subs.itertuples():
                vals=groups[(int(record.L),float(record.T),float(record.J),float(record.H),str(record.dynamics),algo)]
                seed=int.from_bytes(hashlib.sha256(f'{dyn}|{h}|{record.T}|{algo}'.encode()).digest()[:4], 'little')
                a,b=bootstrap_log_mean_ci(vals,seed=seed)
                logmean=float(np.log(np.mean(vals)))
                x.append(1.0/float(record.T));ym.append(logmean);lo.append(logmean-a);hi.append(b-logmean)
                details.append({'dynamics':dyn,'H':h,'T':record.T,'algorithm':algo,'n':len(vals),
                                'inverse_T':x[-1],'ln_mean_tau':logmean,'bootstrap95_low':a,'bootstrap95_high':b,
                                'mean_tau_mcss':float(np.mean(vals))})
            ax.errorbar(x,ym,yerr=[lo,hi],fmt='o-',capsize=2.8,label=LABELS[algo])
            fit_idx=[i for i,rec in enumerate(subs.itertuples()) if float(rec.T)<=1.2]
            if len(fit_idx)>=3:
                fit=np.polyfit(np.asarray(x)[fit_idx],np.asarray(ym)[fit_idx],1)
                xx=np.linspace(min(np.asarray(x)[fit_idx]),max(np.asarray(x)[fit_idx]),60)
                ax.plot(xx,np.polyval(fit,xx),linestyle='--',alpha=.65,
                        label=f'Ajuste local {LABELS[algo]} (pend.={fit[0]:.2f})')
        ax.set(xlabel='1 / (T/J)  [kB=J=1]',ylabel='ln(<tau> / MCSS)',title=f'N2.4 — activacion local | {dyn.capitalize()}, H/J={h:g}, L=32')
        ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.tight_layout();save_figure(fig,out,'N2_04_activacion_'+case_tag(dyn,h,0).rsplit('_T',1)[0],registered)
    write_rows(out/'N2_04_bootstrap_medias.csv',details)
    return len(details)


def plot_performance(thermal: pd.DataFrame, scaling: pd.DataFrame,out:Path, registered):
    for (dyn,h),sub in scaling.groupby(['dynamics','H'],sort=True):
        sub=sub.sort_values('L')
        fig,ax=plt.subplots(figsize=(8.4,5.1))
        ax.plot(sub.L,sub.standard_cpu_ns_per_attempt,marker='o',label='Standard: ns / intento')
        ax.plot(sub.L,sub.nfold_cpu_ns_per_event,marker='s',label='n-fold: ns / evento aceptado')
        ax.set(xlabel='L (N=L²)',ylabel='Tiempo de CPU histórico / operación [ns]',
               title=f'N2.5 — costo por operacion | {dyn.capitalize()}, H/J={h:g}, T/J={sub['T'].iloc[0]:g}')
        ax.set_xscale('log',base=2);ax.set_yscale('log');ax.grid(alpha=.25)
        ax.legend();fig.tight_layout()
        save_figure(fig,out,'N2_05_coste_L_'+case_tag(dyn,h,0).rsplit('_T',1)[0],registered)
    for dyn,subdyn in thermal.groupby('dynamics',sort=True):
        fig,ax=plt.subplots(figsize=(8.4,5.3))
        for h,sub in subdyn.groupby('H',sort=True):
            sub=sub.sort_values('standard_acceptance_fraction')
            if np.any(sub.standard_acceptance_fraction <= 0) or np.any(sub.speedup_standard_over_nfold<=0):
                raise ValueError('Speed-up o aceptacion no positivos')
            ax.plot(sub.standard_acceptance_fraction,sub.speedup_standard_over_nfold,'o-',label=f'H/J={h:g}')
        ax.axhline(1,linestyle='--',linewidth=.9,label='Igual coste')
        ax.set(xlabel='Aceptacion Standard [fraccion]',ylabel='Speed-up CPU = t Standard / t n-fold',
               title=f'N2.6 — aceleracion vs aceptacion | {dyn.capitalize()}, L=32')
        ax.set_xscale('log');ax.set_yscale('log');ax.grid(alpha=.25);ax.legend()
        fig.tight_layout();save_figure(fig,out,f'N2_06_speedup_vs_aceptacion_{dyn}',registered)
    perf=thermal[['dynamics','H','T','L','runs','standard_acceptance_fraction',
                  'speedup_standard_over_nfold','nfold_equiv_attempts_per_event']].copy()
    perf.to_csv(out/'N2_06_speedup_vs_aceptacion_datos.csv',index=False)


def validate_summary_vs_runs(groups:dict, summary:pd.DataFrame):
    for rec in summary.itertuples():
        std,nf=select_pair(groups,rec.dynamics,float(rec.H),float(rec.T),int(rec.L),float(rec.J))
        if len(std)!=int(rec.runs) or len(nf)!=int(rec.runs):
            raise ValueError('Numero de realizaciones no coincide con summary: '+str((rec.dynamics,rec.H,rec.T)))
        if not np.isclose(np.mean(std),float(rec.mean_tau_standard_mcss),rtol=1e-9):
            raise ValueError('Media Standard en summary distinta de CSV raw')
        if not np.isclose(np.mean(nf),float(rec.mean_tau_nfold_mcss),rtol=1e-9):
            raise ValueError('Media nfold en summary distinta de CSV raw')


def main(argv=None, root:Path=ROOT) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solo', choices=['all','distribuciones','rendimiento'],default='all')
    args=parser.parse_args(argv)
    root=Path(root).resolve()
    run_dir=create_run_dir(root,'nivel2')
    out=run_dir/'figuras_nivel2';out.mkdir()
    status='failed';note=''; registered=[]; initial=None; sources=[]
    try:
        initial=manifest_state(root)
        verify_frozen_integrity(root,initial)
        thermal_dir=root/'simulator/results/temperature_sweep'
        groups,sources=load_runs(thermal_dir/'raw')
        thermal=pd.read_csv(thermal_dir/'temperature_sweep_summary.csv')
        scaling=pd.read_csv(root/'simulator/results/scalability_L/scalability_summary.csv')
        validate_summary_vs_runs(groups,thermal)
        if args.solo in ('all','distribuciones'):
            count=plot_distributions(groups,out,registered)
        else:count=0
        if args.solo in ('all','rendimiento'):
            plot_thermal(groups,thermal,out,registered)
            plot_performance(thermal,scaling,out,registered)
        after=manifest_state(root)
        changed=[p for p,sha in initial.items() if after.get(p)!=sha]
        if changed:
            raise RuntimeError('Archivos historicos modificados: '+', '.join(changed[:10]))
        status='passed'
        note=f'Graficas: {len(registered)//2} figuras PNG+PDF. Casos distribucionales: {count}.'
    except Exception as exc:
        note=f'{type(exc).__name__}: {exc}\n{traceback.format_exc()}'
        print(note,file=sys.stderr)
    finally:
        for path in sorted(out.iterdir()):
            if path.is_file() and not any(x['path']==path.relative_to(run_dir).as_posix() for x in registered):
                registered.append({'name':path.stem,'kind':path.suffix.lstrip('.'), 'path':path.relative_to(run_dir).as_posix(), 'sha256':sha256(path)})
        with (run_dir/'MANIFEST_SALIDAS.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['name','kind','path','sha256']);w.writeheader();w.writerows(registered)
        record={'status':status,'mode':args.solo,'created_utc':datetime.now(timezone.utc).isoformat(),
                'baseline':'v1.0.0','snapshot':SNAPSHOT,'project_root':str(root),'python':sys.version,
                'platform':platform.platform(),'matplotlib':matplotlib.__version__,
                'numpy':np.__version__,'pandas':pd.__version__, 'sources':sources,
                'thermal_summary_sha256':sha256(root/'simulator/results/temperature_sweep/temperature_sweep_summary.csv'),
                'scalability_summary_sha256':sha256(root/'simulator/results/scalability_L/scalability_summary.csv'),
                'outputs':len(registered),'notes':note}
        (run_dir/'metadata.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# Bloque 2 - Graficas de Nivel 2','',f'**Estado:** {status.upper()}','',
               f'**Modo:** `{args.solo}`','',note,'',
               f'**Fuente:** release `v1.0.0`, snapshot `{SNAPSHOT}` (solo lectura).','',
               '## Familias','',
               '- N2.01 Supervivencia S(t) (lineal y semilog).',
               '- N2.02 ECDF y diferencia F_nfold-F_Standard.',
               '- N2.03 Densidad de log10(tau) con bins compartidos.',
               '- N2.04 ln(media tau) vs inversa T, bootstrap 95% (400 remuestreos).',
               '- N2.05 Tiempo por intento Standard y por evento n-fold (datos CPU historicos).',
               '- N2.06 Speed-up CPU vs aceptacion Standard (datos CPU historicos).','',
               'Los tres casos historicamente INCONCLUSIVE mantienen ese estado. El contraste KS en N2.02',
               'es descriptivo (p sin Holm); no prueba equivalencia. Los ajustes termicos son locales.',
               'Todas las 56 series de temperatura proceden de CSV por realizacion sin censura en la release.',
               'No se han generado simulaciones ni tiempos CPU nuevos.','',
               '## Directorio de resultados','',f'`{out}`','',
               'Archivos de salida en `MANIFEST_SALIDAS.csv` (SHA256).']
        (run_dir/'RESUMEN.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(f'Bloque 2: {status.upper()} | {out} | {note}',flush=True)
    return 0 if status=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
