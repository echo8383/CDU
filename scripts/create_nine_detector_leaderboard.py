from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
L2 = ROOT / 'layer2_results'

six = pd.read_csv(L2 / 'SIX_DETECTOR_RESULTS.csv')
six = six.rename(columns={'Series':'n_series','positive_series_ratio':'positive_series_ratio'})
six = six[['Detector','n_series','Raw_VUS','CDU_5fold_bits','CDU_10fold_bits',
           'CDU_CI_low','CDU_CI_high','positive_series_ratio',
           'bootstrap_prob_macro_positive','Global_Hard20_VUS',
           'Global_Hard30_VUS','Global_Hard50_VUS','Family_Hard20_VUS',
           'Family_Hard30_VUS','Easy20_VUS','Audit_status']]

new = pd.read_csv(L2 / 'detector_cdu_hardvus_summary_completed.csv')
# The completed summary also contains the older TimesNet row. TimesNet is
# already represented by the audited six-detector table; only add the three
# genuinely new detectors here.
new = new[new['Detector'].isin(['FITS','M2N2','TranAD'])].copy()
new = new.rename(columns={'P_CDU_gt_0':'positive_series_ratio'})
new['n_series'] = 350
new['bootstrap_prob_macro_positive'] = np.nan
new['Audit_status'] = 'PINNED_CACHE_COMPLETE'

# Compute the same series-level median, positive ratio, and paired bootstrap
# probability for the three newly added detectors from their cached CDU rows.
for det in ['FITS','M2N2','TranAD']:
    p = L2 / f'{det}_cdu_per_series.csv'
    d = pd.read_csv(p)
    d5 = d[d['folds'].astype(int) == 5]['CDU_bits'].to_numpy(float)
    row = new['Detector'].eq(det)
    rng = np.random.default_rng(2024)
    boot = np.array([d5[rng.integers(0, len(d5), len(d5))].mean() for _ in range(10000)])
    new.loc[row, 'CDU_median_5fold'] = np.median(d5)
    new.loc[row, 'positive_series_ratio'] = np.mean(d5 > 0)
    new.loc[row, 'bootstrap_prob_macro_positive'] = np.mean(boot > 0)

new = new[['Detector','n_series','Raw_VUS','CDU_5fold_bits','CDU_10fold_bits',
           'CDU_CI_low','CDU_CI_high','positive_series_ratio',
           'bootstrap_prob_macro_positive','Global_Hard20_VUS',
           'Global_Hard30_VUS','Global_Hard50_VUS','Family_Hard20_VUS',
           'Family_Hard30_VUS','Easy20_VUS','Audit_status']]

# TimesNet is present in SIX_DETECTOR_RESULTS; all other six are as audited.
all_df = pd.concat([six, new], ignore_index=True)
all_df['Raw_rank'] = all_df['Raw_VUS'].rank(method='min', ascending=False).astype(int)
all_df['CDU5_rank'] = all_df['CDU_5fold_bits'].rank(method='min', ascending=False).astype(int)
order = ['Raw_rank','CDU5_rank','Detector']
all_df = all_df.sort_values(order).reset_index(drop=True)
cols = ['Raw_rank','CDU5_rank','Detector','n_series','Raw_VUS',
        'CDU_5fold_bits','CDU_10fold_bits','CDU_CI_low','CDU_CI_high',
        'positive_series_ratio','bootstrap_prob_macro_positive',
        'Global_Hard20_VUS','Global_Hard30_VUS','Global_Hard50_VUS',
        'Family_Hard20_VUS','Family_Hard30_VUS','Easy20_VUS','Audit_status']
all_df[cols].to_csv(L2 / 'NINE_DETECTOR_LEADERBOARD.csv', index=False)

def fmt(x):
    return 'NA' if pd.isna(x) else f'{float(x):.6f}'

lines = ['# Nine-detector leaderboard', '',
         '数据均来自当前 pinned score cache；未重新运行 detector。Raw VUS/CDU 不与历史 leaderboard 数值混用。', '',
         '| Raw rank | CDU rank | Detector | Raw VUS | CDU 5-fold (bits) | CDU 10-fold (bits) | Family-Hard-20 VUS | Family-Hard-30 VUS | Audit status |',
         '|---:|---:|---|---:|---:|---:|---:|---:|---|']
for _, r in all_df.sort_values('Raw_rank').iterrows():
    lines.append(f"| {int(r.Raw_rank)} | {int(r.CDU5_rank)} | {r.Detector} | {fmt(r.Raw_VUS)} | {fmt(r.CDU_5fold_bits)} | {fmt(r.CDU_10fold_bits)} | {fmt(r.Family_Hard20_VUS)} | {fmt(r.Family_Hard30_VUS)} | {r.Audit_status} |")
lines += ['', '## 解释', '',
          '- Raw rank 与 CDU rank 分别按 350-series macro 均值降序排列。',
          '- `positive_series_ratio` 是 5-fold 中 CDU_i > 0 的 series 比例；`bootstrap_prob_macro_positive` 是 bootstrap macro mean > 0 的比例，两者分开保存。',
          '- AnomalyTransformer 的既有审计状态为 FAIL（两条常数 score 序列）；TimesNet 为既有 preliminary/consistency cache，未纳入严格三模型 audit PASS。',
          '- FITS、M2N2、TranAD 是本轮 pinned cache complete；这表示 score/CDU 已生成，不等同于历史 leaderboard exact parity。']
(ROOT / 'NINE_DETECTOR_LEADERBOARD.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(all_df[cols].to_string(index=False))
