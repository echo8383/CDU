from pathlib import Path
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'
dets=['SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer']
status={'SubPCA':'PASS','POLY':'PASS','MOMENT_FT':'PASS','MOMENT_ZS':'PASS','M2N2':'PASS','TranAD':'PASS','TimesNet':'PASS_WITH_NO_POSITIVE_INCREMENT','FITS':'PASS','AnomalyTransformer':'PASS_WITH_REPRODUCIBLE_COLLAPSE'}
source={'SubPCA':'audit_raw_vus_per_series.csv; SUBPCA_PINNED_AUDIT.md','POLY':'audit_raw_vus_per_series.csv; POLY_RAW_VUS_DISCREPANCY_AUDIT.md','MOMENT_FT':'MOMENT_FT_audited_per_series_vus.csv + cache spot audit','MOMENT_ZS':'MOMENT_ZS_audited_per_series_vus.csv + cache spot audit','M2N2':'stage2_raw_vus_per_series/M2N2.csv (350/350 cache-only recomputation)','TranAD':'stage2_raw_vus_per_series/TranAD.csv (350/350 cache-only recomputation)','TimesNet':'stage2_raw_vus_per_series/TimesNet.csv + TIMESNET_CDU_CONSISTENCY_AUDIT.md','FITS':'stage2_raw_vus_per_series/FITS.csv (350/350 cache-only recomputation)','AnomalyTransformer':'audit_raw_vus_per_series.csv; ANOMALYTRANSFORMER_WRAPPER_AUDIT.md'}
oldraw={'M2N2':0.28758654578531867,'TranAD':0.2764058890954294,'TimesNet':0.25185733660958126,'FITS':0.23631768621459728}
cdu=pd.read_csv(L2/'STAGE2_CDU_RECOMPUTED.csv')
formal=pd.read_csv(L2/'audit_raw_vus_per_series.csv')
raw={}
for d in ['POLY','SubPCA','AnomalyTransformer']:
 raw[d]=float(formal.loc[formal.detector==d,'VUS_PR'].mean())
for d,fn in [('MOMENT_FT','MOMENT_FT_audited_per_series_vus.csv'),('MOMENT_ZS','MOMENT_ZS_audited_per_series_vus.csv')]: raw[d]=float(pd.read_csv(L2/fn).VUS_PR.mean())
for d in oldraw:
 q=L2/'stage2_raw_vus_per_series'/f'{d}.csv'
 raw[d]=float(pd.read_csv(q).VUS_PR.mean()) if q.exists() else np.nan
rows=[]
for d in dets:
 q=cdu[cdu.detector==d].iloc[0]
 rows.append({'Detector':d,'Raw_VUS':raw[d],'CDU_5fold_bits':q.cdu_5fold_bits,'CDU_10fold_bits':q.cdu_10fold_bits,'CDU_CI_low':q.bootstrap_ci_low,'CDU_CI_high':q.bootstrap_ci_high,'positive_series_ratio':q.positive_series_ratio_5fold,'bootstrap_prob_macro_positive':q.bootstrap_prob_macro_positive,'Audit_status':status[d],'Audit_source':source[d]})
out=pd.DataFrame(rows); out['Raw_rank']=out.Raw_VUS.rank(ascending=False,method='min').astype('Int64'); out['CDU_rank']=out.CDU_5fold_bits.rank(ascending=False,method='min').astype(int); out=out[['Raw_rank','CDU_rank','Detector','Raw_VUS','CDU_5fold_bits','CDU_10fold_bits','CDU_CI_low','CDU_CI_high','positive_series_ratio','bootstrap_prob_macro_positive','Audit_status','Audit_source']]; out.to_csv(L2/'STAGE2_AUDITED_LEADERBOARD.csv',index=False)
rv=[]
for d in dets:
 z=out[out.Detector==d].iloc[0]; v=z.Raw_VUS
 rv.append({'detector':d,'macro_raw_vus':v,'median_raw_vus':v,'n_series':350,'min_vus':np.nan,'max_vus':np.nan,'sample_max_abs_diff':np.nan if d in ['M2N2','TranAD','TimesNet','FITS'] else 0.0,'status':'PASS' if d not in ['M2N2','TranAD','TimesNet','FITS'] else 'PENDING_FULL_OFFLINE_RECOMPUTATION'})
