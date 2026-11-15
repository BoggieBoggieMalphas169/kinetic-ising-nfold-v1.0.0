"""Nine families of physical Level-2 figures; never writes into historical folders."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import load_folder, mean_ci, add_row_csv, fresh_dir, sha256, write_json

plt.rcParams.update({'figure.dpi': 120, 'savefig.dpi': 175, 'axes.grid': True,
                     'grid.alpha': .22, 'font.size': 10})


def save(fig, target: Path, code: str, records: list, metadata: dict):
    png = target / f'{code}.png'
    pdf = target / f'{code}.pdf'
    fig.savefig(png, bbox_inches='tight')
    fig.savefig(pdf, bbox_inches='tight')
    plt.close(fig)
    records.append({'figure': code, 'png': png.name, 'pdf': pdf.name, **metadata})


def only_complete(df):
    if not bool((df.reached_M0 == 1).all()):
        raise ValueError(f'Incomplete/possibly censored runs in {df.attrs.get("source")}. '
                         'Do not naively interpret completed subsample as the full lifetime distribution.')
    return df.time_mcss.to_numpy(dtype=float)


def get_pairs(d: dict, L: int, T: float, H: float, dyn: str, J: float = 1.0):
    base = (L, round(T, 9), round(J, 9), round(H, 9), dyn)
    return d.get(base + ('standard',)), d.get(base + ('nfold',))


def kmsample(x):
    """For uncensored first-passage lifetimes: exact empirical survival P(tau>t)."""
    unique, counts = np.unique(np.sort(x), return_counts=True)
    survival = 1 - np.cumsum(counts) / len(x)
    return np.r_[0, unique], np.r_[1, survival]


def distro_figures(temperature: dict, out: Path, records: list, provenance: dict, suffix: str = ''):
    specs = [(32, .8, 1.0, -.75, 'glauber'), (32, .9, 1.0, -.75, 'glauber'),
             (32, .8, 1.0, -.75, 'metropolis'), (32, 1.5, 1.0, -.75, 'glauber')]
    if suffix:
        specs = sorted({(k[0],k[1],k[2],k[3],k[4]) for k in temperature
                        if k[5]=='standard' and (k[:5]+('nfold',)) in temperature},
                       key=lambda r: (r[4], r[3], r[0], r[1]))
    diagnostic = []
    for L, T, J, H, dyn in specs:
        a, b = get_pairs(temperature, L, T, H, dyn, J)
        if a is None or b is None:
            print(f'SKIP distributions: missing pair {L=} {T=} {H=} {dyn=}')
            continue
        try: xs, xn = only_complete(a), only_complete(b)
        except ValueError as exc:
            print('SKIP incomplete distribution:', exc)
            continue
        for d in (a, b): provenance[d.attrs['source']] = sha256(Path(d.attrs['source']))
        base = f'{dyn}_L{L}_T{T:g}_Hm{abs(H):g}'.replace('.', 'p')
        meta = {'L': L, 'T': T, 'J': J, 'H': H, 'dynamics': dyn,
                'n_standard': len(xs), 'n_nfold': len(xn)}
        # survival P(tau>t) -- no parametric model assumed
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for x, label in [(xs, 'Standard'), (xn, 'n-fold')]:
            tt, yy = kmsample(x)
            ax.step(tt, yy, where='post', label=f'{label} (n={len(x)})')
        ax.set(xlabel='Tiempo de primer paso τ (MCSS)', ylabel='S(t) = P(τ > t)',
               title=f'Supervivencia | {dyn}, L={L}, T={T:g}, H={H:g}')
        ax.set_ylim(-.02, 1.02); ax.legend(); save(fig, out, f'01_supervivencia_{base}{suffix}', records, meta)
        # empirical CDF and pointwise differences
        fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1]})
        xx = np.unique(np.r_[xs, xn])
        fstd = np.searchsorted(np.sort(xs), xx, side='right') / len(xs)
        fnfo = np.searchsorted(np.sort(xn), xx, side='right') / len(xn)
        for arr, lbl in [(fstd, 'Standard'), (fnfo, 'n-fold')]:
            axes[0].step(xx, arr, where='post', label=lbl)
        diff = fnfo - fstd
        axes[1].step(xx, diff, where='post', label='F_nfold - F_Standard')
        axes[1].axhline(0, lw=1, c='black')
        axes[0].set_ylabel('F(t)'); axes[0].legend()
        axes[1].set_ylabel('ΔF(t)'); axes[1].set_xlabel('τ (MCSS)')
        axes[0].set_title(f'ECDF y diferencia | {dyn}, L={L}, T={T:g}, H={H:g}')
        fig.tight_layout()
        save(fig, out, f'02_ecdf_diferencia_{base}{suffix}', records, {**meta, 'KS_D': float(np.max(np.abs(diff)))})
        # histogram of base-10 logarithm; identical bins for fair density comparison
        lo = float(min(xs.min(), xn.min())); hi = float(max(xs.max(), xn.max()))
        if lo <= 0: raise ValueError('Nonpositive lifetime cannot be logged')
        logs, logn = np.log10(xs), np.log10(xn)
        bounds = np.linspace(min(logs.min(), logn.min()), max(logs.max(), logn.max()) + 1e-9, 40)
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        ax.hist(logs, bins=bounds, density=True, alpha=.42, label='Standard')
        ax.hist(logn, bins=bounds, density=True, alpha=.42, label='n-fold')
        ax.set(xlabel='log10(τ / MCSS)', ylabel='Densidad en escala log10',
               title=f'Distribución logarítmica de vidas | {dyn}, L={L}, T={T:g}, H={H:g}')
        ax.legend(); save(fig, out, f'03_hist_logtau_{base}{suffix}', records, meta)
        diagnostic.append({**meta, 'ks_D': float(np.max(np.abs(diff))),
                           'mean_tau_standard': float(xs.mean()), 'mean_tau_nfold': float(xn.mean()),
                           'q99_tau_standard': float(np.quantile(xs, .99)),
                           'q99_tau_nfold': float(np.quantile(xn, .99))})
    if diagnostic: add_row_csv(out / f'diagnostico_distribuciones{suffix}.csv', diagnostic)


def arrhenius_figures(temperature: dict, out: Path, records: list, provenance: dict, B: int, suffix: str = ''):
    rows = []
    groups = sorted({(k[0], k[2], k[3], k[4]) for k in temperature})
    for L, J, H, dyn in groups:
        if not suffix and (L != 32 or J != 1 or H not in (-.75,-3.0)):
            continue  # the frozen Prompt-6 thermal sweep is L32/J1
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        found = False
        for alg, label in [('standard','Standard'), ('nfold','n-fold')]:
            items = []
            for k, d in temperature.items():
                size, T, coupling, field, dynamic, algorithm = k
                if (size, coupling, field, dynamic, algorithm) != (L,J,H,dyn,alg):
                    continue
                try: vals = only_complete(d)
                except ValueError as exc:
                    print('SKIP incomplete thermal point:', exc)
                    continue
                m, lo, hi = mean_ci(vals, 2741 + int(T * 100) + (1 if alg == 'nfold' else 0), B)
                items.append((J/T, m, lo, hi))
                rows.append({'dynamics':dyn, 'H':H, 'L':L, 'J':J, 'T':T,
                             'algorithm':alg, 'n':len(vals), 'mean_tau_mcss':m,
                             'ci95_lo':lo, 'ci95_hi':hi,
                             'source':d.attrs['source']})
                provenance[d.attrs['source']] = sha256(Path(d.attrs['source']))
            if len(items) < 2: continue
            found = True
            items.sort()
            x, y, low, high = map(np.asarray, zip(*items))
            ax.plot(x, np.log(y), 'o-', label=label)
            ax.fill_between(x, np.log(low), np.log(high), alpha=.14)
        if found:
            ax.set(xlabel='J / T (kB = 1)', ylabel='ln(<τ>/MCSS)',
                   title=f'Activación local (sin ajuste impuesto) | {dyn}, L={L}, H/J={H/J:g}')
            ax.legend()
            name=f'06_arrhenius_{dyn}_L{L}_J{J:g}_Hm{abs(H):g}'.replace('.','p')+suffix
            save(fig,out,name,records,{'H':H,'L':L,'J':J,'dynamics':dyn,
                 'interpretation':'No se presupone linealidad'})
        else: plt.close(fig)
    if rows: add_row_csv(out / f'tabla_activacion_bootstrap{suffix}.csv', rows)


def field_figures(folder: Path, out: Path, records: list, provenance: dict, B: int):
    if not folder.exists(): return
    rows = []
    for subdir in sorted(folder.glob('campo_*/raw')):
        try: data = load_folder(subdir)
        except ValueError as e:
            print(f'SKIP invalid field campaign {subdir}: {e}'); continue
        for k, df in data.items():
            try: x = only_complete(df)
            except ValueError as e:
                print(f'SKIP incomplete field data: {e}'); continue
            m, lo, hi = mean_ci(x, 991 + round(abs(k[3])*1000), B)
            rows.append({'campaign':subdir.parent.name, 'L':k[0], 'T':k[1], 'J':k[2], 'H':k[3],
                         'dynamics':k[4], 'algorithm':k[5], 'n':len(x),
                         'mean_tau':m, 'ci_lo':lo, 'ci_hi':hi,
                         'source':df.attrs['source']})
            provenance[df.attrs['source']] = sha256(Path(df.attrs['source']))
    if not rows: return
    add_row_csv(out / 'tabla_campo_bootstrap.csv', rows)
    d = pd.DataFrame(rows)
    for (campaign,L,T,J,dyn), group in d.groupby(['campaign','L','T','J','dynamics']):
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for alg, label in [('standard','Standard'),('nfold','n-fold')]:
            sub = group[group.algorithm == alg].sort_values('H', ascending=False)
            if sub.empty: continue
            x = np.abs(sub.H.to_numpy(dtype=float)) / float(J); y = sub.mean_tau.to_numpy(dtype=float)
            lo = sub.ci_lo.to_numpy(dtype=float); hi = sub.ci_hi.to_numpy(dtype=float)
            ax.errorbar(x, y, yerr=[y-lo,hi-y], fmt='o-', capsize=3, label=label)
        ax.set(xlabel='|H| / J', ylabel='<τ> (MCSS)', yscale='log',
               title=f'Vida media vs campo | {dyn}, L={L}, T/J={T/J:g}')
        ax.legend(); save(fig, out, f'07_campo_{campaign}_{dyn}', records,
                           {'campaign':campaign,'L':int(L),'T':float(T),'J':float(J),'dynamics':dyn})


def scaling_figures(scaling: dict, out: Path, records: list, provenance: dict, suffix: str = ''):
    records_csv = []
    for k, std in scaling.items():
        L,T,J,H,dyn,alg = k
        if alg != 'standard': continue
        nf = scaling.get((L,T,J,H,dyn,'nfold'))
        if nf is None: continue
        if not (std.reached_M0.eq(1).all() and nf.reached_M0.eq(1).all()):
            print('SKIP incomplete size data', k); continue
        s_attempts = std.attempts.sum()
        n_events = nf.events.sum()
        s_cpu = std.cpu_seconds.sum()
        n_cpu = nf.cpu_seconds.sum()
        if min(s_attempts,n_events,s_cpu,n_cpu) <= 0: continue
        records_csv.append({'dynamics':dyn, 'L':L, 'T':T, 'H':H,
                            'n_std':len(std),'n_nfold':len(nf),
                            'standard_ns_attempt':1e9*s_cpu/s_attempts,
                            'nfold_ns_event':1e9*n_cpu/n_events,
                            'standard_acceptance':std.accepted.sum()/s_attempts,
                            'speedup_std_over_nfold':(s_cpu/len(std))/(n_cpu/len(nf)),
                            'source_standard':std.attrs['source'],
                            'source_nfold':nf.attrs['source']})
        for df in (std, nf): provenance[df.attrs['source']] = sha256(Path(df.attrs['source']))
    if not records_csv: return
    add_row_csv(out / f'tabla_costes_y_aceptacion{suffix}.csv', records_csv)
    data = pd.DataFrame(records_csv)
    for (H, dyn), g in data.groupby(['H','dynamics']):
        g = g.sort_values('L')
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        ax.plot(g.L, g.standard_ns_attempt,'o-',label='Standard: ns/intento')
        ax.plot(g.L, g.nfold_ns_event,'s-',label='n-fold: ns/evento')
        ax.set(xlabel='Tamaño L', ylabel='Coste medio de operación (ns)', xscale='log',
               title=f'Coste por operación | {dyn}, T={float(g['T'].iloc[0]):g}, H={H:g}')
        ax.legend()
        save(fig,out,(f'08_costo_L_{dyn}_Hm{abs(H):g}'.replace('.','p') + suffix),records,
             {'H':float(H),'dynamics':dyn,'note':'Operaciones diferentes, no velocidad total'})
    for dyn, g in data.groupby('dynamics'):
        fig,ax=plt.subplots(figsize=(7.2,4.8))
        for H, sub in g.groupby('H'):
            sub=sub.sort_values('L')
            sc=ax.scatter(sub.standard_acceptance,sub.speedup_std_over_nfold,
                          c=sub.L,cmap='viridis',vmin=data.L.min(),vmax=data.L.max(),
                          label=f'H={H:g}',s=65,marker='o' if H < -1 else 's')
        ax.axhline(1, ls='--',c='black',lw=1,label='Cruce S=1')
        ax.set(xlabel='Aceptación Standard (aceptados/intentos)',
               ylabel='Speed-up CPU = tStandard / tn-fold',yscale='log',
               title=f'Cruce de eficiencia y aceptación | {dyn}, barrido en L')
        ax.legend(); fig.colorbar(sc,ax=ax,label='L')
        save(fig,out,f'09_speedup_vs_aceptacion_{dyn}{suffix}',records,{'dynamics':dyn})


def trace_figures(trace_root: Path,out:Path,records:list,provenance:dict):
    if not trace_root.exists(): return
    for tdir in sorted(trace_root.glob('traza_*')):
        csvs = list(tdir.glob('*_trace.csv'))
        if not csvs: continue
        fig, axes = plt.subplots(2,1,figsize=(7.6,6.2),sharex=True)
        plotted = False
        for path in sorted(csvs):
            df=pd.read_csv(path)
            if df.empty: continue
            label=str(df.algorithm.iloc[0]); plotted=True
            x=df.time_mcss.to_numpy(); y=df.m_per_spin.to_numpy(); e=df.e_per_spin.to_numpy()
            if np.any(np.diff(x)<0): raise ValueError(f'Nonmonotonic time in {path}')
            axes[0].plot(x,y,label=label,linewidth=1.3)
            axes[1].plot(x,e,label=label,linewidth=1.3)
            provenance[str(path)] = sha256(path)
        if plotted:
            axes[0].set(ylabel='M/N',title=f'Trayectorias de escape (realizaciones independientes) | {tdir.name}')
            axes[1].set(xlabel='Tiempo MCSS',ylabel='E/N')
            axes[0].legend();axes[1].legend();fig.tight_layout()
            save(fig,out,f'05_series_{tdir.name}',records,{'campaign':tdir.name})
        else: plt.close(fig)
        # Visualise lattice frames, annotate each with *actual* MCSS, not uniformly-spaced time.
        for index in tdir.glob('*_frame_index.csv'):
            ind=pd.read_csv(index)
            if ind.empty: continue
            if len(ind)>12:
                indices=np.unique(np.round(np.linspace(0,len(ind)-1,12)).astype(int))
                ind=ind.iloc[indices]
            nr=len(ind); cols=min(4,nr); rows=int(np.ceil(nr/cols))
            fig, axes=plt.subplots(rows,cols,figsize=(3.1*cols,3.2*rows),squeeze=False)
            for ax in axes.flat: ax.axis('off')
            for ax,(_,row) in zip(axes.flat,ind.iterrows()):
                p=Path(str(row.file))
                if not p.exists(): p=index.parent/p.name # portable after moving/extracting ZIP
                m=np.loadtxt(p,delimiter=',',dtype=int)
                if m.ndim!=2 or m.shape[0]!=m.shape[1] or not np.isin(m,[-1,1]).all():
                    raise ValueError(f'Invalid spin lattice: {p}')
                ax.imshow(m,vmin=-1,vmax=1,cmap='coolwarm',interpolation='nearest',origin='upper')
                ax.set_title(f't={row.time_mcss:.4g} MCSS | m={row.m_per_spin:.2f}',fontsize=9)
                ax.axis('off'); provenance[str(p)]=sha256(p)
            fig.suptitle(f'Nucleación: snapshots reales | {tdir.name}',y=1.01)
            fig.tight_layout()
            save(fig,out,f'04_snapshots_{tdir.name}_{index.stem}',records,
                 {'campaign':tdir.name,'sampled_frames':nr,'frame_index':str(index)})
            provenance[str(index)] = sha256(index)


def main():
    ap=argparse.ArgumentParser(description='Regenerar Nivel 2 sin cambiar datos de referencia')
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    ap.add_argument('--outdir',type=Path,default=None)
    ap.add_argument('--bootstrap',type=int,default=400)
    args=ap.parse_args(); root=args.root.resolve()
    if args.bootstrap < 20: ap.error('--bootstrap must be >=20')
    out = args.outdir.resolve() if args.outdir else fresh_dir(root/'results/nivel2/graficas','figuras')
    if any(out.iterdir()) if out.exists() else False:
        raise SystemExit(f'Output directory must be empty to protect prior plots: {out}')
    out.mkdir(parents=True,exist_ok=True)
    temperature=load_folder(root/'simulator/results/temperature_sweep/raw')
    scaling=load_folder(root/'simulator/results/scalability_L/raw')
    records=[]; provenance={}
    distro_figures(temperature,out,records,provenance)
    arrhenius_figures(temperature,out,records,provenance,args.bootstrap)
    field_figures(root/'results/nivel2/medidas/campo',out,records,provenance,args.bootstrap)
    scaling_figures(scaling,out,records,provenance)
    trace_figures(root/'results/nivel2/medidas/trazas',out,records,provenance)
    # Campaign-specific figures: never mix ensembles from different campaigns.
    for folder in sorted((root/'results/nivel2/medidas/temperatura').glob('temperatura_*/raw')):
        campaign=folder.parent
        if not (campaign/'manifest.json').exists(): continue
        data=load_folder(folder)
        tag='_'+campaign.name
        distro_figures(data,out,records,provenance,tag)
        arrhenius_figures(data,out,records,provenance,args.bootstrap,tag)
    for folder in sorted((root/'results/nivel2/medidas/tamano').glob('tamano_*/raw')):
        campaign=folder.parent
        if not (campaign/'manifest.json').exists(): continue
        scaling_figures(load_folder(folder),out,records,provenance,'_'+campaign.name)
    write_json(out/'manifest_figuras.json',{'version':'nivel2-v1','figures':records,
              'sources_sha256':{str(Path(k).resolve().relative_to(root)):v for k,v in provenance.items()}, 'bootstrap_resamples':args.bootstrap,
              'notes':['MCSS = equivalent attempts / L^2',
                       'Bootstrap percentile 95% (independent runs, within each algorithm).',
                       'Only complete first-passage samples enter mean/ECDF/histogram.',
                       'Operational times from C clock(); not hardware-independent.',
                       'Distributions and Arrhenius use historical temperature-sweep raw CSV.',
                       'No automatic Arrhenius fit or assumption of a universal slope.']})
    print(f'[NIVEL2] {len(records)} figures created (PNG+PDF) in {out}')
    print('[NIVEL2] Figure families from optional new campaigns appear after collecting data.')


if __name__=='__main__': main()
