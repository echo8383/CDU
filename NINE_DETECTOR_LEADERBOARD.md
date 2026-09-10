# Nine-detector leaderboard

数据均来自当前 pinned score cache；未重新运行 detector。Raw VUS/CDU 不与历史 leaderboard 数值混用。

| Raw rank | CDU rank | Detector | Raw VUS | CDU 5-fold (bits) | CDU 10-fold (bits) | Family-Hard-20 VUS | Family-Hard-30 VUS | Audit status |
|---:|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 1 | SubPCA | 0.422413 | 0.059996 | 0.061626 | 0.292556 | 0.321397 | PASS |
| 2 | 4 | POLY | 0.389271 | 0.008503 | 0.008472 | 0.217679 | 0.255128 | PASS |
| 3 | 5 | MOMENT_FT | 0.386409 | 0.001894 | 0.001476 | 0.202058 | 0.226969 | CACHE_OFFLINE_COMPLETE |
| 4 | 7 | MOMENT_ZS | 0.383229 | 0.000324 | 0.000245 | 0.184291 | 0.213584 | CACHE_OFFLINE_COMPLETE |
| 5 | 2 | M2N2 | 0.287587 | 0.029404 | 0.029511 | 0.198821 | 0.199945 | PINNED_CACHE_COMPLETE |
| 6 | 3 | TranAD | 0.276406 | 0.021713 | 0.022082 | 0.203195 | 0.216291 | PINNED_CACHE_COMPLETE |
| 7 | 9 | TimesNet | 0.251857 | -0.000269 | -0.000202 | 0.172758 | 0.171170 | NOT AUDITED |
| 8 | 6 | FITS | 0.236318 | 0.000671 | 0.000483 | 0.150740 | 0.163002 | PINNED_CACHE_COMPLETE |
| 9 | 8 | AnomalyTransformer | 0.111769 | -0.000200 | -0.000114 | 0.111294 | 0.109358 | FAIL: 2 constant-score series |

## 解释

- Raw rank 与 CDU rank 分别按 350-series macro 均值降序排列。
- `positive_series_ratio` 是 5-fold 中 CDU_i > 0 的 series 比例；`bootstrap_prob_macro_positive` 是 bootstrap macro mean > 0 的比例，两者分开保存。
- AnomalyTransformer 的既有审计状态为 FAIL（两条常数 score 序列）；TimesNet 为既有 preliminary/consistency cache，未纳入严格三模型 audit PASS。
- FITS、M2N2、TranAD 是本轮 pinned cache complete；这表示 score/CDU 已生成，不等同于历史 leaderboard exact parity。
