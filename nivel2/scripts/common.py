"""Common, intentionally read-only loading and provenance helpers for Level 2."""
from __future__ import annotations
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd


def fresh_dir(parent: Path, prefix: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid4().hex[:6]
        out = parent / (prefix + '_' + name)
        try:
            out.mkdir(exist_ok=False)
            return out
        except FileExistsError:
            pass
    raise RuntimeError('Cannot create a unique result directory')


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_runs(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    required = {'algorithm', 'dynamics', 'L', 'T', 'H', 'J', 'time_mcss', 'reached_M0',
                'cpu_seconds', 'events'}
    if missing := required.difference(data.columns):
        raise ValueError(f'{path}: missing columns {sorted(missing)}')
    if data.empty or data[['L','T','H','J','time_mcss']].isna().any().any():
        raise ValueError(f'{path}: empty/invalid numerical data')
    if not all(data[c].nunique() == 1 for c in ['L','T','H','J','dynamics','algorithm']):
        raise ValueError(f'{path}: mixed physical conditions')
    if not data['algorithm'].iloc[0] in ('standard', 'nfold'):
        raise ValueError(f'{path}: invalid algorithm')
    if (data['time_mcss'] < 0).any() or (data['events'] < 0).any():
        raise ValueError(f'{path}: negative time/event count')
    N = data['L'].to_numpy() ** 2
    expected = data['time_mcss'].to_numpy() * N
    attempts = (data['attempts'] if data['algorithm'].iloc[0] == 'standard'
                else data['equivalent_attempts']).to_numpy()
    if not np.allclose(expected, attempts, rtol=0, atol=1e-6):
        raise ValueError(f'{path}: MCSS != attempts/L^2')
    data.attrs['source'] = str(path)
    return data


def key(df: pd.DataFrame) -> tuple:
    r = df.iloc[0]
    return (int(r['L']), round(float(r['T']), 9), round(float(r['J']), 9),
            round(float(r['H']), 9), str(r['dynamics']), str(r['algorithm']))


def load_folder(folder: Path) -> dict[tuple, pd.DataFrame]:
    d = {}
    for filename in sorted(folder.glob('*.csv')):
        df = read_runs(filename)
        k = key(df)
        if k in d:
            raise ValueError(f'Duplicate physical condition in {folder}: {k}')
        d[k] = df
    return d


def mean_ci(data, seed: int, B: int = 400) -> tuple[float, float, float]:
    a = np.asarray(data, dtype=float)
    if a.size < 2 or np.any(~np.isfinite(a)) or np.any(a <= 0):
        raise ValueError('At least 2 complete positive lifetimes required for bootstrap')
    rng = np.random.default_rng(seed)
    means = np.empty(B)
    for start in range(0, B, 50):
        n = min(50, B - start)
        ii = rng.integers(0, a.size, size=(n, a.size))
        means[start:start + n] = a[ii].mean(axis=1)
    return float(a.mean()), *map(float, np.quantile(means, [.025, .975]))


def add_row_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
