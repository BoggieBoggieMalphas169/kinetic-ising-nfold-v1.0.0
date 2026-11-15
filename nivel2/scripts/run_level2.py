"""Level-2 experiment orchestrator. Every measurement goes into a fresh folder."""
from __future__ import annotations
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

from .common import fresh_dir, read_runs, sha256, write_json

ROOT=Path(__file__).resolve().parents[2]


def which_exe(root: Path, filename: str, build: Path|None) -> Path:
    b=build if build else (root/'build')
    ext='.exe' if sys.platform=='win32' else ''
    candidates=[b/'simulator'/'Release'/(filename+ext),b/'simulator'/(filename+ext),
                b/'Release'/(filename+ext),b/(filename+ext),
                b/'simulator'/'Debug'/(filename+ext)]
    for p in candidates:
        if p.exists(): return p.resolve()
    raise FileNotFoundError('Cannot locate '+filename+'; compile first using nivel2/ps1/Nivel2_compilar.ps1. Checked:\n'+'\n'.join(map(str,candidates)))


def call(cmd:list[str]):
    print('[CMD]',' '.join(cmd),flush=True)
    subprocess.run(cmd,check=True)


def compile_repo(root:Path,build:Path):
    call(['cmake','-S',str(root),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release'])
    call(['cmake','--build',str(build),'--config','Release'])
    call(['ctest','--test-dir',str(build),'--output-on-failure','-C','Release'])


def field_campaign(args, root:Path, build:Path):
    if args.runs<2 or args.L%2 or args.L<4 or args.T<=0 or args.J<=0:
        raise ValueError('Require runs>=2, even L>=4, T>0 and J>0')
    if not args.H_values or any(h>=0 for h in args.H_values):
        raise ValueError('Field H values must be negative (initial s=+1)')
    exes={alg:which_exe(root,'ising_'+alg,build) for alg in ('standard','nfold')}
    out=fresh_dir(root/'results/nivel2/medidas/campo','campo')
    raw=out/'raw';raw.mkdir()
    metadata={'schema':'nivel2-field-v1','L':args.L,'T':args.T,'J':args.J,
              'H_values':args.H_values, 'runs_per_pair':args.runs,'seed_base':args.seed,
              'dynamics':args.dynamics,'max_attempts':args.max_attempts,
              'platform':platform.platform(),'executables':{k:str(v) for k,v in exes.items()},
              'status':'started','csv':[]}
    write_json(out/'config.json',metadata)
    try:
        for dyn_idx,dyn in enumerate(args.dynamics):
            for h_idx,H in enumerate(args.H_values):
                # distinct numerical seeds per physical case; algorithms have independent RNG schedules
                seed=args.seed+1000003*dyn_idx+10007*h_idx
                if seed>=2**64: raise ValueError('Seed overflow')
                for alg in ('standard','nfold'):
                    dest=raw/f'{alg}_{dyn}_H{h_idx:02d}.csv'
                    cmd=[str(exes[alg]),'--L',str(args.L),'--T',str(args.T),'--J',str(args.J),
                         '--H',str(H),'--runs',str(args.runs),'--seed',str(seed),
                         '--dynamics',dyn,'--output',str(dest)]
                    if args.max_attempts:
                        if alg=='standard': cmd += ['--max-attempts',str(args.max_attempts)]
                        else: cmd += ['--max-time-attempts',str(args.max_attempts)]
                    call(cmd)
                    df=read_runs(dest)
                    metadata['csv'].append({'file':str(dest.relative_to(out)),
                                            'sha256':sha256(dest),'rows':len(df),
                                            'complete':int(df.reached_M0.eq(1).sum()),
                                            'censored':int(df.reached_M0.eq(0).sum())})
    except BaseException as err:
        write_json(out/'ERROR.json',{'error':str(err),'completed':metadata['csv']})
        print('[ERROR] Partial campaign preserved under',out)
        raise
    metadata['status']='completed'
    write_json(out/'manifest.json',metadata)
    print('[NIVEL2] New field data:',out)
    if any(x['censored'] for x in metadata['csv']):
        print('[WARN] Some runs did not reach M=0; their mean lifetimes must not be used directly.')
    return out



def repeat_campaign(args, root:Path, build:Path, mode:str):
    """Fresh multi-point sweep; same output contract as the production executables."""
    if mode not in ('temperature','size'):
        raise ValueError(mode)
    if args.runs<2 or args.L<4 or args.L%2 or args.T<=0 or args.J<=0:
        raise ValueError('Require runs>=2, even L>=4, T>0 and J>0')
    if not args.H_values or any(H>=0 for H in args.H_values):
        raise ValueError('Require negative H values')
    values=args.T_values if mode=='temperature' else args.L_values
    if not values or (mode=='temperature' and any(T<=0 for T in values)) or (mode=='size' and any(L<4 or L%2 for L in values)):
        raise ValueError('Temperatures must be >0; sizes must be even and >=4')
    exes={alg:which_exe(root,'ising_'+alg,build) for alg in ('standard','nfold')}
    title='temperatura' if mode=='temperature' else 'tamano'
    folder=fresh_dir(root/'results/nivel2/medidas'/title,title)
    raw=folder/'raw';raw.mkdir()
    meta={'schema':'nivel2-'+mode+'-v1','mode':mode,'L_base':args.L,'T_base':args.T,
          'J':args.J,'values':values,'H_values':args.H_values,'runs':args.runs,
          'dynamics':args.dynamics,'seed_base':args.seed,'max_attempts':args.max_attempts,
          'platform':platform.platform(),'status':'started','csv':[]}
    write_json(folder/'config.json',meta)
    try:
        for di,dyn in enumerate(args.dynamics):
            for hi,H in enumerate(args.H_values):
                for vi,value in enumerate(values):
                    L=args.L if mode=='temperature' else int(value)
                    T=float(value) if mode=='temperature' else args.T
                    seed=args.seed + di*1000003 + hi*10007 + vi*101
                    if seed>=2**64: raise ValueError('Seed overflow')
                    for alg in ('standard','nfold'):
                        dest=raw/f'{alg}_{dyn}_H{hi:02d}_P{vi:02d}.csv'
                        cmd=[str(exes[alg]),'--L',str(L),'--T',str(T),'--J',str(args.J),
                             '--H',str(H),'--runs',str(args.runs),'--seed',str(seed),
                             '--dynamics',dyn,'--output',str(dest)]
                        if args.max_attempts:
                            cmd += (['--max-attempts'] if alg=='standard' else ['--max-time-attempts'])
                            cmd += [str(args.max_attempts)]
                        call(cmd)
                        d=read_runs(dest)
                        meta['csv'].append({'file':str(dest.relative_to(folder)),
                                            'sha256':sha256(dest),'rows':len(d),
                                            'complete':int(d.reached_M0.eq(1).sum()),
                                            'censored':int(d.reached_M0.eq(0).sum())})
    except BaseException as err:
        write_json(folder/'ERROR.json',{'error':str(err),'completed':meta['csv']})
        print('[ERROR] Partial campaign preserved:',folder)
        raise
    meta['status']='completed'
    write_json(folder/'manifest.json',meta)
    print('[NIVEL2] New',mode,'campaign:',folder)
    return folder


def trace_campaign(args, root:Path, build:Path):
    if args.L<4 or args.L%2 or args.T<=0 or args.J<=0 or args.H>=0:
        raise ValueError('Require even L>=4, T/J>0 and H<0')
    exe=which_exe(root,'ising_trace',build)
    out=fresh_dir(root/'results/nivel2/medidas/trazas','traza')
    metadata={'schema':'nivel2-trace-v1','L':args.L,'T':args.T,'J':args.J,
              'H':args.H,'dynamics':args.dynamics[0],'seed':args.seed,
              'trace_every':args.trace_every,'snapshot_every':args.snapshot_every,
              'max_frames':args.max_frames,'max_steps':args.max_steps,
              'warning':'max_steps counts attempted updates in Standard but events in n-fold',
              'executable':str(exe),'csv':[]}
    write_json(out/'config.json',metadata)
    try:
        for alg in ('standard','nfold'):
            prefix=out/f'{alg}_frame'
            csvpath=out/f'{alg}_trace.csv'
            cmd=[str(exe),'--algorithm',alg,'--L',str(args.L), '--T',str(args.T),
                 '--J',str(args.J),'--H',str(args.H),'--dynamics',args.dynamics[0],
                 '--seed',str(args.seed),'--stream','1','--trace',str(csvpath),
                 '--frames-prefix',str(prefix),'--trace-every',str(args.trace_every),
                 '--snapshot-every',str(args.snapshot_every),'--max-frames',str(args.max_frames),
                 '--max-steps',str(args.max_steps)]
            call(cmd)
            import pandas as pd
            d=pd.read_csv(csvpath)
            metadata['csv'].append({'file':csvpath.name,'sha256':sha256(csvpath),
                                    'lines':len(d),'reached_M0':int(d.reached_M0.iloc[-1]),
                                    'final_tau_mcss':float(d.time_mcss.iloc[-1])})
    except BaseException as err:
        write_json(out/'ERROR.json',{'error':str(err),'completed':metadata['csv']})
        print('[ERROR] Partial traces preserved under',out)
        raise
    write_json(out/'manifest.json',metadata)
    print('[NIVEL2] New traces:',out)
    return out


def main():
    ap=argparse.ArgumentParser(description='Produce or replot physical Level-2 Ising figures')
    ap.add_argument('action',choices=['compile','historical','field','temperature','size','trace','plot','validate','all-quick'])
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--build',type=Path,default=None)
    ap.add_argument('--L',type=int,default=32)
    ap.add_argument('--T',type=float,default=1.5)
    ap.add_argument('--J',type=float,default=1.)
    ap.add_argument('--H',type=float,default=-.75)
    ap.add_argument('--H-values',nargs='+',type=float,default=[-.75,-1.,-1.5,-2.,-3.])
    ap.add_argument('--runs',type=int,default=100)
    ap.add_argument('--T-values',nargs='+',type=float,default=[1.0,1.2,1.5,1.8,2.1])
    ap.add_argument('--L-values',nargs='+',type=int,default=[8,16,32,64,128])
    ap.add_argument('--seed',type=int,default=20261115)
    ap.add_argument('--dynamics',nargs='+',choices=['glauber','metropolis'],default=['glauber','metropolis'])
    ap.add_argument('--max-attempts',type=int,default=0)
    ap.add_argument('--max-steps',type=int,default=0)
    ap.add_argument('--trace-every',type=int,default=10)
    ap.add_argument('--snapshot-every',type=int,default=200)
    ap.add_argument('--max-frames',type=int,default=120)
    ap.add_argument('--bootstrap',type=int,default=400)
    args=ap.parse_args()
    root=args.root.resolve(); build=(args.build or root/'build').resolve()
    if args.seed<0 or args.seed>=2**64 or min(args.trace_every,args.snapshot_every,args.max_frames)<1:
        ap.error('seed out of uint64 range or invalid sampling interval')
    if args.max_attempts<0 or args.max_steps<0: ap.error('No negative limits')
    if args.action in ('compile','validate'):
        if args.action=='compile': compile_repo(root,build)
        else:
            call(['ctest','--test-dir',str(build),'--output-on-failure','-C','Release'])
            call([sys.executable,'-m','nivel2.scripts.check_baseline','--root',str(root)])
            call([sys.executable,'-m','nivel2.scripts.validate_level2','--root',str(root),
                  '--build',str(build)])
    elif args.action=='field': field_campaign(args,root,build)
    elif args.action=='trace': trace_campaign(args,root,build)
    elif args.action in ('temperature','size'): repeat_campaign(args,root,build,args.action)
    elif args.action in ('plot','historical'):
        call([sys.executable,'-m','nivel2.scripts.plot_level2','--root',str(root),
              '--bootstrap',str(args.bootstrap)])
    elif args.action=='all-quick':
        compile_repo(root,build)
        args.runs=min(args.runs,12)
        args.H_values=[-1.5,-2.,-3.]
        args.L=min(args.L,16)
        field_campaign(args,root,build)
        args.max_steps=0
        trace_campaign(args,root,build)
        call([sys.executable,'-m','nivel2.scripts.plot_level2','--root',str(root),
              '--bootstrap',str(args.bootstrap)])


if __name__=='__main__': main()
