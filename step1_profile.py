"""Step 1: 对 TSB-AD-U 官方逐序列 VUS-PR 矩阵做画像。

目的：在不下载任何数据的前提下，先摸清"谁在什么条件下强"，
并为后续的去平凡化实验建立参照与分层维度。
"""
import numpy as np
import pandas as pd
from scipy import stats

pd.set_option('display.width', 200)

META = ['file', 'ts_len', 'anomaly_len', 'num_anomaly', 'avg_anomaly_len',
        'anomaly_ratio', 'point_anomaly', 'seq_anomaly']

df = pd.read_csv('uni_vuspr.csv')
DET = [c for c in df.columns if c not in META]

# TSB-AD 的三分类（依 README 的算法分组）
STAT = ['Sub-IForest', 'IForest', 'Sub-LOF', 'LOF', 'POLY', 'MatrixProfile',
        'KShapeAD', 'SAND', 'Series2Graph', 'SR', 'Sub-PCA', 'Sub-HBOS',
        'Sub-OCSVM', 'Sub-MCD', 'Sub-KNN', 'KMeansAD']
NN = ['AutoEncoder', 'CNN', 'LSTMAD', 'TranAD', 'AnomalyTransformer',
      'OmniAnomaly', 'USAD', 'Donut', 'TimesNet', 'FITS']
FM = ['OFA', 'Lag-Llama', 'Chronos', 'TimesFM', 'MOMENT (ZS)', 'MOMENT (FT)']
FAMILY = {d: ('统计' if d in STAT else '神经网络' if d in NN else '基础模型') for d in DET}

print('=' * 78)
print('TSB-AD-U 逐序列 VUS-PR 矩阵画像')
print('=' * 78)
print(f'序列数 {len(df)}   检测器数 {len(DET)}   缺失值 {int(df[DET].isna().sum().sum())}')
print(f'分组: 统计 {len(STAT)} / 神经网络 {len(NN)} / 基础模型 {len(FM)}')

# ---------- 1. 总榜 ----------
mean_all = df[DET].mean().sort_values(ascending=False)
print('\n' + '-' * 78)
print('[1] 总榜（均值 VUS-PR）')
print('-' * 78)
for r, (d, v) in enumerate(mean_all.items(), 1):
    print(f'{r:>3}. {d:<22} {v:.4f}   [{FAMILY[d]}]')

print('\n分组均值:')
for fam in ['统计', '神经网络', '基础模型']:
    cols = [d for d in DET if FAMILY[d] == fam]
    print(f'  {fam:<6} {df[cols].mean().mean():.4f}   最好: {df[cols].mean().idxmax()} '
          f'({df[cols].mean().max():.4f})')

# ---------- 2. 点异常 vs 序列异常分层 ----------
pt = df[df.point_anomaly == 1]
sq = df[df.seq_anomaly == 1]
print('\n' + '-' * 78)
print(f'[2] 按异常类型分层  点异常 n={len(pt)}  序列异常 n={len(sq)}')
print('-' * 78)
lay = pd.DataFrame({
    '点异常': pt[DET].mean(),
    '序列异常': sq[DET].mean(),
})
lay['差值(点-序列)'] = lay['点异常'] - lay['序列异常']
lay['族'] = [FAMILY[d] for d in lay.index]
print(lay.sort_values('差值(点-序列)', ascending=False).round(4).to_string())

print('\n分组在两类异常上的均值:')
for fam in ['统计', '神经网络', '基础模型']:
    cols = [d for d in DET if FAMILY[d] == fam]
    print(f'  {fam:<6} 点异常 {pt[cols].mean().mean():.4f}   序列异常 {sq[cols].mean().mean():.4f}')

# ---------- 3. 检测器之间的相关结构 ----------
print('\n' + '-' * 78)
print('[3] 逐序列 Spearman 相关：谁和谁行为一致')
print('-' * 78)
rank_corr = df[DET].corr(method='spearman')

# 与 MOMENT(ZS) 最相关的（基础模型的行为邻居）
for anchor in ['MOMENT (ZS)', 'Chronos', 'Sub-PCA']:
    s = rank_corr[anchor].drop(anchor).sort_values(ascending=False)
    print(f'\n与 {anchor} 行为最接近的 6 个:')
    for d, v in s.head(6).items():
        print(f'    {d:<22} rho={v:.3f}  [{FAMILY[d]}]')

# 整体：族内 vs 族间平均相关
print('\n族内 / 族间平均 Spearman:')
for f1 in ['统计', '神经网络', '基础模型']:
    row = []
    for f2 in ['统计', '神经网络', '基础模型']:
        c1 = [d for d in DET if FAMILY[d] == f1]
        c2 = [d for d in DET if FAMILY[d] == f2]
        vals = [rank_corr.loc[a, b] for a in c1 for b in c2 if a != b]
        row.append(f'{np.mean(vals):.3f}')
    print(f'  {f1:<6} ' + '  '.join(f'{v:>6}' for v in row))
print(f'  {"":6} ' + '  '.join(f'{f:>6}' for f in ["统计", "神经", "基础"]))

# ---------- 4. 性能与序列属性的关系 ----------
print('\n' + '-' * 78)
print('[4] 性能与序列属性的 Spearman 相关（正=属性越大表现越好）')
print('-' * 78)
props = ['ts_len', 'anomaly_ratio', 'avg_anomaly_len', 'num_anomaly']
rows = []
for d in DET:
    rows.append({'检测器': d, '族': FAMILY[d],
                 **{p: stats.spearmanr(df[d], df[p]).statistic for p in props}})
pr = pd.DataFrame(rows).set_index('检测器')
print(pr.sort_values('avg_anomaly_len').round(3).to_string())

# ---------- 5. 关键：方差型基线的"影子" ----------
# anomaly_ratio 低 + 平均异常段短 => 点状；这类序列上高分方法值得警惕
print('\n' + '-' * 78)
print('[5] 逐序列冠军分布（谁在多少条序列上拿第一）')
print('-' * 78)
winner = df[DET].idxmax(axis=1)
wc = winner.value_counts()
for d, c in wc.items():
    print(f'  {d:<22} {c:>3} 条 ({100*c/len(df):.1f}%)  [{FAMILY[d]}]')
print(f'\n拿过第一的检测器数: {len(wc)}/{len(DET)}  '
      f'—— 没有单一方法主导，印证 TSB-AutoAD 的模型选择动机')

# 每条序列的最优分 vs 全局最优单模型
oracle = df[DET].max(axis=1).mean()
best_single = mean_all.iloc[0]
print(f'\n全局最优单模型 (Sub-PCA) 均值 : {best_single:.4f}')
print(f'逐序列 oracle 选择均值        : {oracle:.4f}')
print(f'模型选择的理论增益上限        : +{oracle - best_single:.4f} '
      f'({100*(oracle/best_single-1):.1f}%)')

df.to_pickle('step1_df.pkl')
pd.DataFrame({'family': pd.Series(FAMILY)}).to_csv('det_family.csv')
print('\n[已保存 step1_df.pkl / det_family.csv]')
