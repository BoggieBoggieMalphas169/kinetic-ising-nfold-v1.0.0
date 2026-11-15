"""Bloque 4: graficas temporales y mapas de dominios de trazas B3 verificadas.

NO ejecuta el motor C, NO altera el snapshot y NO genera animaciones.
El tiempo del eje X es MCSS, no el indice de fotograma ni numero de eventos.
Se usan todos los eventos aceptados; los rechazos figuran como esperas.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np

from .validar_baseline import ROOT, create_run_dir, manifest_state, sha256
from .trazas_b3 import spin_decode, validate_directory, validate_pair

FAMILIES = ('standard', 'nfold')
DYNAMICS = ('glauber', 'metropolis')
SPIN_MAP = ListedColormap(['#db7860', '#447bb0'])
SPIN_NORM = BoundaryNorm([-1.5, 0, 1.5], ncolors=2)


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f'CSV vacio: {path}')
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f'No hay registros que escribir: {path.name}')
    with path.open('x', encoding='utf-8', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def check_baseline(root: Path) -> dict[str, str]:
    """Exige hashes historicos validos, no basta una comparacion antes/despues."""
    before = manifest_state(root)
    with (root / 'release' / 'release_manifest.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if before.get(row['path']) != row['sha256']:
                raise ValueError('La release historica no coincide con manifiesto: ' + row['path'])
    return before


def select_source(root: Path, directory: str | Path | None) -> Path:
    parent = (root / 'results' / 'practica_cierre').resolve()
    if directory:
        requested = Path(directory)
        if not requested.is_absolute():
            requested = (root / requested)
        path = requested.resolve()
        if not path.is_relative_to(parent):
            raise ValueError('La fuente debe estar dentro de results/practica_cierre/')
        if path.parent != parent:
            raise ValueError('Indica la carpeta de campana B3, no un subdirectorio')
    else:
        candidates = sorted((p for p in parent.iterdir()
                             if p.is_dir() and (p / 'MANIFEST_B3.json').is_file()),
                            key=lambda p: p.name, reverse=True)
        if not candidates:
            raise FileNotFoundError('No existen campanas B3. Ejecuta antes el bloque 3 (opcion 7).')
        path = candidates[0]
    if not (path / 'MANIFEST_B3.json').is_file():
        raise ValueError(f'No es una campana de trazas B3: {path}')
    return path


def select_b4(root: Path, directory: str | Path | None) -> Path:
    parent = (root / 'results' / 'practica_cierre').resolve()
    if directory:
        requested = Path(directory)
        path = (requested if requested.is_absolute() else root / requested).resolve()
        if not path.is_relative_to(parent) or path.parent != parent:
            raise ValueError('La carpeta B4 debe estar bajo results/practica_cierre/')
    else:
        candidates = sorted((p for p in parent.iterdir()
                             if p.is_dir() and (p / 'MANIFEST_B4.json').is_file()),
                            key=lambda p: p.name, reverse=True)
        if not candidates:
            raise FileNotFoundError('No hay productos B4 para validar.')
        path = candidates[0]
    if not (path / 'MANIFEST_B4.json').is_file():
        raise ValueError('No contiene MANIFEST_B4.json')
    return path


def load_case(case_path: Path) -> dict[str, Any]:
    prefix = case_path / 'trayectoria'
    report = validate_pair(prefix, case_path / 'resumen_trazado.csv')
    frames = csv_rows(case_path / 'trayectoria_frames.csv')
    with (case_path / 'trayectoria_events.csv').open('r', encoding='utf-8', newline='') as handle:
        events = list(csv.DictReader(handle))  # 0 eventos = CSV solo con cabecera
    summary = [r for r in csv_rows(case_path / 'resumen_trazado.csv') if int(r['run']) == report['run']][0]
    n = report['L'] ** 2
    # La serie por eventos tiene resolucion completa, a diferencia de los frames
    # espaciados cada K eventos. No se interpola ningun estado fisico.
    initial = frames[0]
    series = [dict(source='initial', event=0, attempts=0, time_mcss=0.,
                   M=int(initial['M']), E=float(initial['E']),
                   m_per_spin=int(initial['M']) / n, e_per_spin=float(initial['E']) / n)]
    for r in events:
        attempts = int(r['attempts']); m = int(r['M']); e = float(r['E'])
        series.append(dict(source='accepted_event', event=int(r['event']), attempts=attempts,
                           time_mcss=attempts / n, M=m, E=e,
                           m_per_spin=m / n, e_per_spin=e / n))
    # En una corrida censurada puede haber intentos rechazados tras el ultimo flip.
    last = frames[-1]
    if int(last['attempts']) > series[-1]['attempts']:
        series.append(dict(source='terminal_no_flip', event=int(last['events']),
                           attempts=int(last['attempts']), time_mcss=int(last['attempts']) / n,
                           M=int(last['M']), E=float(last['E']),
                           m_per_spin=int(last['M']) / n, e_per_spin=float(last['E']) / n))
    if series[-1]['attempts'] != int(last['attempts']):
        raise ValueError('Reloj final distinto de ultimo fotograma')
    if len(series) != len(events) + 1 + int(series[-1]['source'] == 'terminal_no_flip'):
        raise ValueError('Longitud inesperada de la serie')
    if any(b['attempts'] <= a['attempts'] for a, b in zip(series, series[1:])):
        raise ValueError('El tiempo no crece entre eventos')
    if not math.isclose(series[-1]['time_mcss'], float(summary['time_mcss']), rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError('Tiempo MCSS terminal incoherente')
    return {'name': case_path.name, 'case_dir': case_path, 'report': report,
            'frames': frames, 'events': events, 'summary': summary, 'series': series,
            'censored': not bool(int(summary['reached_M0']))}


def select_frames_by_time(frames: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    """Escoge la ULTIMA instantanea anterior a cada tiempo objetivo.

    No inventa configuraciones ni convierte el indice de frame en tiempo uniforme.
    Las repetidas se eliminan; inicial y final se conservan.
    """
    if not 2 <= count <= 12:
        raise ValueError('El numero de paneles debe estar entre 2 y 12')
    times = np.array([float(r['time_mcss']) for r in frames])
    if not np.all(np.isfinite(times)) or np.any(np.diff(times) < 0):
        raise ValueError('Frames con reloj no monotono')
    targets = np.linspace(0, times[-1], count)
    chosen = {0, len(frames) - 1}
    for target in targets[1:-1]:
        chosen.add(int(np.searchsorted(times, target, side='right') - 1))
    return [frames[i] for i in sorted(chosen)]


def _save(fig, out: Path, stem: str, dpi: int=160) -> list[Path]:
    paths = []
    for fmt in ('png', 'pdf'):
        path = out / f'{stem}.{fmt}'
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=dpi, bbox_inches='tight',
                    metadata=({'Title': stem} if fmt == 'pdf' else None))
        paths.append(path)
    plt.close(fig)
    return paths


def _subtitle(case: dict[str, Any]) -> str:
    r = case['report']; status = 'CENSURADA' if case['censored'] else 'escape M=0'
    return f"{r['algorithm']} + {r['dynamics']}  |  L={r['L']}, T/J={r['T']/r['J']:.3g}, H/J={r['H']/r['J']:.3g}  |  {status}"


def plot_series(case: dict[str, Any], out: Path, dpi: int=160) -> list[Path]:
    ss = case['series']
    t = np.array([r['time_mcss'] for r in ss])
    m = np.array([r['m_per_spin'] for r in ss])
    en = np.array([r['e_per_spin'] for r in ss])
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    axes[0].step(t, m, where='post', linewidth=1.15, label='m = M/N')
    axes[0].axhline(0, color='0.45', linestyle=':', linewidth=1)
    axes[0].set(ylabel='Magnetizacion por espin M/N')
    axes[1].step(t, en, where='post', linewidth=1.15, label='e = E/N')
    axes[1].set(xlabel='Tiempo Monte Carlo (MCSS = intentos equivalentes / N)',
                ylabel='Energia por espin E/N')
    for ax in axes:
        ax.grid(alpha=0.18)
        if t[-1] == 0: ax.set_xlim(-0.1, 0.1)
    fig.suptitle('B4 - Evolucion temporal de una realizacion\n' + _subtitle(case), fontsize=11)
    fig.text(.5, .015, 'Saltos entre eventos aceptados; los rechazos no cambian el estado. No es un promedio de ensemble.',
             ha='center', fontsize=8, color='0.35')
    fig.tight_layout(rect=(0,.035,1,.90))
    return _save(fig, out, 'B4_01_series_' + case['name'],dpi)


def plot_mosaic(case: dict[str, Any], out: Path, count: int, dpi: int=160) -> tuple[list[Path], list[dict]]:
    selection = select_frames_by_time(case['frames'], count)
    L = case['report']['L']
    fig, axes = plt.subplots(1, len(selection), figsize=(3.05*len(selection), 3.9), squeeze=False)
    records = []
    for ax, f in zip(axes[0], selection):
        image = np.array(spin_decode(f['spin_bits'], L), dtype=np.int8).reshape(L,L)
        ax.imshow(image, cmap=SPIN_MAP, norm=SPIN_NORM, interpolation='nearest', origin='upper')
        ax.set_title(f"frame {f['frame']}  |  t={float(f['time_mcss']):.4g} MCSS\nm={int(f['M'])/(L*L):+.3f}   e={float(f['E'])/(L*L):+.3f}", fontsize=8.8)
        ax.set_xticks([]); ax.set_yticks([])
        records.append({'case':case['name'], 'frame':int(f['frame']), 'event':int(f['events']),
                        'attempts':int(f['attempts']), 'time_mcss':float(f['time_mcss']),
                        'M':int(f['M']), 'E':float(f['E']), 'spin_bits_sha256':hashlib.sha256(f['spin_bits'].encode()).hexdigest()})
    fig.suptitle('B4 - Instantaneas observadas (no equiespaciadas)\n' + _subtitle(case), fontsize=11)
    fig.text(.5,.015,'Naranja: -1 (fase favorecida por H<0). Azul: +1. Seleccion por tiempo; instantanea anterior al objetivo.',
             fontsize=8, ha='center', color='0.3')
    fig.tight_layout(rect=(0,.05,1,.84))
    return _save(fig, out, 'B4_02_instantaneas_' + case['name'],dpi), records


def _same_physics(a: dict, b: dict) -> bool:
    x=a['report']; y=b['report']
    return x['L']==y['L'] and all(math.isclose(x[k],y[k],rel_tol=0,abs_tol=1e-12) for k in ('T','J','H')) and x['dynamics']==y['dynamics']


def plot_comparison(a: dict, b: dict, out: Path, dpi: int=160) -> list[Path]:
    if not _same_physics(a,b) or {a['report']['algorithm'],b['report']['algorithm']} != {'standard','nfold'}:
        raise ValueError('No se pueden comparar trayectorias de distinta fisica o mismo algoritmo')
    fig, axes = plt.subplots(1,2,figsize=(11,4.3))
    for case in [a,b]:
        ss=case['series']; t=[r['time_mcss'] for r in ss]
        tag=case['report']['algorithm'] + (' (censurada)' if case['censored'] else '')
        axes[0].step(t,[r['m_per_spin'] for r in ss],where='post',label=tag,linewidth=1.15)
        axes[1].step(t,[r['e_per_spin'] for r in ss],where='post',label=tag,linewidth=1.15)
    axes[0].axhline(0,color='0.4',linestyle=':',linewidth=1)
    for ax, ylabel in zip(axes, ['M/N','E/N']):
        ax.set(xlabel='Tiempo (MCSS)',ylabel=ylabel)
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('B4 - Comparacion ilustrativa de trayectorias independientes\n'
                 f"{a['report']['dynamics']} | L={a['report']['L']}, T/J={a['report']['T']/a['report']['J']:.3g}, H/J={a['report']['H']/a['report']['J']:.3g}", fontsize=11)
    fig.text(.5,.01,'No deben coincidir trayectoria a trayectoria; esto NO demuestra equivalencia estadistica.',
             fontsize=8,ha='center',color='0.35')
    fig.tight_layout(rect=(0,.04,1,.88))
    return _save(fig,out,'B4_03_comparacion_' + a['report']['dynamics'],dpi)


def plot_final_gallery(cases: dict[str, dict], out: Path, dpi: int=160) -> list[Path] | None:
    if len(cases) != 4:
        return None
    first = next(iter(cases.values()))['report']
    if any(c['report']['L'] != first['L'] or any(not math.isclose(c['report'][k],first[k],rel_tol=0,abs_tol=1e-12)
           for k in ('T','J','H')) for c in cases.values()):
        return None
    fig, axes=plt.subplots(2,2,figsize=(8,8))
    for i,algo in enumerate(FAMILIES):
        for j,dyn in enumerate(DYNAMICS):
            c=cases[f'{algo}_{dyn}']; ax=axes[i,j]
            f=c['frames'][-1]
            ax.imshow(np.array(spin_decode(f['spin_bits'], first['L'])).reshape(first['L'],first['L']),
                      cmap=SPIN_MAP,norm=SPIN_NORM,interpolation='nearest')
            ax.set(title=f"{algo} + {dyn} | t={float(f['time_mcss']):.4g} MCSS\n"
                         + ('CENSURADA' if c['censored'] else 'M=0'))
            ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('B4 - Estados terminales de realizaciones independientes\n'
                 'Mismos parametros, distintas historias estocasticas',fontsize=12)
    fig.tight_layout(rect=(0,.025,1,.91))
    return _save(fig,out,'B4_04_galeria_estados_finales',dpi)


def _verify_output_hashes(path: Path) -> list[dict]:
    manifest = csv_rows(path / 'SHA256_B4.csv')
    for row in manifest:
        file=(path / row['path']).resolve()
        if not file.is_relative_to(path.resolve()) or not file.is_file():
            raise ValueError('Ruta de salida B4 invalida')
        if sha256(file) != row['sha256']:
            raise ValueError('B4: hash incorrecto en ' + row['path'])
    return manifest


def generate(root: Path, source: Path, dpi: int=160, panels: int=5) -> Path:
    # La validacion de B3 es previa a la creacion del directorio final de B4.
    if not 72 <= dpi <= 300 or not 2 <= panels <= 12:
        raise ValueError('dpi o panels fuera de los limites admitidos')
    before = check_baseline(root)
    reports = validate_directory(source)
    if not reports:
        raise ValueError('No hay casos de traza en el manifiesto B3')
    source_state = {p.name:sha256(p) for p in [source/'MANIFEST_B3.json',source/'SHA256_NUEVAS_SALIDAS.csv']}
    case_dirs = {r['algorithm']+'_'+r['dynamics']:source/(r['algorithm']+'_'+r['dynamics']) for r in reports}
    # Validacion de todo lo que vamos a dibujar antes de crear productos nuevos.
    cases = {key:load_case(p) for key,p in sorted(case_dirs.items())}
    directory=create_run_dir(root,'visualizacion_b4')
    out=directory/'figuras_b4'; out.mkdir()
    summary=[]; chosen=[]; paths=[]; status='FAIL'
    try:
        for key, case in cases.items():
            write_csv(out/f'B4_00_datos_series_{key}.csv',case['series'])
            paths.append(out/f'B4_00_datos_series_{key}.csv')
            paths.extend(plot_series(case,out,dpi))
            pic,records=plot_mosaic(case,out,panels,dpi)
            paths.extend(pic); chosen.extend(records)
            report=case['report']
            summary.append({**{k:report[k] for k in ('algorithm','dynamics','L','T','J','H','seed','stream','run','frames','events','attempts','time_mcss','final_M','reached_M0')},
                            'censored':case['censored'],'original_frames_sha256':sha256(case['case_dir']/'trayectoria_frames.csv'),
                            'original_events_sha256':sha256(case['case_dir']/'trayectoria_events.csv'),
                            'terminal_energy_per_spin':case['series'][-1]['e_per_spin']})
        write_csv(out/'B4_05_frames_seleccionados.csv',chosen)
        write_csv(out/'B4_06_resumen_fisico.csv',summary)
        paths.extend([out/'B4_05_frames_seleccionados.csv',out/'B4_06_resumen_fisico.csv'])
        for dyn in DYNAMICS:
            if f'standard_{dyn}' in cases and f'nfold_{dyn}' in cases:
                if _same_physics(cases[f'standard_{dyn}'], cases[f'nfold_{dyn}']):
                    paths.extend(plot_comparison(cases[f'standard_{dyn}'],cases[f'nfold_{dyn}'],out,dpi))
        gallery = plot_final_gallery(cases,out,dpi)
        if gallery: paths.extend(gallery)
        status='PASS'
    finally:
        historical_unchanged = manifest_state(root) == before
        if not historical_unchanged: status='FAIL'
        source_unchanged = all(sha256(source/name)==v for name,v in source_state.items())
        if not source_unchanged: status='FAIL'
        metadata={'status':status, 'created_utc':datetime.now(timezone.utc).isoformat(),
                  'block':'B4', 'source_b3':source.relative_to(root).as_posix(),
                  'source_b3_manifest_sha256':source_state['MANIFEST_B3.json'],
                  'source_b3_hashes_sha256':source_state['SHA256_NUEVAS_SALIDAS.csv'],
                  'source_b3_validation':'PASS', 'historical_manifest_unchanged':historical_unchanged,
                  'source_b3_unchanged':source_unchanged,'python':sys.version.splitlines()[0],
                  'platform':platform.platform(), 'dpi':dpi,'selected_panels_requested':panels,
                  'cases':summary,'figures':len([p for p in paths if p.suffix=='.png'])}
        (directory/'MANIFEST_B4.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        lines=['# Bloque 4: series temporales y nucleacion', '',f'**Estado: {status}**','',
               f'Fuente B3: `{source.relative_to(root).as_posix()}`',
               f'Casos: {len(cases)} | Figuras: {metadata["figures"]} (PNG + PDF)','','## Salidas',
               '- B4_00: series por TODOS los eventos aceptados y tiempo en MCSS.',
               '- B4_01: curvas en escalera de M/N y E/N por realizacion.',
               '- B4_02: instantaneas reales seleccionadas por tiempo (no equidistantes).',
               '- B4_03: comparaciones ilustrativas de trayectorias independientes.',
               '- B4_04: mosaico de estados terminales, si hay cuatro casos compatibles.',
               '- B4_05 y B4_06: tabla de frames seleccionados y resumen fisico.', '',
               '**No son promedios de ensemble, ni animaciones.** Los tiempos mostrados son MCSS,',
               'NO segundos reales. Una trayectoria censurada NO equivale a escape.','',
               'Motor C original y snapshot historico: sin cambios.']
        (directory/'RESUMEN.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        with (directory/'SHA256_B4.csv').open('x',newline='',encoding='utf-8') as handle:
            writer=csv.writer(handle); writer.writerow(['path','sha256'])
            for p in sorted([*paths, directory/'MANIFEST_B4.json', directory/'RESUMEN.md']):
                if p.exists():writer.writerow([p.relative_to(directory).as_posix(),sha256(p)])
        if not historical_unchanged: raise ValueError('B4 altero el manifiesto historico')
        if not source_unchanged: raise ValueError('B4 altero la fuente B3')
    return directory


def validate_output(root: Path, path: Path) -> dict:
    check_baseline(root)
    data=json.loads((path/'MANIFEST_B4.json').read_text(encoding='utf-8'))
    if data.get('status')!='PASS' or data.get('historical_manifest_unchanged') is not True:
        raise ValueError('B4 no es una corrida satisfactoria')
    source=(root/data['source_b3']).resolve()
    if source != select_source(root,source):raise ValueError('Origen fuera del directorio permitido')
    if sha256(source/'MANIFEST_B3.json')!=data['source_b3_manifest_sha256'] or \
       sha256(source/'SHA256_NUEVAS_SALIDAS.csv')!=data['source_b3_hashes_sha256']:
        raise ValueError('La fuente B3 ha cambiado')
    trace_reports=validate_directory(source)
    files=_verify_output_hashes(path)
    if sum(row['path'].endswith('.png') for row in files)!=data['figures']:
        raise ValueError('Numero de figuras incongruente')
    for report in trace_reports:
        name=report['algorithm']+'_'+report['dynamics']
        case=load_case(source/name)
        processed=csv_rows(path/'figuras_b4'/f'B4_00_datos_series_{name}.csv')
        if len(processed)!=len(case['series']):
            raise ValueError('Numero de puntos de la serie cambiado')
        for a,b in zip(processed,case['series']):
            for k in ('source','event','attempts','M'):
                if str(a[k])!=str(b[k]):
                    raise ValueError(f'Serie {name} modificada: {k}')
            for k in ('time_mcss','E','m_per_spin','e_per_spin'):
                if not math.isclose(float(a[k]),float(b[k]),rel_tol=1e-12,abs_tol=1e-10):
                    raise ValueError(f'Serie {name} modificada: {k}')
    return {'status':'PASS','cases':len(trace_reports),'figures':data['figures'],'files_hashed':len(files),
            'historical_release':'PASS','source_b3':'PASS',
            'output_directory':str(path)}


def main(argv: list[str] | None=None) -> int:
    ap=argparse.ArgumentParser(description='Bloque 4 Ising: mapas y series de trazas reales B3')
    sub=ap.add_subparsers(dest='action',required=True)
    g=sub.add_parser('generar',help='Genera figuras y datos derivados; sin ejecutar el simulador')
    g.add_argument('--directorio-trazas',default='',help='B3 de entrada; vacio: ultima campana')
    g.add_argument('--dpi',type=int,default=160)
    g.add_argument('--paneles',type=int,default=5)
    v=sub.add_parser('validar',help='Verifica hashes y consistencia fisica de salida B4')
    v.add_argument('--directorio',default='',help='B4 a verificar; vacio: ultima')
    opts=ap.parse_args(argv)
    try:
        if opts.action=='generar':
            src=select_source(ROOT,opts.directorio_trazas)
            output=generate(ROOT,src,dpi=opts.dpi,panels=opts.paneles)
            print(json.dumps(validate_output(ROOT,output),ensure_ascii=False,indent=2))
        else:
            path=select_b4(ROOT,opts.directorio)
            print(json.dumps(validate_output(ROOT,path),ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print(f'ERROR B4: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
