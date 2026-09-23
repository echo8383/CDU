"""Validate saved matched-probe results and export research tables without refitting."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from evaluate_cdu_protocol_v1 import DETECTORS, load_source_map
from run_symmetric_rank_controls import CONTROLS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/evidence/rank_probe_extension'


def bootstrap(v):
    b = v[np.random.default_rng(2024).integers(0, len(v), (10000, len(v)))].mean(axis=1)
    return np.quantile(b, [.025, .975]), (b > 0).mean()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = load_source_map()
    null = pd.read_csv(ROOT / 'protocol_fast_results/shared_baseline/PER_SERIES.csv').set_index('series_id').L_null
    results, basis, audits = [], [], []
    for probe in ['linear', 'spline', 'hgb']:
        folder = ROOT / 'protocol_rank_probe_results/cap2048' / probe
        assert json.loads((folder/'QUEUE_STATUS.json').read_text())['status'] == 'COMPLETE'
        baseline = pd.read_csv(folder/'baseline/PER_SERIES.csv').set_index('series_id').sort_index()
        assert set(baseline.index) == set(mapping)
        utility = (null.reindex(baseline.index)-baseline.L_basis).groupby(baseline.source_dataset).mean()
        ci, prob = bootstrap(utility.to_numpy())
        basis.append(dict(probe=probe, L_prior=null.groupby(pd.Series(mapping)).mean().mean(),
                          L_basis=baseline.groupby('source_dataset').L_basis.mean().mean(),
                          basis_utility=utility.mean(), CI_low=ci[0], CI_high=ci[1]))
        for task in [*CONTROLS, *DETECTORS]:
            f = pd.read_csv(folder/task/'PER_SERIES.csv').set_index('series_id').sort_index()
            assert len(f) == 350 and f.index.is_unique and set(f.index) == set(mapping)
            assert np.isfinite(f.select_dtypes(include='number')).all().all()
            np.testing.assert_array_equal(f.L_basis, baseline.L_basis)
            np.testing.assert_allclose(f.CDU, f.L_basis-f.L_basis_detector, atol=1e-14, rtol=0)
            assert (f.source_dataset == pd.Series(mapping).reindex(f.index)).all()
            v = f.groupby('source_dataset').CDU.mean().to_numpy()
            ci, prob = bootstrap(v)
            saved = pd.read_csv(folder/task/'SUMMARY.csv').iloc[0]
            np.testing.assert_allclose([saved.CDU,saved.CDU_CI_low,saved.CDU_CI_high], [v.mean(),*ci], atol=1e-14)
            results.append(dict(probe=probe, detector=task, CDU=v.mean(), CI_low=ci[0], CI_high=ci[1],
                                positive_sources=int((v>0).sum()), bootstrap_prob_macro_positive=prob,
                                CI_covers_zero=bool(ci[0]<=0<=ci[1]), source=str(folder/task/'PER_SERIES.csv')))
            audits.append(dict(probe=probe, condition=task, series=350, sources=len(v),
                               baseline_identical=True, formula_verified=True, summary_verified=True))
    all_results = pd.DataFrame(results)
    detectors = all_results[all_results.detector.isin(DETECTORS)]
    controls = all_results[all_results.detector.isin(CONTROLS)]
    ranks = detectors.pivot(index='detector', columns='probe', values='CDU').corr(method='spearman')
    for name, frame in [('DETECTORS',detectors),('CONTROLS',controls),('BASIS_UTILITY',pd.DataFrame(basis)),('AUDIT',pd.DataFrame(audits))]:
        frame.to_csv(OUT/f'{name}.csv',index=False)
    ranks.to_csv(OUT/'RANK_CORRELATION.csv')
    recon = pd.read_csv(ROOT/'paper/evidence/score_decomposition/DETECTOR_DECOMPOSITION_SUMMARY.csv')
    report = ['# 完成实验汇总：probe 依赖、统计可预测性与残差行为', '',
      '## 主要结果', '',
      '三种 probe 均完成 350 条序列、23-source LOSO。每条训练序列最多 2048 个无标签抽样点，三个 probe 的抽样完全一致，测试使用全部时间点。', '',
      'Spline 下 SubPCA、M2N2、POLY 的未校正 95% 来源 bootstrap 区间高于零；HGB 下 SubPCA、M2N2 高于零。Linear 下九个区间均含零。不能据此宣布所有 probe 等价，也不把观察到的最佳 probe 替换为预先指定的主结果。', '',
      '350 条序列的旧 basis cache 与重新平均秩变换后的数组逐元素完全相同（float32 最大绝对差为 0，2026-09-17 逐文件核查）。因此不能把这次结果解释为修复了绝对尺度不匹配。较早 symmetric-rank 与 legacy 运行的采样种子不同，其数值差异不是表示变换的证据；本报告三种 probe 使用同一采样种子。', '',
      '## 九模型 CDU（bits）', '', detectors.drop(columns='source').to_markdown(index=False,floatfmt='.7f'), '',
      '## 控制组', '', controls.drop(columns='source').to_markdown(index=False,floatfmt='.9g'), '',
      'Spline 的 duplicate/noise 区间覆盖零，positive control 区间高于零。Linear duplicate 存在微小负偏移，其 CI 不含零；HGB duplicate/noise 为约 -2.7e-17 的浮点量级负值，字面 CI 同样不含零。原数值完整保留：不能写成所有 controls 都满足严格零覆盖判据，也不能把浮点差异解释为实质信息。所有 probe 均未给这两个负对照分配显著正增量。', '',
      '## Probe 排名相关性', '', ranks.to_markdown(floatfmt='.4f'), '',
      '## 基底效用', '', pd.DataFrame(basis).to_markdown(index=False,floatfmt='.7f'), '',
      'Null loss 引用已完成 Fast 的全量加权训练先验，作为固定参考；当前 probe 采用抽样训练。此处并非为抽样训练重新拟合 null。', '',
      '## 分数重构与残差', '', recon[['detector','source_macro_R2','source_macro_Spearman','Raw_VUS','predicted_VUS_series_macro','residual_VUS_series_macro']].to_markdown(index=False,floatfmt='.6f'), '',
      '重构为 source-LOSO ridge 回归预测 detector 的 rank score。R²/Spearman 先逐序列计算再按 source 宏平均。AnomalyTransformer 两条常数序列的这两个指标未定义（348 个有限值），仍保留全部 350 条在损失和 VUS 中。', '',
      '残差是 rank(score) 减去预测值。该差值不等于条件独立残差，也不构成标签信息的正交或因果分解；其高分方向未必仍表示异常。VUS 不可加，因此 raw/predicted/residual VUS 只能作描述性对照，不能报告“解释了多少比例的 anomaly information”。', '',
      '## 文件与复核', '',
      'AUDIT.csv 检查了完整人口、基底 loss 完全一致、逐行 L_B-L_BD、来源映射及保存的 bootstrap 汇总。脚本不重跑任何 detector 或 probe。所有结果均来自 protocol_rank_probe_results/cap2048 与 protocol_score_decomposition/cap2048。', '']
    (OUT/'RESULTS_REPORT_ZH.md').write_text('\n'.join(report),encoding='utf-8')
    table = [r'\begin{table}[t]',r'\centering',r'\caption{Matched sampled-training sensitivity: CDU in bits. Bold entries have unadjusted source-bootstrap 95\% intervals above zero.}',r'\label{tab:probes}',r'\small',r'\setlength{\tabcolsep}{4pt}',r'\begin{tabular}{cccc}',r'\toprule',r'Detector & Linear & Spline & HGB \\',r'\midrule']
    for name in DETECTORS:
        cells = []
        for probe in ['linear','spline','hgb']:
            row = detectors[(detectors.detector==name)&(detectors.probe==probe)].iloc[0]
            value = f'{row.CDU:.5f}'
            cells.append(r'\textbf{'+value+'}' if row.CI_low>0 else value)
        table.append(name.replace('_','-')+' & '+' & '.join(cells)+r' \\')
    table.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}'])
    (ROOT/'icassp/tables/rank_probe_generated.tex').write_text('\n'.join(table)+'\n',encoding='utf-8')
    print(pd.DataFrame(basis).to_string(index=False))
    print('Validated 36 condition tables; report:',OUT/'RESULTS_REPORT_ZH.md')


if __name__ == '__main__':
    main()
