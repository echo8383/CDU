"""Step 2: 在 TSB-AD-U 上跑 one-liner 基底，用官方 VUS-PR 度量。

目标：
  (a) 复现 ICLR 2026 报的 one-liner 量级（Var-96 ~0.42 级别、Last-3 ~0.28 级别）；
  (b) 得到每条序列上每条 one-liner 的 VUS-PR，作为去平凡化的基底成绩；
  (c) 与官方 32 个检测器的逐序列成绩对齐，算出"谁被平凡量解释了"。
"""
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import oneliners as ol
from vus_eval.basic_metrics import generate_curve

DATA_DIR = 'Datasets/TSB-AD-U'
SLIDING = 100          # TSB-AD 默认
THRE = 250

META = ['file', 'ts_len', 'anomaly_len', 'num_anomaly', 'avg_anomaly_len',
        'anomaly_ratio', 'point_anomaly', 'seq_anomaly']


def vus_pr(score, label):
    """官方 VUS-PR。"""
    score = np.nan_to_num(np.asarray(score, dtype=float), nan=0.0,
                          posinf=0.0, neginf=0.0)
    if score.std() == 0:
        return 0.0
    try:
        *_, _auc, ap = generate_curve(np.asarray(label, dtype=int), score,
                                      SLIDING, 'opt', THRE)
        return float(ap)
    except Exception:
        return np.nan


def process_file(fn):
    """处理一条序列；独立进程运行以并行化昂贵的 VUS-PR 循环。"""
    path = os.path.join(DATA_DIR, fn)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path).dropna()
    x = df.iloc[:, 0].values.astype(float)
    label = df['Label'].astype(int).to_numpy()
    sd = x.std()
    xz = (x - x.mean()) / (sd if sd > 0 else 1.0)
    names, B = ol.build_basis(xz)
    rec = {'file': fn, 'ts_len': len(xz)}
    for nm, b in zip(names, B):
        rec[nm] = vus_pr(b, label)
    return rec


def main(limit=None, out='step2_oneliner_vuspr.csv', workers=None):
    ref = pd.read_csv('uni_vuspr.csv')
    files = ref['file'].tolist()[:limit] if limit else ref['file'].tolist()
    # 已完成的行直接复用，允许长任务中断后继续。
    existing = {}
    if os.path.exists(out):
        try:
            old = pd.read_csv(out)
            # 断点文件会包含按全量文件列表 reindex 的空行；只有完整基底成绩才算已完成。
            required = 'Var-96' if 'Var-96' in old.columns else next((c for c in old.columns if c not in ('file','ts_len')), None)
            if required is not None:
                old = old[old[required].notna()]
            existing = {r['file']: r.to_dict() for _, r in old.iterrows()}
        except Exception:
            existing = {}
    todo = [f for f in files if f not in existing]
    rows = list(existing.values())
    t0 = time.time()
    n_workers = workers or max(1, min(os.cpu_count() or 2, 4))
    print(f'  已完成 {len(existing)}/{len(files)}，待处理 {len(todo)}，并行进程 {n_workers}', flush=True)
    if todo:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futs = {pool.submit(process_file, fn): fn for fn in todo}
            for k, fut in enumerate(as_completed(futs), 1):
                fn = futs[fut]
                try:
                    rec = fut.result()
                    if rec is not None:
                        rows.append(rec)
                except Exception as exc:
                    print(f'  [error] {fn}: {exc}', flush=True)
                else:
                    print(f'  完成 {k}/{len(todo)}: {fn}', flush=True)
                if k % 10 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f'  {k}/{len(todo)}  用时 {el:.0f}s  并行进程 {n_workers}', flush=True)
                    # 长序列任务可能被系统终止；周期性落盘保证可断点续跑。
                    ck = pd.DataFrame(rows).drop_duplicates('file').set_index('file').reindex(files).reset_index()
                    ck.to_csv(out, index=False)

    res = pd.DataFrame(rows)
    res = res.drop_duplicates('file').set_index('file').reindex(files).reset_index()
    res.to_csv(out, index=False)
    print(f'\n[已保存 {out}]  shape={res.shape}')

    ol_cols = [c for c in res.columns if c not in ('file', 'ts_len')]
    print('\n=== one-liner 均值 VUS-PR（降序）===')
    print(res[ol_cols].mean().sort_values(ascending=False).round(4).to_string())
    return res


if __name__ == '__main__':
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    w = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out = sys.argv[3] if len(sys.argv) > 3 else 'step2_oneliner_vuspr.csv'
    main(limit=lim, workers=w, out=out)
