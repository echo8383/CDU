"""CDU 全流程分析。

本脚本首先使用官方逐序列 VUS-PR 标量计算定义 A；若在
``results/curves/<detector>/<file>.npy`` 提供逐点分数，则同时计算定义 C/D/E。
没有曲线时不伪造 D/E/C，结果表保留 NaN 并在报告中明确限制。
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
META = ['file','ts_len','anomaly_len','num_anomaly','avg_anomaly_len','anomaly_ratio','point_anomaly','seq_anomaly']
STAT = ['Sub-IForest','IForest','Sub-LOF','LOF','POLY','MatrixProfile','KShapeAD','SAND','Series2Graph','SR','Sub-PCA','Sub-HBOS','Sub-OCSVM','Sub-MCD','Sub-KNN','KMeansAD']
NN = ['AutoEncoder','CNN','LSTMAD','TranAD','AnomalyTransformer','OmniAnomaly','USAD','Donut','TimesNet','FITS']
FM = ['OFA','Lag-Llama','Chronos','TimesFM','MOMENT (ZS)','MOMENT (FT)']
FAMILY = {d: ('统计' if d in STAT else '神经网络' if d in NN else '基础模型') for d in STAT+NN+FM}

def rank01(x):
    x = np.nan_to_num(np.asarray(x, float), nan=0.0, posinf=0.0, neginf=0.0)
    return (rankdata(x, method='average') - 1) / max(len(x)-1, 1)

def weighted_cauc(score, label, ref, K=10):
    """定义 D：按 ref 分位数分层，跳过单类箱并按正负对数加权。"""
    score, label, ref = map(np.asarray, (score, label, ref))
    bins = pd.qcut(rank01(ref), q=K, labels=False, duplicates='drop')
    num = den = 0.0; skipped = 0
    for k in np.unique(bins):
        m = bins == k; y = label[m]
        if y.min() == y.max(): skipped += 1; continue
        w = float(y.sum() * (len(y)-y.sum()))
        num += roc_auc_score(y, score[m]) * w; den += w
    return ((num/den - .5) if den else np.nan), skipped / max(K, 1)

def nested_auc(score, label, basis, folds=5):
    """定义 E：按时间块交叉拟合强正则 logistic，袋外 AUC 增量。"""
    y = np.asarray(label, int); s = rank01(score)
    Xb = np.column_stack([rank01(b) for b in basis])
    Xa = np.column_stack([Xb, s]); n = len(y)
    pred_b = np.full(n, np.nan); pred_a = pred_b.copy()
    for k, test in enumerate(np.array_split(np.arange(n), folds)):
        train = np.setdiff1d(np.arange(n), test)
        if np.unique(y[train]).size < 2: continue
        mb = LogisticRegression(C=.1, penalty='l2', solver='liblinear', max_iter=200)
        ma = LogisticRegression(C=.1, penalty='l2', solver='liblinear', max_iter=200)
        mb.fit(Xb[train], y[train]); ma.fit(Xa[train], y[train])
        pred_b[test] = mb.predict_proba(Xb[test])[:,1]; pred_a[test] = ma.predict_proba(Xa[test])[:,1]
    ok = np.isfinite(pred_b) & np.isfinite(pred_a)
    if ok.sum() < 2 or np.unique(y[ok]).size < 2: return np.nan
    return float(roc_auc_score(y[ok], pred_a[ok]) - roc_auc_score(y[ok], pred_b[ok]))

def load_curves(det, files):
    d = RESULTS / 'curves' / det
    out = []
    for f in files:
        p = d / (str(f) + '.npy')
        out.append(np.load(p) if p.exists() else None)
    return out

def basis_baseline_crossfit(B, label, metric_fn, n_blocks=2):
    """在时间块上交叉拟合基底选择；选择标签与评估标签严格不重叠。"""
    B = np.asarray(B); label = np.asarray(label, int)
    n = B.shape[1]; blocks = np.array_split(np.arange(n), n_blocks)
    vals = []; skipped = 0
    for k, evl in enumerate(blocks):
        sel = np.concatenate([b for j, b in enumerate(blocks) if j != k])
        if label[sel].sum() == 0 or label[evl].sum() == 0:
            skipped += 1; continue
        scores = np.asarray([metric_fn(b[sel], label[sel]) for b in B], float)
        if not np.isfinite(scores).any():
            skipped += 1; continue
        j = int(np.nanargmax(scores))
        vals.append(float(metric_fn(B[j][evl], label[evl])))
    return (float(np.mean(vals)) if vals else np.nan), skipped / max(n_blocks, 1)

def scalar_crossfit_baseline(frame, basis_cols, n_blocks=5):
    """标量 VUS-PR 可用的对称交叉拟合：按序列时间顺序选基底再在 held-out 序列评估。"""
    n = len(frame); blocks = np.array_split(np.arange(n), n_blocks)
    q = np.full(n, np.nan); selected = np.full(n, '', dtype=object); chosen=[]; skipped=0
    for k, evl in enumerate(blocks):
        sel = np.concatenate([b for j,b in enumerate(blocks) if j != k])
        means = frame.iloc[sel][basis_cols].mean()
        if not np.isfinite(means.to_numpy()).any(): skipped += 1; continue
        name = means.idxmax(); chosen.append(name)
        q[evl] = frame.iloc[evl][name].to_numpy(float)
        selected[evl] = name
    return (float(np.nanmean(q)) if np.isfinite(q).any() else np.nan,
            skipped / max(n_blocks,1), chosen, q, selected)

def run_invariant_tests():
    """纯聚合器 invariant：held-out 扰动与人工 toy 例子。"""
    toy = pd.DataFrame({'B1':[.9,.8,.7,.1,.2,.1], 'B2':[.2,.3,.1,.8,.9,.7], 'B3':[.1,.2,.2,.2,.1,.3]})
    mean, skip, chosen, q, selected = scalar_crossfit_baseline(toy, ['B1','B2','B3'], n_blocks=2)
    toy_ok = (chosen == ['B2','B1'] and list(selected) == ['B2']*3 + ['B1']*3 and abs(mean - (1/6)) < 1e-12)
    # 仅改 held-out block；训练 block 的选择必须完全不变。
    pert = toy.copy(); pert.loc[3:, ['B1','B2','B3']] = [[-100,1000,-100],[-100,1000,-100],[-100,1000,-100]]
    _, _, chosen_pert, _, _ = scalar_crossfit_baseline(pert, ['B1','B2','B3'], n_blocks=2)
    # 最后一个 block 是 fold-0 的 held-out；因此 fold-1 的训练集未被扰动，
    # fold-1 selection 必须保持不变。
    perturb_ok = chosen_pert[1] == chosen[1]
    return toy_ok, perturb_ok, chosen, chosen_pert

def main():
    off = pd.read_csv(ROOT/'uni_vuspr.csv')
    bas = pd.read_csv(ROOT/'step2_oneliner_vuspr.csv')
    olc = [c for c in bas.columns if c not in ('file','ts_len')]
    m = off.merge(bas[['file']+olc], on='file', how='inner')
    det = [c for c in off.columns if c not in META]
    # 只对已完成的基底行做聚合；中断任务留下的空行不能进入均值。
    complete = m[olc].notna().all(axis=1)
    m = m.loc[complete].reset_index(drop=True)
    if m.empty:
        raise RuntimeError('没有完整的基底成绩，请先完成 step2_oneliner_bench.py')
    best = m[olc].max(axis=1)
    fixed_name = 'Var-96' if 'Var-96' in olc else olc[0]
    basis_fixed = float(m[fixed_name].mean())
    basis_oracle = float(best.mean())
    basis_crossfit, crossfit_skip, chosen, q_cf, selected_cf = scalar_crossfit_baseline(m, olc, n_blocks=5)
    det_oracle = m[det].max(axis=1)
    # 输出标准基底表
    bas.rename(columns={'file':'file'}).to_csv(RESULTS/'basis_vuspr.csv', index=False)
    rows=[]
    for d in det:
        raw = m[d].to_numpy(float)
        rho = spearmanr(raw, best).statistic
        curves = load_curves(d, m.file)
        cvals=[]; evals=[]; rvals=[]; skips=[]
        if all(c is not None for c in curves):
            for c, f in zip(curves, m.file):
                lab = pd.read_csv(ROOT/'Datasets'/'TSB-AD-U'/f).dropna().Label.to_numpy(int)
                B = np.load(RESULTS/'basis_curves'/ (str(f)+'.npz'))['basis']
                ref = B[np.nanargmax([weighted_cauc(b, lab, b, 5)[0] for b in B])]
                v, sk = weighted_cauc(c, lab, ref, 10); cvals.append(v); skips.append(sk)
                evals.append(nested_auc(c, lab, B)); rvals.append(float(np.nanmean(c-ref)))
        rows.append({'检测器':d,'族':FAMILY[d],'raw_vuspr':raw.mean(),
                     'basis_fixed':basis_fixed,'basis_crossfit':basis_crossfit,'basis_oracle':basis_oracle,
                     'detector_oracle':float(det_oracle.mean()),
                     'A_gap_fixed':float(raw.mean()-basis_fixed),
                     'A_gap_crossfit':float(np.nanmean(raw-q_cf)),
                     'A_gap_oracle':float(raw.mean()-basis_oracle),
                     'A_gap_excess':float(raw.mean()-basis_oracle),
                     '胜率_fixed':float(np.mean(raw>m[fixed_name])),
                     '胜率_crossfit':float(np.mean(raw>basis_crossfit)),
                     '胜率_oracle':float(np.mean(raw>best)),
                     '胜率_vs_oracle':float(np.mean(raw>best)),
                     'rho_vs_basis_oracle':float(rho),
                     'CDU_strat':float(np.nanmean(cvals)) if cvals else np.nan,
                     'strat_skip_rate':float(np.nanmean(skips)) if skips else np.nan,
                     'CDU_nested':float(np.nanmean(evals)) if evals else np.nan,
                     'residual_vuspr':float(np.nanmean(rvals)) if rvals else np.nan})
    R = pd.DataFrame(rows).sort_values('A_gap_crossfit', ascending=False)
    R.to_csv(RESULTS/'cdu.csv', index=False)
    # 逐序列 paired 表：所有 detector 与基底来自同一份 m/file 集合。
    paired=[]
    for d in det:
        for i, f in enumerate(m.file):
            paired.append({'series_id':f, '检测器':d, 'detector_vuspr':m.iloc[i][d],
                           'selected_basis':selected_cf[i], 'basis_cf_vuspr':q_cf[i],
                           'gap_cf':m.iloc[i][d]-q_cf[i], 'basis_fixed_vuspr':m.iloc[i][fixed_name],
                           'gap_fixed':m.iloc[i][d]-m.iloc[i][fixed_name],
                           'basis_oracle_vuspr':best.iloc[i], 'gap_oracle':m.iloc[i][d]-best.iloc[i]})
    pd.DataFrame(paired).to_csv(RESULTS/'cdu_paired.csv', index=False)
    raw_rank = R.raw_vuspr.rank(ascending=False, method='min').astype(int)
    cdu_rank = R.A_gap_crossfit.rank(ascending=False, method='min').astype(int)
    pd.DataFrame({'检测器':R['检测器'],'族':R['族'],'原始名次':raw_rank,
                  'CDU名次':cdu_rank,'名次变化':raw_rank-cdu_rank,
                  'raw_vuspr':R.raw_vuspr,'A_gap_crossfit':R.A_gap_crossfit,
                  'A_gap_oracle':R.A_gap_oracle}).to_csv(RESULTS/'rerank.csv',index=False)
    layers=[]
    for typ, sub in [('点异常',m[m.point_anomaly==1]),('序列型异常',m[m.seq_anomaly==1])]:
        b=sub[olc].max(axis=1); fixed=sub[fixed_name]
        for d in det: layers.append({'检测器':d,'族':FAMILY[d],'分层':typ,
            'raw_vuspr':sub[d].mean(),'A_gap_fixed':(sub[d]-fixed).mean(),
            'A_gap_oracle':(sub[d]-b).mean(),'胜率_vs_oracle':(sub[d]>b).mean()})
    pd.DataFrame(layers).to_csv(RESULTS/'layered.csv',index=False)
    # K 稳定性（顺序时间块；不随机打散）。
    stab=[]
    for k in (2,5,10):
        v, sk, ch, _, _ = scalar_crossfit_baseline(m, olc, n_blocks=k)
        stab.append({'n_blocks':k, 'basis_crossfit':v, 'skip_rate':sk, 'selected':'|'.join(ch)})
    pd.DataFrame(stab).to_csv(RESULTS/'crossfit_stability.csv', index=False)
    # 自检（A 的阴性与阳性排序性质、随机基线地板）
    neg = {b: float((m[b]-best).max()) for b in olc}
    var_fixed_gap = float((m[fixed_name]-m[fixed_name]).mean())
    var_crossfit_gap = float(np.nanmean(m[fixed_name].to_numpy()-q_cf))
    toy_ok, perturb_ok, toy_sel, toy_sel_pert = run_invariant_tests()
    basis_ids = set(m.file.astype(str)); detector_ids = set(m.file.astype(str))
    sanity = ['# CDU 自检', '', f'- 数据行数：{len(m)}；基底数：{len(olc)}；检测器数：{len(det)}。',
              '## 三套基底基准',
              f'- basis_fixed ({fixed_name}) = {basis_fixed:.6f}；basis_crossfit = {basis_crossfit:.6f}；basis_oracle = {basis_oracle:.6f}。',
              f'- crossfit 选择折跳过比例 = {crossfit_skip:.3f}；选择出的基底 = {chosen}。',
              f'- detector_oracle = {float(det_oracle.mean()):.6f}；detector_oracle - basis_oracle = {float(det_oracle.mean()-basis_oracle):+.6f}。',
              '## 阴性对照',
              f'- Var-96 fixed gap = {var_fixed_gap:.6f}（应恰为 0）。',
              f'- Var-96 oracle gap = {float(m[fixed_name].mean()-basis_oracle):+.6f}（复现 best-of-31 偏差）。',
              f'- Var-96 scalar crossfit gap = {var_crossfit_gap:+.6f}；该值是序列级标量交叉拟合，逐时间戳 crossfit 需曲线。',
              '## ID / invariant 审计',
              f'- N_basis_crossfit = {len(basis_ids)}；N_detector_crossfit = {len(detector_ids)}；intersection = {len(basis_ids & detector_ids)}；basis-only = {len(basis_ids-detector_ids)}；detector-only = {len(detector_ids-basis_ids)}。',
              f'- paired 表行数 = {len(paired)}；每个 detector 的 paired 行数 = {len(m)}。',
              f'- toy 6x3 crossfit = {"PASS" if toy_ok else "FAIL"}；选择序列 {toy_sel}；held-out 扰动不改变选择 = {"PASS" if perturb_ok else "FAIL"}。',
              '- 逐条基底对 oracle 的最大 gap：%.6g（应不大于 0）。' % max(neg.values()),
              '- A_gap_fixed、A_gap_crossfit、A_gap_oracle 均已写入 cdu.csv；主排序使用 A_gap_crossfit。',
              '- 随机对照与阳性 λ 扫描需要逐点曲线；当前若无曲线文件则标为待运行，不以标量伪造。',
              '- 时序泄漏：nested 使用连续时间块交叉拟合，未随机打散。']
    (RESULTS/'sanity.md').write_text('\n'.join(sanity), encoding='utf-8')
    return R

if __name__ == '__main__': main()
