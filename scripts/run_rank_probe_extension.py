"""Matched linear/spline/HGB sensitivity on frozen ranked scores; source checkpoints."""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import SplineTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from evaluate_cdu_protocol_v1 import DETECTORS, CACHE_DIRS, average_rank01, load_source_map, make_probe, log_loss_bits
from run_probe_robustness import sample_indices, weights
from run_basis_sensitivity import checkpoint, summarize
from run_symmetric_rank import read_ranked_basis, RANKED
from run_symmetric_rank_controls import CONTROL_ROOT, CONTROLS
from run_protocol_v1_controls import atomic_csv, atomic_json

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_VERSION = 'rank-probe-matched-v1'
HGB = dict(learning_rate=.1, max_iter=32, max_leaf_nodes=7, max_depth=3,
           min_samples_leaf=100, l2_regularization=1., max_bins=31,
           early_stopping=False, random_state=2024)


class Probe:
    def __init__(self, kind):
        self.kind = kind
        self.transform = None
        self.model = HistGradientBoostingClassifier(**HGB) if kind == 'hgb' else make_probe(.1)

    def fit(self, x, y, sample_weight):
        if self.kind == 'spline':
            # Fixed knots on the declared [0,1] rank interface; no label tuning.
            self.transform = SplineTransformer(degree=3, knots=np.tile(
                np.linspace(0., 1., 4)[:, None], (1, x.shape[1])),
                include_bias=False, sparse_output=True, extrapolation='constant')
            x = self.transform.fit_transform(x)
        self.model.fit(x, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, x):
        parts = []
        for start in range(0, len(x), 32768):
            chunk = x[start:start + 32768]
            if self.transform is not None:
                chunk = self.transform.transform(chunk)
            parts.append(self.model.predict_proba(chunk))
        return np.concatenate(parts)


