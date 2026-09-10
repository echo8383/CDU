"""Step 3: 去平凡化分析。

输入：
  uni_vuspr.csv              官方 350x32 逐序列 VUS-PR
  step2_oneliner_vuspr.csv   本地跑出的 350x31 one-liner 逐序列 VUS-PR

产出（定义 A：gap-excess，可在无分数曲线的情况下计算）：
  - 每个检测器的 excess-VUS-PR（相对 one-liner 基底逐序列最优）
  - 胜率：在多少条序列上真正超过基底
  - 按点/序列异常分层的 excess
  - 重排表：原始榜 vs 去平凡化榜
"""
import numpy as np
import pandas as pd
from scipy import stats

META = ['file', 'ts_len', 'anomaly_len', 'num_anomaly', 'avg_anomaly_len',
        'anomaly_ratio', 'point_anomaly', 'seq_anomaly']
STAT = ['Sub-IForest', 'IForest', 'Sub-LOF', 'LOF', 'POLY', 'MatrixProfile',
        'KShapeAD', 'SAND', 'Series2Graph', 'SR', 'Sub-PCA', 'Sub-HBOS',
        'Sub-OCSVM', 'Sub-MCD', 'Sub-KNN', 'KMeansAD']
NN = ['AutoEncoder', 'CNN', 'LSTMAD', 'TranAD', 'AnomalyTransformer',
      'OmniAnomaly', 'USAD', 'Donut', 'TimesNet', 'FITS']
FM = ['OFA', 'Lag-Llama', 'Chronos', 'TimesFM', 'MOMENT (ZS)', 'MOMENT (FT)']


def load():
    off = pd.read_csv('uni_vuspr.csv')
    olr = pd.read_csv('step2_oneliner_vuspr.csv')
    det = [c for c in off.columns if c not in META]
    olc = [c for c in olr.columns if c not in ('file', 'ts_len')]
    m = off.merge(olr[['file'] + olc], on='file', how='inner',
                  suffixes=('', '_ol'))
    return m, det, olc


def main():
    m, DET, OLC = load()
    fam = {d: ('统计' if d in STAT else '神经网络' if d in NN else '基础模型')
           for d in DET}
    print('=' * 80)
    print('去平凡化分析（定义 A：gap-excess，逐序列）')
    print('=' * 80)
    print(f'对齐序列数 {len(m)}   检测器 {len(DET)}   one-liner {len(OLC)}')

    # ---- one-liner 基底本身的成绩 ----
    ol_mean = m[OLC].mean().sort_values(ascending=False)
    print('\n--- one-liner 基底均值 VUS-PR（前10）---')
    for k, (n, v) in enumerate(ol_mean.head(10).items(), 1):
        print(f'{k:>3}. {n:<14} {v:.4f}')

    # 逐序列基底最优（这是每个检测器要打败的对手）
    base_best = m[OLC].max(axis=1)
    base_arg = m[OLC].idxmax(axis=1)
    print(f'\n逐序列基底最优 (oracle over one-liners) 均值: {base_best.mean():.4f}')
    print(f'基底中单条最强 ({ol_mean.index[0]}) 均值        : {ol_mean.iloc[0]:.4f}')
    print('\n基底 oracle 的构成（哪条 one-liner 最常胜出）:')
    for n, c in base_arg.value_counts().head(8).items():
        print(f'    {n:<14} {c:>3} 条 ({100*c/len(m):.1f}%)')

    # ---- 每个检测器的 excess ----
    rows = []
    for d in DET:
        raw = m[d]
        ex_single = raw - ol_mean.iloc[0]          # 相对基底最强单条（均值意义）
        ex_oracle = raw - base_best                # 相对逐序列基底 oracle
        win = (raw > base_best).mean()
        # 与基底最强单条的逐序列秩相关（同源性诊断）
        rho = stats.spearmanr(raw, m[ol_mean.index[0]]).statistic
        rho_or = stats.spearmanr(raw, base_best).statistic
        rows.append({
            '检测器': d, '族': fam[d],
            'raw': raw.mean(),
            'excess_vs_best_single': ex_single.mean(),
            'excess_vs_oracle': ex_oracle.mean(),
            '胜率_vs_oracle': win,
            'rho_vs_best_single': rho,
            'rho_vs_oracle': rho_or,
        })
    R = pd.DataFrame(rows).set_index('检测器')

    print('\n' + '-' * 80)
    print('[核心表] 按 excess_vs_oracle 降序')
    print('-' * 80)
    show = R.sort_values('excess_vs_oracle', ascending=False)
    print(show.round(4).to_string())

    # ---- 重排 ----
    print('\n' + '-' * 80)
    print('[重排] 原始榜 vs 去平凡化榜（名次变化）')
    print('-' * 80)
    r_raw = R['raw'].rank(ascending=False).astype(int)
    r_ex = R['excess_vs_oracle'].rank(ascending=False).astype(int)
    cmp = pd.DataFrame({'原始名次': r_raw, '去平凡化名次': r_ex,
                        '变化': r_raw - r_ex, '族': R['族'],
                        'raw': R['raw'].round(4),
                        'excess': R['excess_vs_oracle'].round(4)})
    print(cmp.sort_values('原始名次').to_string())

    print('\n名次上升最多（去平凡化后更显真本事）:')
    for d, r in cmp.sort_values('变化', ascending=False).head(5).iterrows():
        print(f'    {d:<22} {int(r["原始名次"]):>2} -> {int(r["去平凡化名次"]):>2} '
              f'(+{int(r["变化"])})  [{r["族"]}]')
    print('\n名次下降最多（原始分被平凡量撑着）:')
    for d, r in cmp.sort_values('变化').head(5).iterrows():
        print(f'    {d:<22} {int(r["原始名次"]):>2} -> {int(r["去平凡化名次"]):>2} '
              f'({int(r["变化"])})  [{r["族"]}]')

    # ---- 分层 ----
    print('\n' + '-' * 80)
    print('[分层] 点异常 vs 序列异常上的 excess_vs_oracle')
    print('-' * 80)
    pt = m[m.point_anomaly == 1]
    sq = m[m.seq_anomaly == 1]
    lay = []
    for d in DET:
        lay.append({
            '检测器': d, '族': fam[d],
            '点异常_excess': (pt[d] - pt[OLC].max(axis=1)).mean(),
            '序列异常_excess': (sq[d] - sq[OLC].max(axis=1)).mean(),
            '点异常_胜率': (pt[d] > pt[OLC].max(axis=1)).mean(),
            '序列异常_胜率': (sq[d] > sq[OLC].max(axis=1)).mean(),
        })
    L = pd.DataFrame(lay).set_index('检测器')
    print(L.sort_values('序列异常_excess', ascending=False).round(4).to_string())

    print('\n分族汇总（excess_vs_oracle 均值 / 胜率）:')
    for f in ['统计', '神经网络', '基础模型']:
        cols = [d for d in DET if fam[d] == f]
        e = R.loc[cols, 'excess_vs_oracle'].mean()
        w = R.loc[cols, '胜率_vs_oracle'].mean()
        rho = R.loc[cols, 'rho_vs_oracle'].mean()
        print(f'  {f:<6} excess {e:+.4f}   胜率 {w:.3f}   与基底oracle秩相关 {rho:.3f}')

    R.to_csv('step3_excess.csv')
    cmp.to_csv('step3_rerank.csv')
    L.to_csv('step3_layered.csv')
    m.to_csv('step3_merged.csv', index=False)
    print('\n[已保存 step3_excess.csv / step3_rerank.csv / step3_layered.csv / step3_merged.csv]')


if __name__ == '__main__':
    main()
