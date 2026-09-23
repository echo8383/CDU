# 第二探针稳健性实验

训练点上限：2048/series。测试时间点全部保留。
固定 HGB：32 次 boosting，最多 7 个叶子，深度 3，学习率 0.1，最小叶节点 100，L2=1，31 bins。
不启用 early stopping，不使用随机时间点验证，不搜索超参数；23-source LOSO 与原来源宏平均、配对 Bootstrap 相同。

| Probe | Condition | Sources | Status |
|---|---|---:|---|
| logistic | duplicate_Var-96 | 23/23 | COMPLETE_VALIDATED |
| logistic | independent_noise | 23/23 | COMPLETE_VALIDATED |
| logistic | complementary_alpha_2 | 23/23 | COMPLETE_VALIDATED |
| logistic | SubPCA | 23/23 | COMPLETE_VALIDATED |
| logistic | POLY | 23/23 | COMPLETE_VALIDATED |
| logistic | MOMENT_FT | 23/23 | COMPLETE_VALIDATED |
| logistic | MOMENT_ZS | 23/23 | COMPLETE_VALIDATED |
| logistic | M2N2 | 23/23 | COMPLETE_VALIDATED |
| logistic | TranAD | 23/23 | COMPLETE_VALIDATED |
| logistic | TimesNet | 23/23 | COMPLETE_VALIDATED |
| logistic | FITS | 23/23 | COMPLETE_VALIDATED |
| logistic | AnomalyTransformer | 23/23 | COMPLETE_VALIDATED |
| hgb | duplicate_Var-96 | 23/23 | COMPLETE_VALIDATED |
| hgb | independent_noise | 23/23 | COMPLETE_VALIDATED |
| hgb | complementary_alpha_2 | 23/23 | COMPLETE_VALIDATED |
| hgb | SubPCA | 23/23 | COMPLETE_VALIDATED |
| hgb | POLY | 23/23 | COMPLETE_VALIDATED |
| hgb | MOMENT_FT | 23/23 | COMPLETE_VALIDATED |
| hgb | MOMENT_ZS | 23/23 | COMPLETE_VALIDATED |
| hgb | M2N2 | 23/23 | COMPLETE_VALIDATED |
| hgb | TranAD | 23/23 | COMPLETE_VALIDATED |
| hgb | TimesNet | 23/23 | COMPLETE_VALIDATED |
| hgb | FITS | 23/23 | COMPLETE_VALIDATED |
| hgb | AnomalyTransformer | 23/23 | COMPLETE_VALIDATED |

已完成数据见同目录 SUMMARY.csv 与 CONTROLS.csv；部分折结果不得作为完整总体估计。
若使用训练抽样，matched logistic 采用相同抽样和权重；不能将与全量主结果的差异仅归因于 probe。
控制检查未满足预期时必须报告，不调参数使其转为通过。