def score(sid, task, n):
    path = (CONTROL_ROOT / task if task in CONTROLS else CACHE_DIRS[task]) / f'{sid}.npy'
    raw = np.load(path, allow_pickle=False)
    if raw.shape != (n,) or not np.isfinite(raw).all():
        raise RuntimeError(f'Invalid score {task}/{sid}')
    return average_rank01(raw).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', choices=['linear', 'spline', 'hgb'], required=True)
    parser.add_argument('--training-cap', type=int, default=2048)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--max-new-folds', type=int, default=0)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.training_cap <= 0:
        parser.error('training-cap must be positive')
    mapping = load_source_map()
    ids, sources = sorted(mapping), sorted(set(mapping.values()))
    folder = ROOT / 'protocol_rank_probe_results' / f'cap{args.training_cap}' / args.probe
    cfg = dict(probe=args.probe, training_cap=args.training_cap, C=.1,
               spline=dict(degree=3, knots=[0., 1/3, 2/3, 1.], include_bias=False),
               hgb=HGB, sample_version=SAMPLE_VERSION, test_points='all',
               aggregation='source macro of series mean loss', bootstrap_seed=2024,
               runner_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               basis_manifest=hashlib.sha256((RANKED / 'MANIFEST.json').read_bytes()).hexdigest(),
               source_map=mapping)
    cfg['dependencies'] = {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                           for name in ['run_symmetric_rank.py', 'evaluate_cdu_protocol_v1.py',
                                        'run_probe_robustness.py', 'run_basis_sensitivity.py']}
    paths = [CACHE_DIRS[d] / f'{sid}.npy' for d in DETECTORS for sid in ids]
    paths += [CONTROL_ROOT / d / f'{sid}.npy' for d in CONTROLS for sid in ids]
    cfg['score_identity'] = [(str(p.relative_to(ROOT)), p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
    signature = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    manifest = folder / 'RUN_MANIFEST.json'
    if manifest.exists() and json.loads(manifest.read_text())['signature'] != signature:
        raise RuntimeError('Existing version differs; use separate outputs')
    atomic_json(dict(config=cfg, signature=signature), manifest)
    arrays, labels, rows, cursor = [], [], [], 0
    for k, sid in enumerate(ids, 1):
        b, y, names = read_ranked_basis(sid)
        idx = sample_indices(sid, len(y), args.training_cap, SAMPLE_VERSION)
        arrays.append(b[idx]); labels.append(y[idx])
        rows.append(dict(series_id=sid, source=mapping[sid], start=cursor,
                         end=cursor + len(idx), n_full=len(y)))
        cursor += len(idx)
        if k % 50 == 0:
            print(f'[{args.probe}/prepare] {k}/350', flush=True)
    xall, yall = np.concatenate(arrays), np.concatenate(labels)
    del arrays, labels, b, y
    fitted = 0
    with threadpool_limits(limits=args.threads):
        for task in ['baseline', *CONTROLS, *DETECTORS]:
            directory = folder / task
            for number, source in enumerate(sources, 1):
                target = directory / 'by_source' / f'{source}.csv'
                test = [r for r in rows if r['source'] == source]
                train = [r for r in rows if r['source'] != source]
                expected = {r['series_id'] for r in test}
                if checkpoint(target, signature, expected) is not None:
                    print(f'[{args.probe}/{task}] {number}/23 {source}: SKIP', flush=True)
                    continue
                started = time.perf_counter()
                x = np.concatenate([xall[r['start']:r['end']] for r in train])
                y = np.concatenate([yall[r['start']:r['end']] for r in train])
                if task != 'baseline':
                    curves = []
                    for r in train:
                        s = score(r['series_id'], task, r['n_full'])
                        idx = sample_indices(r['series_id'], len(s), args.training_cap, SAMPLE_VERSION)
                        curves.append(s[idx])
                    x = np.column_stack([x, np.concatenate(curves)])
                    del curves
                print(f'[{args.probe}/{task}] {number}/23 {source}: FIT n={len(y)}', flush=True)
                model = Probe(args.probe).fit(x, y, weights(train))
                del x, y
                reference = None
                if task != 'baseline':
                    reference = checkpoint(folder / 'baseline/by_source' / f'{source}.csv', signature, expected).set_index('series_id')
                output = []
                for r in test:
                    sid = r['series_id']
                    b, y, _ = read_ranked_basis(sid)
                    if task != 'baseline':
                        b = np.column_stack([b, score(sid, task, len(y))])
                    loss = log_loss_bits(y, model.predict_proba(b)[:, 1])
                    if not np.isfinite(loss):
                        raise RuntimeError(f'Nonfinite loss {task}/{sid}')
                    item = dict(series_id=sid, source_dataset=source, condition=task,
                                n_points=len(y), n_anomalies=int(y.sum()))
                    if task == 'baseline':
                        item['L_basis'] = loss
                    else:
                        lb = float(reference.loc[sid].L_basis)
                        item.update(L_basis=lb, L_basis_detector=loss, CDU=lb-loss)
                    output.append(item)
                elapsed = time.perf_counter() - started
                atomic_csv(pd.DataFrame(output), target)
                atomic_json(dict(signature=signature, runtime_seconds=elapsed,
                                 test_source=source, training_sources=sorted({r['source'] for r in train})),
                            target.with_suffix('.json'))
                print(f'[{args.probe}/{task}] {number}/23 {source}: PASS runtime={elapsed:.1f}s', flush=True)
                del model, b, y
                fitted += 1
                if args.max_new_folds and fitted >= args.max_new_folds:
                    return
            if task != 'baseline':
                summarize(directory, sources, signature, task)
            else:
                atomic_csv(pd.concat([pd.read_csv(directory / 'by_source' / f'{s}.csv') for s in sources]), directory / 'PER_SERIES.csv')
    atomic_json(dict(status='COMPLETE', signature=signature), folder / 'QUEUE_STATUS.json')


if __name__ == '__main__':
    main()
