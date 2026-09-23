"""Matched detector-only, sampling-seed, and spline basis-family experiments."""
import argparse
import gc
import hashlib
import json
import time
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from run_rank_probe_extension import Probe, score, SAMPLE_VERSION, HGB
from evaluate_cdu_protocol_v1 import DETECTORS, load_source_map, log_loss_bits
from run_symmetric_rank import read_ranked_basis
from run_basis_sensitivity import FAMILIES, keep_columns, checkpoint, summarize
from run_probe_robustness import sample_indices, weights
from run_protocol_v1_controls import atomic_csv, atomic_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['detector_only','seed','basis'], required=True)
    p.add_argument('--probe', choices=['linear','spline','hgb'], default='spline')
    p.add_argument('--sample-seed', type=int, default=0)
    p.add_argument('--drop-family', choices=list(FAMILIES))
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--max-new-folds', type=int, default=0)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    if a.mode == 'basis' and not a.drop_family:
        p.error('basis mode requires --drop-family')
    if a.mode == 'detector_only' and a.sample_seed != 0:
        p.error('detector-only must match completed seed-0 results')
    if a.mode != 'basis' and a.drop_family:
        p.error('--drop-family requires basis mode')
    mapping = load_source_map()
    ids, sources = sorted(mapping), sorted(set(mapping.values()))
    tag = f'{a.mode}_{a.probe}_seed{a.sample_seed}' + (f'_{a.drop_family}' if a.drop_family else '')
    out = ROOT / 'protocol_followup_results' / tag
    sample_version = SAMPLE_VERSION if a.sample_seed == 0 else f'{SAMPLE_VERSION}|replicate={a.sample_seed}'
    config = dict(mode=a.mode, probe=a.probe, sample_seed=a.sample_seed, sample_version=sample_version,
                  drop_family=a.drop_family, cap=2048, test='all', C=.1, hgb=HGB,
                  spline_knots=[0,1/3,2/3,1], weighting='source-series-time hierarchical',
                  files={f:hashlib.sha256((ROOT/'scripts'/f).read_bytes()).hexdigest() for f in
                         ['run_cdu_followup.py','run_rank_probe_extension.py','run_basis_sensitivity.py',
                          'evaluate_cdu_protocol_v1.py','run_probe_robustness.py']},
                  source_map=mapping)
    parent = ROOT / 'protocol_rank_probe_results/cap2048' / a.probe
    config['parent_manifest_hash'] = hashlib.sha256((parent/'RUN_MANIFEST.json').read_bytes()).hexdigest()
    signature = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    manifest = out/'RUN_MANIFEST.json'
    if manifest.exists() and json.loads(manifest.read_text())['signature'] != signature:
        raise RuntimeError('Checkpoint configuration changed')
    atomic_json(dict(config=config,signature=signature),manifest)
    rows, bs, ys, cursor = [], [], [], 0
    for k,sid in enumerate(ids,1):
        b,y,names = read_ranked_basis(sid)
        keep = keep_columns(names,a.drop_family) if a.drop_family else np.ones(31,bool)
        idx = sample_indices(sid,len(y),2048,sample_version)
        bs.append(b[idx][:,keep]); ys.append(y[idx])
        rows.append(dict(series_id=sid,source=mapping[sid],start=cursor,end=cursor+len(idx),n_full=len(y)))
        cursor += len(idx)
        if k%50==0: print(f'[{tag}/prepare] {k}/350',flush=True)
    xall,yall = np.concatenate(bs),np.concatenate(ys)
    del bs,ys,b,y
    tasks = list(DETECTORS) if a.mode=='detector_only' else ['baseline',*DETECTORS]
    new_folds=0
    with threadpool_limits(limits=a.threads):
        for task in tasks:
            sall=None
            if task!='baseline':
                sall=np.concatenate([score(r['series_id'],task,r['n_full'])[
                    sample_indices(r['series_id'],r['n_full'],2048,sample_version)] for r in rows])
            directory=out/task
            for number,source in enumerate(sources,1):
                path=directory/'by_source'/f'{source}.csv'
                train=[r for r in rows if r['source']!=source]
                test=[r for r in rows if r['source']==source]
                expected={r['series_id'] for r in test}
                if checkpoint(path,signature,expected) is not None:
                    print(f'[{tag}/{task}] {number}/23 {source}: SKIP',flush=True); continue
                started=time.perf_counter()
                idx=np.concatenate([np.arange(r['start'],r['end']) for r in train])
                x=xall[idx] if a.mode!='detector_only' else sall[idx,None]
                if task!='baseline' and a.mode!='detector_only': x=np.column_stack([x,sall[idx]])
                y=yall[idx]; w=weights(train)
                prior=float(np.clip(np.average(y,weights=w),1e-7,1-1e-7))
                print(f'[{tag}/{task}] {number}/23 {source}: FIT n={len(y)} p={x.shape[1]}',flush=True)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    model=Probe(a.probe).fit(x,y,w)
                del x,y,w,idx
                reference=None
                if task!='baseline':
                    reference_path = (parent/task/'PER_SERIES.csv' if a.mode=='detector_only'
                                      else out/'baseline/by_source'/f'{source}.csv')
                    reference=pd.read_csv(reference_path).set_index('series_id')
                output=[]
                for r in test:
                    sid=r['series_id']; b,y,_=read_ranked_basis(sid)
                    x=b[:,keep]
                    if task!='baseline':
                        s=score(sid,task,len(y))
                        x=s[:,None] if a.mode=='detector_only' else np.column_stack([x,s])
                    loss=log_loss_bits(y,model.predict_proba(x)[:,1])
                    l0=log_loss_bits(y,np.full(len(y),prior))
                    if not np.isfinite([loss,l0]).all(): raise RuntimeError('nonfinite loss')
                    item=dict(series_id=sid,source_dataset=source,condition=task,n_points=len(y),
                              n_anomalies=int(y.sum()),L_null=l0)
                    if task=='baseline': item['L_basis']=loss
                    elif a.mode=='detector_only':
                        ref=reference.loc[sid]
                        assert ref.n_points==len(y) and ref.n_anomalies==int(y.sum())
                        item.update(L_detector=loss,detector_utility=l0-loss,L_basis=float(ref.L_basis),
                                    L_basis_detector=float(ref.L_basis_detector),CDU=float(ref.CDU))
                    else:
                        lb=float(reference.loc[sid].L_basis)
                        item.update(L_basis=lb,L_basis_detector=loss,CDU=lb-loss)
                    output.append(item)
                elapsed=time.perf_counter()-started
                atomic_csv(pd.DataFrame(output),path)
                atomic_json(dict(signature=signature,runtime_seconds=elapsed,test_source=source,
                                 training_sources=sorted({r['source'] for r in train}),
                                 warnings=[str(v.message) for v in caught]),path.with_suffix('.json'))
                print(f'[{tag}/{task}] {number}/23 {source}: PASS runtime={elapsed:.1f}s',flush=True)
                del model,x,b,y; gc.collect(); new_folds+=1
                if a.max_new_folds and new_folds>=a.max_new_folds: return
            frame=pd.concat([pd.read_csv(directory/'by_source'/f'{s}.csv') for s in sources],ignore_index=True)
            atomic_csv(frame,directory/'PER_SERIES.csv')
            if task!='baseline': summarize(directory,sources,signature,task)
            if a.mode=='detector_only':
                source_frame=frame.groupby('source_dataset')[['L_null','L_basis','L_detector','L_basis_detector','detector_utility','CDU']].mean()
                atomic_csv(source_frame.reset_index(),directory/'FOUR_LOSS_PER_SOURCE.csv')
    atomic_json(dict(status='COMPLETE',signature=signature),out/'QUEUE_STATUS.json')


if __name__=='__main__': main()
