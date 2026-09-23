"""Reconcile completed Fast outputs and cached Raw VUS; never fit a model."""
from pathlib import Path
import hashlib
import json
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/evidence/fast_main'
DETECTORS = ['SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer']
LOSS = ['L_null','L_basis','L_detector','L_basis_detector','basis_utility','detector_utility','CDU']


def main():
    provenance = []
    def read(path):
        provenance.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        return pd.read_csv(path)
    mapping = json.loads((ROOT/'source_groups.json').read_text(encoding='utf-8'))['series_to_source']
    ids = sorted(mapping)
    base = read(ROOT/'protocol_fast_results/shared_baseline/PER_SERIES.csv').set_index('series_id').loc[ids]
    old = read(ROOT/'layer2_results/STAGE2_AUDITED_LEADERBOARD.csv').set_index('Detector')
    summaries, per_series, per_source, integrity, sensitivity = [], [], [], [], []
    rng = np.random.default_rng(2024)
    draws = rng.integers(0,23,size=(10000,23))
    for detector in DETECTORS:
        folder = ROOT/'protocol_fast_results/main'/detector
        raw_path = (ROOT/'layer2_results/audit_raw_vus_per_series.csv' if detector in ['SubPCA','POLY','AnomalyTransformer']
                    else ROOT/f'layer2_results/{detector}_audited_per_series_vus.csv' if detector.startswith('MOMENT_')
                    else ROOT/f'layer2_results/stage2_raw_vus_per_series/{detector}.csv')
        raw = read(raw_path)
        raw = raw.loc[raw.detector == detector].copy()
        series = read(folder/'PER_SERIES.csv')
        summary = read(folder/'SUMMARY.csv').iloc[0]
        stored_source = read(folder/'PER_SOURCE.csv').set_index('source_dataset').sort_index()
        for frame in [raw, series]:
            if len(frame)!=350 or frame.series_id.nunique()!=350 or set(frame.series_id)!=set(ids):
                raise ValueError(f'{detector}: population mismatch')
        series = series.set_index('series_id').loc[ids]
        raw = raw.set_index('series_id').loc[ids]
        if not (series.detector == detector).all() or not (series.protocol_version == 'CDU-protocol-fast-v1').all():
            raise ValueError(f'{detector}: definition mismatch')
        if not (series.source_dataset == pd.Series(mapping).loc[ids]).all():
            raise ValueError(f'{detector}: source mismatch')
        if not np.isfinite(series[LOSS].to_numpy()).all() or not np.isfinite(raw.VUS_PR).all():
            raise ValueError(f'{detector}: nonfinite data')
        for col in ['L_null','L_basis','n_points','n_anomalies']:
            np.testing.assert_allclose(series[col],base[col],atol=1e-14,rtol=0)
        for col,left,right in [('CDU','L_basis','L_basis_detector'),('detector_utility','L_null','L_detector'),('basis_utility','L_null','L_basis')]:
            np.testing.assert_allclose(series[col],series[left]-series[right],atol=1e-14,rtol=0)
        for col in ['C_basis','C_detector','C_basis_detector']:
            if not (series[col] == 0.1).all(): raise ValueError(f'{detector}: C drift')
        for ordinal, sid in enumerate(ids,1):
            cache = ROOT/('layer2_results/poly_pinned_scores' if detector=='POLY' else f'layer2_results/detector_scores/{detector}')/(sid+'.npy')
            score = np.load(cache,allow_pickle=False)
            if score.ndim!=1 or len(score)!=int(series.loc[sid,'n_points']) or not np.isfinite(score).all():
                raise ValueError(f'{detector}/{sid}: invalid cache')
            digest = hashlib.sha256(np.ascontiguousarray(score,dtype=np.float64).tobytes()).hexdigest()
            if digest != raw.loc[sid,'score_hash']:
                raise ValueError(f'{detector}/{sid}: Raw VUS cache hash mismatch')
            integrity.append({'detector':detector,'series_id':sid,'score_hash':digest,'n_points':len(score),'raw_hash_match':True})
            if ordinal%100==0: print(f'[{detector}] cache identity {ordinal}/350',flush=True)
        series['Raw_VUS'] = raw.VUS_PR
        source = series.groupby('source_dataset')[LOSS+['Raw_VUS']].mean().sort_index()
        if len(source)!=23: raise ValueError('Missing source')
        np.testing.assert_allclose(source[LOSS],stored_source[LOSS],atol=1e-14,rtol=0)
        means = source[LOSS].mean()
        np.testing.assert_allclose(means,summary[LOSS].to_numpy(dtype=float),atol=1e-14,rtol=0)
        boot = source.CDU.to_numpy()[draws].mean(axis=1)
        low,high = np.quantile(boot,[.025,.975])
        prob = (boot>0).mean()
        np.testing.assert_allclose([low,high,prob],[summary.CDU_CI_low,summary.CDU_CI_high,summary.bootstrap_prob_source_macro_positive],atol=1e-14,rtol=0)
        np.testing.assert_allclose(raw.VUS_PR.mean(),old.loc[detector,'Raw_VUS'],atol=1e-12,rtol=0)
        row={'Detector':detector,'Raw_VUS':raw.VUS_PR.mean(),'Source_macro_Raw_VUS':source.Raw_VUS.mean(),**means.to_dict(),
             'CDU_CI_low':low,'CDU_CI_high':high,'positive_sources':int((source.CDU>0).sum()),
             'bootstrap_prob_source_macro_positive':prob,'n_series':350,'n_sources':23,
             'status':'COMPLETE_CI_INCLUDES_ZERO' if low<=0<=high else 'COMPLETE_CI_EXCLUDES_ZERO',
             'Raw_source':raw_path.relative_to(ROOT).as_posix(),'Fast_source':folder.relative_to(ROOT).as_posix()}
        summaries.append(row)
        series['detector']=detector
        source['detector']=detector
        per_series.append(series.reset_index()); per_source.append(source.reset_index())
        for omitted in source.index:
            sensitivity.append({'detector':detector,'omitted_source':omitted,'CDU_without_source':source.drop(omitted).CDU.mean(),
                                'method':'reaggregate existing OOF losses; no probe refitting'})
    table=pd.DataFrame(summaries)
    for metric,rank in [('Raw_VUS','Raw_rank'),('Source_macro_Raw_VUS','Source_raw_rank'),('detector_utility','Utility_rank'),('CDU','CDU_rank')]:
        table[rank]=table[metric].rank(ascending=False,method='min').astype(int)
    table['Raw_to_CDU_uplift']=table.Raw_rank-table.CDU_rank
    table['Source_raw_to_CDU_uplift']=table.Source_raw_rank-table.CDU_rank
    associations=[]
    for metric in ['Raw_VUS','Source_macro_Raw_VUS','detector_utility']:
        associations.append({'metric':metric,'versus':'CDU','spearman_rho':spearmanr(table[metric],table.CDU).statistic,
                             'kendall_tau':kendalltau(table[metric],table.CDU).statistic,'n_detectors':9,'interpretation':'descriptive; no causal claim'})
    OUT.mkdir(parents=True,exist_ok=True)
    table.to_csv(OUT/'MAIN_RESULTS.csv',index=False)
    pd.concat(per_series).to_csv(OUT/'PER_SERIES.csv',index=False)
    pd.concat(per_source).to_csv(OUT/'PER_SOURCE.csv',index=False)
    pd.DataFrame(integrity).to_csv(OUT/'CACHE_RAW_LINK.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(OUT/'SOURCE_SENSITIVITY.csv',index=False)
    pd.DataFrame(associations).to_csv(OUT/'RANK_ASSOCIATIONS.csv',index=False)
    for rel in ['source_groups.json','scripts/run_protocol_fast.py','scripts/evaluate_cdu_protocol_v1.py']:
        provenance.append({'path':rel,'sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()})
    (OUT/'manifest.json').write_text(json.dumps({'as_of':datetime.now().astimezone().isoformat(),'sources':provenance,
        'scope':'existing Fast loss arithmetic, bootstrap, Raw cache identity and aggregation; no detector/probe fit',
        'limitation':'No independent refitting of Fast losses; Fast checkpoints do not store run-time score hashes. Current Raw cache identity is verified; historical Fast input identity depends on frozen-run provenance.'},indent=2)+'\n',encoding='utf-8')
    tex=[r'\begin{table*}[t]',r'\centering',r'\small',
         r'\caption{Nine frozen detector instances under fixed-$C$ source-LOSO evaluation. Raw VUS is series-macro; Raw$_s$ is source-macro. Utilities and percentile source-bootstrap intervals are in bits. All CDU intervals include zero.}',
         r'\label{tab:main}',r'\begin{tabular}{lrrrrrl}',r'\toprule',r'Detector & Raw VUS & Raw$_s$ & $U_D$ & CDU & Positive sources & CDU 95\% CI\\',r'\midrule']
    for row in table.to_dict('records'):
        name=row['Detector'].replace('_','-')
        tex.append(f"{name} & {row['Raw_VUS']:.4f} & {row['Source_macro_Raw_VUS']:.4f} & {row['detector_utility']:.6f} & {row['CDU']:.6f} & {row['positive_sources']}/23 & $[{row['CDU_CI_low']:.6f},{row['CDU_CI_high']:.6f}]$"+r'\\')
    tex += [r'\bottomrule',r'\end{tabular}',r'\end{table*}']
    (ROOT/'icassp/tables').mkdir(exist_ok=True)
    (ROOT/'icassp/tables/main_results.tex').write_text('\n'.join(tex)+'\n',encoding='utf-8')
    print(table[['Detector','Raw_VUS','Source_macro_Raw_VUS','detector_utility','CDU','Raw_rank','CDU_rank']].to_string(index=False))
    print(pd.DataFrame(associations).to_string(index=False))


if __name__=='__main__':
    main()