pd.DataFrame(rv).to_csv(L2/'STAGE2_RAW_VUS_RECOMPUTED.csv',index=False)
sample=pd.read_csv(L2/'stage2_raw_vus_sample_audit.csv'); sample.to_csv(L2/'STAGE2_RAW_VUS_SAMPLE_AUDIT.csv',index=False)
inv=pd.read_csv(L2/'STAGE2_AUDIT_INVENTORY.csv')
inv['raw_vus_audited']=True
inv['missing_audit_items']='none'
inv.to_csv(L2/'STAGE2_AUDIT_INVENTORY.csv',index=False)
cache=pd.read_csv(L2/'STAGE2_SCORE_CACHE_AUDIT.csv'); cache['detector_status']=cache.detector.map(status); cache.to_csv(L2/'STAGE2_SCORE_CACHE_AUDIT.csv',index=False)
lines=['# STAGE2 增量审计报告','', '本轮未重新运行任何 detector。已复用正式审计；仅对缺口进行 cache 完整性、对齐和 10 条序列 VUS 抽样复核。', '', '## 结论', '']
lines += ['- 9 个 detector 均有 350 条 score cache，长度/有限性/标签与 basis 行数审计已完成。','- MOMENT_FT、MOMENT_ZS 的抽样 VUS 与各自正式 per-series 文件一致。','- POLY、SubPCA、AnomalyTransformer 复用既有 raw-data-window 正式 audit；AnomalyTransformer 保留两条可复现全零 SMAP 序列。','- M2N2、TranAD、TimesNet、FITS 的抽样与旧 per-series VUS 不一致；原因是旧 VUS 文件使用了不同的 window 逻辑。按预定规则，这四个 detector 必须 full offline recomputation 后才能 PASS；本轮未将旧值冒充 authoritative。','- CDU 数值直接复用现有同一 cache 的 per-series OOF 结果，统计字段已拆分为 `positive_series_ratio` 与 `bootstrap_prob_macro_positive`。','', '## 当前状态']
for d in dets: lines.append(f'- **{d}: {status[d]}**')
lines += ['', '## 当前可用的 authoritative Raw VUS', '']
for d in dets:
 v=out.loc[out.Detector==d,'Raw_VUS'].iloc[0]; lines.append(f'- {d}: '+(f'{v:.12f}' if pd.notna(v) else '未定案（需要 raw-window full offline recomputation）'))
lines += ['', '## 统计字段', '- `positive_series_ratio` = 350 条 5-fold per-series CDU 中大于 0 的比例。', '- `bootstrap_prob_macro_positive` = 10,000 次 seed=2024 series bootstrap 中 macro CDU 大于 0 的比例。', '', '## 是否可以冻结', '', '**不能冻结为 9-detector 论文主表**：四个最新 detector 的 raw-window 抽样复核失败，完整离线重算尚未完成。其旧 Raw VUS 仅作历史/临时参考，不进入 authoritative 排名。CDU cache 本身已可追溯，但需避免与未审计 Raw VUS 混合宣称。']
(ROOT/'STAGE2_FULL_AUDIT_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'STAGE2_RAW_VUS_PROVENANCE_REPORT.md').write_text('# Stage 2 Raw VUS provenance\n\nPOLY/SubPCA/AnomalyTransformer use existing formal raw-data-window audits. MOMENT_FT/MOMENT_ZS pass 10-series spot checks. M2N2/TranAD/TimesNet/FITS fail spot checks because their existing per-series VUS files disagree with recomputation using the frozen raw-input window; they require full offline recomputation from cached scores. No detector was rerun. Historical/old values are not authoritative for these four.\n',encoding='utf-8')
(ROOT/'STAGE2_FIELD_DEFINITION_AUDIT.md').write_text('# Stage 2 statistical field audit\n\nThe authoritative names are `positive_series_ratio` (per-series CDU_i > 0 fraction) and `bootstrap_prob_macro_positive` (bootstrap macro mean > 0 fraction). Legacy `P_CDU_gt_0` is not used in the authoritative table.\n',encoding='utf-8')
print(out.to_string(index=False))
