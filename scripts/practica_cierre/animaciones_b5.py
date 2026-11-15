"""B5: animaciones cientificas reproducibles desde eventos B3 validados.

Se usa una malla nueva de instantes en MCSS por clip y se reconstruye EXACTAMENTE
el ultimo estado ocurrido hasta cada instante a partir de los flips aceptados.
No se interpolan spins ni se suponen cambios durante los intentos rechazados.
No modifica C, snapshots ni resultados historicos.
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
from typing import Any, Iterator

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np

from .validar_baseline import ROOT, create_run_dir, manifest_state, sha256
from .visualizacion_b4 import (check_baseline, load_case, select_source,
                                FAMILIES, DYNAMICS, _same_physics)
from .trazas_b3 import validate_directory

COLORMAP = ListedColormap(['#d76550', '#31689b'])  # -1, +1, same as B4
NORM = BoundaryNorm([-1.5, 0, 1.5], 2)
FORMATS = ('gif', 'mp4', 'ambos')


def require_animation_libs() -> None:
    try:
        import imageio.v2 as imageio  # noqa F401
        import imageio_ffmpeg  # noqa F401
        from PIL import Image  # noqa F401
    except ImportError as exc:
        raise RuntimeError('Falta dependencia para GIF/MP4; instala: python -m pip install -r requirements_animaciones.txt') from exc


def source_hashes(source: Path) -> dict[str, str]:
    paths = [source / 'MANIFEST_B3.json', source / 'SHA256_NUEVAS_SALIDAS.csv']
    with (source / 'SHA256_NUEVAS_SALIDAS.csv').open(newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source.resolve()) or not path.is_file():
            raise ValueError('Manifest B3 contiene ruta invalida')
        paths.append(path)
    return {p.relative_to(source).as_posix(): sha256(p) for p in paths}


def select_b5(root: Path, directory: str | Path | None) -> Path:
    parent = (root / 'results' / 'practica_cierre').resolve()
    if directory:
        candidate = Path(directory)
        p = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if not p.is_relative_to(parent) or p.parent != parent:
            raise ValueError('Directorio B5 fuera de results/practica_cierre/')
    else:
        folders = sorted((p for p in parent.iterdir() if p.is_dir() and (p/'MANIFEST_B5.json').is_file()),
                         key=lambda p: p.name, reverse=True)
        if not folders:
            raise FileNotFoundError('No hay animaciones B5; ejecuta generar primero')
        p = folders[0]
    if not (p / 'MANIFEST_B5.json').is_file():
        raise ValueError('No es un directorio B5')
    return p


def targets_at_attempts(end_attempts: int, count: int) -> list[int]:
    """Instantes distribuidos homogeneamente, redondeados hacia abajo a intentos enteros."""
    if end_attempts < 0 or count < 2:
        raise ValueError('Rango temporal o numero de frames incorrecto')
    return [(end_attempts * i)//(count-1) for i in range(count)]


def replay_at_attempts(case: dict[str, Any], targets: list[int]) -> Iterator[dict[str, Any]]:
    """Reconstruccion en O(N + eventos + frames*N), memoria de trabajo O(N).

    Los eventos B3 fueron verificados independientemente antes de invocar este metodo.
    Conserva la ultima configuracion observada tras cada evento aceptado.
    """
    report = case['report']
    L = int(report['L']); N = L*L
    end = int(report['attempts']); events = case['events']
    if any(t < 0 or t > end for t in targets) or any(b < a for a, b in zip(targets, targets[1:])):
        raise ValueError('Objetivos de tiempo no monotonos o fuera de la trayectoria')
    spins = bytearray(case['frames'][0]['spin_bits'], 'ascii')
    if len(spins) != N:
        raise ValueError('Malla inicial incorrecta')
    M, E = int(case['frames'][0]['M']), float(case['frames'][0]['E'])
    ptr = 0; observed = 0
    for target in targets:
        while ptr < len(events) and int(events[ptr]['attempts']) <= target:
            evt = events[ptr]; i = int(evt['site'])
            spins[i] = ord(evt['spin_after'])
            M, E = int(evt['M']), float(evt['E'])
            observed = int(evt['attempts'])
            ptr += 1
        bits = bytes(spins)
        yield {'target_attempts': target, 'target_mcss': target/N, 'observed_attempts': observed,
               'event_count': ptr, 'M': M, 'E': E, 'm_per_spin': M/N, 'e_per_spin': E/N,
               'spin_sha256': hashlib.sha256(bits).hexdigest(),
               'spins': (2*(np.frombuffer(bits, dtype=np.uint8).reshape(L,L).astype(np.int8)-48)-1),
               'terminal': target >= end, 'censored': case['censored']}


def _figure_rgb(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()


class SingleScene:
    def __init__(self, case: dict[str, Any], max_t: float, dpi: int):
        self.case = case
        self.fig = plt.figure(figsize=(8.8, 5.2), dpi=dpi, facecolor='#fcfdfe')
        gs = self.fig.add_gridspec(2, 2, width_ratios=[1, 1.25], height_ratios=[1, 1],
                                   left=.055, right=.97, bottom=.12, top=.82, wspace=.28, hspace=.3)
        ax_grid = self.fig.add_subplot(gs[:, 0]); ax_m = self.fig.add_subplot(gs[0, 1]); ax_e = self.fig.add_subplot(gs[1, 1])
        L = case['report']['L']
        self.im = ax_grid.imshow(np.ones((L,L)), cmap=COLORMAP, norm=NORM, interpolation='nearest')
        ax_grid.set(xticks=[], yticks=[])
        for spine in ax_grid.spines.values():spine.set_linewidth(.8);spine.set_color('#64748b')
        s = case['series']; tt=[v['time_mcss'] for v in s]
        ax_m.step(tt, [v['m_per_spin'] for v in s], where='post', lw=1.6, color='#2563a0')
        ax_e.step(tt, [v['e_per_spin'] for v in s], where='post', lw=1.6, color='#c25a3c')
        self.cursors = [ax.axvline(0,color='black',lw=1,linestyle='--',alpha=.65) for ax in (ax_m,ax_e)]
        for ax,ylabel in ((ax_m,'M / N'),(ax_e,'E / N')):
            ax.set(ylabel=ylabel);ax.grid(alpha=.18)
            ax.set_xlim(0,max(max_t,1e-6))
            if max_t == 0:ax.set_xlim(-.01,.01)
        ax_e.set_xlabel('Tiempo (MCSS)')
        r=case['report']; self.header=self.fig.suptitle(f'B5 | {r["algorithm"].upper()} + {r["dynamics"].capitalize()}  |  L={L}, T/J={r["T"]/r["J"]:g}, H/J={r["H"]/r["J"]:g}',fontsize=12, y=.965, fontweight='bold')
        self.info=self.fig.text(.5,.865,'',ha='center', fontsize=10)
        self.fig.text(.5,.035,'Una realizacion; espines reconstruidos a partir de los eventos aceptados | MCSS no son segundos', ha='center',fontsize=8, color='#475569')
    def draw(self, snap: dict[str, Any]):
        self.im.set_data(snap['spins'])
        for cur in self.cursors:cur.set_xdata([snap['target_mcss']]*2)
        tail='CENSURADA (sin escape)' if snap['censored'] else ('M=0 (final)' if snap['terminal'] else 'en evolucion')
        self.info.set_text(f't = {snap["target_mcss"]:.4f} MCSS  |  eventos = {snap["event_count"]}  |  M/N = {snap["m_per_spin"]:+.3f}  |  E/N = {snap["e_per_spin"]:+.3f}  |  {tail}')
        return _figure_rgb(self.fig)
    def close(self):plt.close(self.fig)


class ComparisonScene:
    def __init__(self, a: dict[str, Any], b: dict[str, Any], max_t: float, dpi: int):
        self.cases = (a,b)
        self.fig = plt.figure(figsize=(10, 5.6), dpi=dpi, facecolor='#fcfdfe')
        gs=self.fig.add_gridspec(2,2,left=.06,right=.96,bottom=.12,top=.81,hspace=.37,wspace=.16,height_ratios=[3,1])
        self.images=[];self.cursors=[];self.status=[]
        for col,case in enumerate((a,b)):
            ax=self.fig.add_subplot(gs[0,col]);L=case['report']['L']
            im=ax.imshow(np.ones((L,L)),cmap=COLORMAP,norm=NORM,interpolation='nearest')
            ax.set(xticks=[],yticks=[])
            self.images.append(im)
            ts=[s['time_mcss'] for s in case['series']]
            ax2=self.fig.add_subplot(gs[1,col]);ax2.step(ts,[s['m_per_spin'] for s in case['series']],where='post',lw=1.4)
            ax2.set(xlim=(0,max(max_t,1e-6)),xlabel='Tiempo MCSS',ylabel='M/N')
            ax2.grid(alpha=.2)
            self.cursors.append(ax2.axvline(0,color='#9f1239',ls='--',lw=1.1))
            self.status.append(ax.set_title('',fontsize=10))
        r=a['report'];self.fig.suptitle(f'B5 | {r["dynamics"].capitalize()}: Standard vs n-fold | L={r["L"]}, T/J={r["T"]/r["J"]:g}, H/J={r["H"]/r["J"]:g}',y=.965,fontsize=12,fontweight='bold')
        self.info=self.fig.text(.5,.86,'',ha='center',fontsize=10)
        self.fig.text(.5,.035,'Misma escala MCSS; realizaciones INDEPENDIENTES, no prueba de equivalencia estadistica. Finales congelados para visualizacion.',ha='center',fontsize=8,color='#475569')
    def draw(self,snaps: tuple[dict[str, Any], dict[str, Any]]):
        for index,(case,snap) in enumerate(zip(self.cases,snaps)):
            self.images[index].set_data(snap['spins'])
            self.cursors[index].set_xdata([snap['target_mcss']]*2)
            status='CENSURADA' if snap['censored'] else ('FIN / M=0' if snap['terminal'] else 'evolucion')
            self.status[index].set_text(f'{case["report"]["algorithm"].upper()} | M/N={snap["m_per_spin"]:+.3f} | {status}')
        self.info.set_text(f'Tiempo comun: {snaps[0]["target_mcss"]:.4f} MCSS | espines en el ultimo evento observado')
        return _figure_rgb(self.fig)
    def close(self):plt.close(self.fig)


def gif_durations_ms(count: int, fps: int) -> list[int]:
    """Duraciones ajustadas al centisegundo GIF con error acumulado <=5 ms."""
    if count < 1 or fps < 1 or fps > 100:
        raise ValueError('Duracion GIF invalida')
    edges = [round(100*i/fps) for i in range(count+1)]
    return [10*(b-a) for a,b in zip(edges,edges[1:])]


def _open_writers(prefix: Path, fmt: str, fps: int, count: int):
    import imageio.v2 as imageio
    writer_gif = imageio.get_writer(prefix.with_suffix('.gif'), mode='I', duration=gif_durations_ms(count, fps), loop=0) if fmt in ('gif','ambos') else None
    writer_mp4 = None
    try:
        if fmt in ('mp4','ambos'):
            writer_mp4 = imageio.get_writer(prefix.with_suffix('.mp4'), format='FFMPEG',mode='I',fps=fps,
                                           codec='libx264',pixelformat='yuv420p',macro_block_size=16,
                                           ffmpeg_log_level='error',quality=7)
    except Exception:
        if writer_gif: writer_gif.close()
        raise
    return writer_gif, writer_mp4


def _render_clip(out: Path, name: str, scene: Any, fps: int, fmt: str,
                 frames: Iterator[np.ndarray], frame_count: int) -> list[Path]:
    """Escribe salida streaming sin acumular arrays RGB."""
    prefix=out/name
    gw,mw=_open_writers(prefix,fmt,fps,frame_count)
    try:
        for idx,img in enumerate(frames):
            if img.shape[0] % 16 or img.shape[1] % 16:
                img = np.pad(img,((0,(-img.shape[0])%16),(0,(-img.shape[1])%16),(0,0)),mode='edge')
            if gw is not None: gw.append_data(img)
            if mw is not None: mw.append_data(img)
    finally:
        if gw is not None:gw.close()
        if mw is not None:mw.close()
        scene.close()
    return [prefix.with_suffix('.'+s) for s in ('gif','mp4') if s==fmt or fmt=='ambos']


def _rows_for_case(clip: str, key: str, case: dict[str, Any], attempts: list[int]) -> tuple[list[dict], list[dict]]:
    """Devuelve filas sin matriz (para CSV) y muestras con matriz para el video.

    Estas muestras ocupan O(N*frames), aceptable con <=240 cuadros; evita
    materializar los estados por cada evento del sistema.
    """
    snapshots=list(replay_at_attempts(case, attempts))
    rows=[]
    for index,s in enumerate(snapshots):
        rows.append({'clip':clip,'frame_index':index,'case':key,
                     'target_attempts':s['target_attempts'],'target_mcss':s['target_mcss'],
                     'observed_attempts':s['observed_attempts'],'event_count':s['event_count'],
                     'M':s['M'],'E':s['E'],'m_per_spin':s['m_per_spin'],'e_per_spin':s['e_per_spin'],
                     'spin_sha256':s['spin_sha256'],'terminal':int(s['terminal']),
                     'censored':int(s['censored'])})
    return rows,snapshots


def render_one(out: Path, case: dict, key: str, fps: int, count: int, dpi: int, fmt: str) -> tuple[list[Path],list[dict]]:
    name=f'B5_01_{key}'
    targets=targets_at_attempts(case['report']['attempts'],count)
    rows,snaps=_rows_for_case(name,key,case,targets)
    scene=SingleScene(case,case['report']['time_mcss'],dpi)
    def frames():
        for s in snaps:
            yield scene.draw(s)
    files=_render_clip(out,name,scene,fps,fmt,frames(),count)
    return files,rows


def render_comparison(out: Path, a: dict, b: dict, dyn: str, fps: int, count: int, dpi: int, fmt: str) -> tuple[list[Path],list[dict]]:
    if not _same_physics(a,b):
        raise ValueError('No se pueden sincronizar trazas de fisica diferente')
    name=f'B5_02_comparacion_{dyn}'
    end=max(a['report']['attempts'],b['report']['attempts'])
    common=targets_at_attempts(end,count)
    ai=[min(t,a['report']['attempts']) for t in common]
    bi=[min(t,b['report']['attempts']) for t in common]
    row_a,snap_a=_rows_for_case(name,'standard_'+dyn,a,ai)
    row_b,snap_b=_rows_for_case(name,'nfold_'+dyn,b,bi)
    # Se registra adicionalmente el tiempo comun, pues la trayectoria terminada
    # se mantiene VISUALMENTE congelada despues de su tiempo de absorcion.
    for row_a_item,row_b_item,t in zip(row_a,row_b,common):
        row_a_item['common_attempts']=t;row_a_item['common_mcss']=t/(a['report']['L']**2)
        row_b_item['common_attempts']=t;row_b_item['common_mcss']=t/(b['report']['L']**2)
    scene=ComparisonScene(a,b,end/(a['report']['L']**2),dpi)
    def frames():
        for t,x,y in zip(common,snap_a,snap_b):
            for s in (x,y):s['target_mcss']=t/(a['report']['L']**2)
            yield scene.draw((x,y))
    files=_render_clip(out,name,scene,fps,fmt,frames(),count)
    return files,row_a+row_b


def write_table(path:Path,rows:list[dict]) -> None:
    if not rows:raise ValueError('No hay datos para el indice de frames')
    columns=['clip','frame_index','case','target_attempts','target_mcss','observed_attempts','event_count','M','E',
             'm_per_spin','e_per_spin','spin_sha256','terminal','censored','common_attempts','common_mcss']
    with path.open('x',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=columns)
        writer.writeheader();writer.writerows(rows)


def generate(root: Path, source: Path, fps: int=12, count: int=64, dpi: int=96, fmt: str='ambos') -> Path:
    if not (2 <= fps <= 30 and 8 <= count <= 240 and 72 <= dpi <= 180 and fmt in FORMATS):
        raise ValueError('Parametros fuera de rango: fps 2..30, frames 8..240, dpi 72..180, formato gif/mp4/ambos')
    require_animation_libs()
    baseline=check_baseline(root)
    reports=validate_directory(source)
    if not reports:raise ValueError('No hay trazas B3 validadas')
    cases={r['algorithm']+'_'+r['dynamics']:load_case(source/(r['algorithm']+'_'+r['dynamics'])) for r in reports}
    hashes=source_hashes(source)
    directory=create_run_dir(root,'animaciones_b5')
    out=directory/'animaciones';out.mkdir()
    filenames=[];rows=[];clips=[];status='FAIL'
    try:
        for key,case in sorted(cases.items()):
            f,r=render_one(out,case,key,fps,count,dpi,fmt)
            filenames.extend(f);rows.extend(r)
            clips.append({'clip':'B5_01_'+key,'cases':[key],'frames':count,'duration_seconds':count/fps,
                          'terminal_mcss':case['report']['time_mcss'],'censored':case['censored']})
        for dyn in DYNAMICS:
            if f'standard_{dyn}' in cases and f'nfold_{dyn}' in cases:
                a,b=cases[f'standard_{dyn}'],cases[f'nfold_{dyn}']
                if _same_physics(a,b):
                    f,r=render_comparison(out,a,b,dyn,fps,count,dpi,fmt)
                    filenames.extend(f);rows.extend(r)
                    clips.append({'clip':'B5_02_comparacion_'+dyn,'cases':['standard_'+dyn,'nfold_'+dyn],
                                  'frames':count,'duration_seconds':count/fps,
                                  'terminal_mcss':max(a['report']['time_mcss'],b['report']['time_mcss']),
                                  'censored':a['censored'] or b['censored']})
        write_table(out/'B5_00_indice_fotogramas.csv',rows)
        filenames.append(out/'B5_00_indice_fotogramas.csv')
        status='PASS'
    finally:
        historical_unchanged=manifest_state(root)==baseline
        source_unchanged=source_hashes(source)==hashes
        if not historical_unchanged or not source_unchanged:status='FAIL'
        manifest={'block':'B5','status':status,'created_utc':datetime.now(timezone.utc).isoformat(),
                  'source_b3':source.relative_to(root).as_posix(),
                  'source_b3_sha256':hashes,'historical_manifest_unchanged':historical_unchanged,
                  'source_b3_unchanged':source_unchanged,'fps':fps,'frames_per_clip':count,'dpi':dpi,
                  'format':fmt,'python':sys.version.splitlines()[0],'platform':platform.platform(),
                  'video_units':'MCSS; never physical seconds',
                  'method':'uniform targets in equivalent attempts; exact event replay; zero-order hold',
                  'clips':clips}
        (directory/'MANIFEST_B5.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        report=['# Bloque 5 - Animaciones cientificas de Ising','',f'Estado: **{status}**','',
                f'Fuente B3: `{manifest["source_b3"]}`',
                f'Clips: {len(clips)} | Frames por clip: {count} | fps: {fps} | Formato: {fmt}','','## Interpretacion fisica','',
                '- Los eventos aceptados reconstruyen la configuracion exacta en cada MCSS.',
                '- Entre intentos rechazados se mantiene la configuracion; NO se interpolan espines.',
                '- En comparaciones, el mismo reloj MCSS controla los dos paneles.',
                '- Tras el escape, se congela el ultimo estado SOLO a efectos visuales.',
                '- La animacion de un ensayo no prueba equivalencia de distribuciones.',
                '- Una trayectoria censurada se rotula como tal (no es un escape).',
                '- Duracion de GIF/MP4 es presentacion audiovisual, NO duracion fisica.','',
                'Los programas y CSV previos permanecen sin modificar.']
        (directory/'RESUMEN.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        with (directory/'SHA256_B5.csv').open('x',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(['path','sha256'])
            for p in sorted([*filenames,directory/'MANIFEST_B5.json',directory/'RESUMEN.md']):
                if p.is_file():w.writerow([p.relative_to(directory).as_posix(),sha256(p)])
        if status!='PASS':raise ValueError('La fuente o release hist. ha sido modificada')
    return directory


def validate_output(root:Path,path:Path) -> dict:
    check_baseline(root)
    data=json.loads((path/'MANIFEST_B5.json').read_text(encoding='utf-8'))
    if data.get('status')!='PASS' or not data.get('historical_manifest_unchanged') or not data.get('source_b3_unchanged'):
        raise ValueError('B5 no finalizo correctamente')
    source=select_source(root,root/data['source_b3'])
    validate_directory(source)
    if source_hashes(source)!=data['source_b3_sha256']:
        raise ValueError('Fuente B3 modificada')
    manifest=list(csv.DictReader((path/'SHA256_B5.csv').open(newline='',encoding='utf-8')))
    actual={}
    for item in manifest:
        file=(path/item['path']).resolve()
        if not file.is_relative_to(path.resolve()) or not file.is_file():raise ValueError('Ruta B5 insegura')
        if sha256(file)!=item['sha256']:raise ValueError('Hash B5 incorrecto: '+str(file))
        actual[item['path']]=file
    expected=set()
    for clip in data['clips']:
        for suffix in (('gif','mp4') if data['format']=='ambos' else (data['format'],)):
            expected.add('animaciones/'+clip['clip']+'.'+suffix)
    if not expected.issubset(actual):raise ValueError('Faltan animaciones del manifiesto')
    # Comprobar que los archivos NO solo existen, sino que son decodificables y
    # conservan el calendario de reproduccion (limitacion GIF: 10 ms por paso).
    from PIL import Image
    import imageio.v2 as imageio
    for clip in data['clips']:
        prefix='animaciones/'+clip['clip']
        if prefix+'.gif' in expected:
            with Image.open(actual[prefix+'.gif']) as gif:
                if gif.n_frames < 1 or gif.n_frames > data['frames_per_clip']:
                    raise ValueError('GIF con cantidad incoherente de cuadros')
                duration=0
                for i in range(gif.n_frames):
                    gif.seek(i)
                    duration += gif.info.get('duration', 0)
                if abs(duration - 1000*data['frames_per_clip']/data['fps']) > 11:
                    raise ValueError('La duracion GIF no coincide con FPS')
        if prefix+'.mp4' in expected:
            video=imageio.get_reader(actual[prefix+'.mp4'])
            try:
                if video.count_frames()!=data['frames_per_clip']:
                    raise ValueError('MP4 no contiene todos los frames fisicos')
                if not math.isclose(video.get_meta_data()['fps'],data['fps'],rel_tol=0,abs_tol=0.01):
                    raise ValueError('FPS MP4 incorrectos')
                picture=video.get_data(0)
                if picture.ndim!=3 or picture.shape[2]!=3:
                    raise ValueError('MP4 inicial no decodificable')
            finally:video.close()
    rows=list(csv.DictReader((path/'animaciones'/'B5_00_indice_fotogramas.csv').open(newline='',encoding='utf-8')))
    grouped={}
    for r in rows:grouped.setdefault((r['clip'],r['case']),[]).append(r)
    for clip in data['clips']:
        for key in clip['cases']:
            relevant=grouped.get((clip['clip'],key),[])
            if len(relevant)!=data['frames_per_clip']:raise ValueError('Indice incompleto de frames')
            case=load_case(source/key)
            attempts=[int(r['target_attempts']) for r in relevant]
            for i,(row,snap) in enumerate(zip(relevant,replay_at_attempts(case,attempts))):
                if int(row['frame_index'])!=i or row['spin_sha256']!=snap['spin_sha256'] or \
                   int(row['M'])!=snap['M'] or int(row['event_count'])!=snap['event_count'] or \
                   int(row['observed_attempts'])!=snap['observed_attempts'] or \
                   int(row['terminal'])!=int(snap['terminal']) or int(row['censored'])!=int(snap['censored']) or \
                   not math.isclose(float(row['E']),snap['E'],abs_tol=1e-8):
                    raise ValueError('Frame fisico no reproducible: '+clip['clip']+' '+key)
            if len(clip['cases'])==1:
                if attempts!=targets_at_attempts(case['report']['attempts'],data['frames_per_clip']):
                    raise ValueError('Malla temporal individual incorrecta')
            else:
                end=max(load_case(source/key2)['report']['attempts'] for key2 in clip['cases'])
                targets=targets_at_attempts(end,data['frames_per_clip'])
                for i,r in enumerate(relevant):
                    if int(r['common_attempts'])!=targets[i] or \
                       int(r['target_attempts'])!=min(targets[i],case['report']['attempts']):
                        raise ValueError('Comparacion con reloj comun incorrecto')
    return {'status':'PASS','clips':len(data['clips']), 'media_files':len(expected),
            'frames_indexed':len(rows),'files_hashed':len(manifest),
            'source_b3':'PASS','historical_release':'PASS','output_directory':str(path)}


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='B5: animaciones MCSS desde eventos reales B3')
    sub=ap.add_subparsers(dest='action',required=True)
    g=sub.add_parser('generar');g.add_argument('--directorio-trazas',default='')
    g.add_argument('--fps',type=int,default=12);g.add_argument('--frames',type=int,default=64)
    g.add_argument('--dpi',type=int,default=96);g.add_argument('--formato',choices=FORMATS,default='ambos')
    v=sub.add_parser('validar');v.add_argument('--directorio',default='')
    args=ap.parse_args(argv)
    try:
        if args.action=='generar':
            src=select_source(ROOT,args.directorio_trazas)
            out=generate(ROOT,src,fps=args.fps,count=args.frames,dpi=args.dpi,fmt=args.formato)
            print(json.dumps(validate_output(ROOT,out),ensure_ascii=False,indent=2))
        else:
            out=select_b5(ROOT,args.directorio)
            print(json.dumps(validate_output(ROOT,out),ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print(f'ERROR B5: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
