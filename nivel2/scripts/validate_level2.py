"""Fast Level-2 integration regression: Standard / n-fold traces versus production C."""
from __future__ import annotations
import argparse
import csv
import math
import subprocess
import tempfile
from pathlib import Path

from .run_level2 import which_exe


def get_csv(p: Path):
    with p.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))


def numeric_equal(a: str, b: str, rel:float=1e-12)->bool:
    return math.isclose(float(a),float(b),rel_tol=rel,abs_tol=1e-12)


def verify(standard:Path, nfold:Path, trace:Path):
    for alg, exe in [('standard',standard),('nfold',nfold)]:
        with tempfile.TemporaryDirectory(prefix='ising_nivel2_verif_') as dirname:
            t=Path(dirname)
            base=['--L','8','--T','1.5','--J','1','--H','-1.5',
                  '--seed','123457','--dynamics','glauber']
            subprocess.run([str(exe),*base,'--runs','1','--output',str(t/'prod.csv')],
                           check=True,capture_output=True,text=True)
            subprocess.run([str(trace),'--algorithm',alg,*base,'--stream','1',
                            '--trace',str(t/'trace.csv'),
                            '--frames-prefix',str(t/'frame'),
                            '--trace-every','1','--snapshot-every','10',
                            '--max-frames','100'],check=True,capture_output=True,text=True)
            row=get_csv(t/'prod.csv')[0]; tr=get_csv(t/'trace.csv')[-1]
            idx=get_csv(t/'frame_index.csv')
            assert tr['final']=='1' and row['reached_M0']=='1'
            assert tr['reached_M0']==row['reached_M0']
            assert int(tr['attempts'])==int(row.get('attempts',row.get('equivalent_attempts')))
            assert int(tr['events'])==int(row['events'])
            assert numeric_equal(tr['time_mcss'],row['time_mcss'])
            assert numeric_equal(float(tr['m_per_spin'])*64,row['final_M'])
            assert numeric_equal(float(tr['e_per_spin'])*64,row['final_E'])
            assert idx[0]['events']=='0' and idx[0]['attempts']=='0'
            assert idx[-1]['final']=='1' and numeric_equal(idx[-1]['time_mcss'],tr['time_mcss'])
            import numpy as np
            for rec in idx:
                path=t/rec['file']
                assert path.is_file() and path.parent==t
                m=np.loadtxt(path,delimiter=',',dtype=np.int8)
                assert m.shape==(8,8) and np.isin(m,[-1,1]).all()
                M=int(m.sum()); energy=(-1.0 * (m*np.roll(m,1,axis=0)+m*np.roll(m,1,axis=1)).sum()
                                      -(-1.5)*M)
                assert numeric_equal(M/64,rec['m_per_spin'])
                assert numeric_equal(energy/64,rec['e_per_spin'])
            # Exclusive creation prevents silent overwrites of previous trace.
            repeat=subprocess.run([str(trace),'--algorithm',alg,*base,'--stream','1',
                                   '--trace',str(t/'trace.csv'),
                                   '--frames-prefix',str(t/'frame'),
                                   '--trace-every','1','--snapshot-every','10',
                                   '--max-frames','100'],capture_output=True,text=True)
            assert repeat.returncode!=0, 'Tracer unexpectedly overwrote an earlier result'
            print(f'[PASS] {alg}: production/tracer bit-identical counters, M, E, and periodic-frame energy')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    ap.add_argument('--build',type=Path,default=None)
    a=ap.parse_args();root=a.root.resolve()
    verify(*(which_exe(root,'ising_'+name,a.build) for name in ('standard','nfold','trace')))
    print('[PASS] New Level-2 diagnostic executable does not alter standard production results.')

if __name__=='__main__': main()
