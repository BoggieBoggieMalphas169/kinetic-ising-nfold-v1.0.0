"""Check that every original archived file, except the declared build change, is unchanged."""
import argparse
import json
from pathlib import Path
from .common import sha256


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args=ap.parse_args()
    root=args.root.resolve()
    provenance=json.loads((root/'nivel2/baseline_original.json').read_text(encoding='utf-8'))
    mismatches=[]
    for name, expected in provenance['sha256_unmodified_original'].items():
        path=root/name
        if not path.is_file() or sha256(path)!=expected: mismatches.append(name)
    if mismatches:
        print(f'[FAIL] {len(mismatches)} original files missing/changed:',*mismatches,sep='\n')
        raise SystemExit(1)
    print(f'[PASS] {len(provenance["sha256_unmodified_original"])} historical files unchanged.')
    print('Declared difference:',provenance['declared_modified_original'])

if __name__=='__main__':main()
