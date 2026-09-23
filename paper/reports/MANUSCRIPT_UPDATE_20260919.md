# 论文更新记录：2026-09-19

## 当前版本

英文：`icassp/main.tex` → `icassp/main.pdf`。
中文阅读版：`icassp/main_zh.tex` → `icassp/main_zh.pdf`。
目标排版为四页正文、一页参考文献。作者与单位仍为待填写项。

本轮仅整合已完成结果，不重跑 detector、probe 或 bootstrap，不修改任何 score cache 或实验定义。

## 主张与两项问题

研究主线是给定声明统计基底后的新增标签预测效用。分数可预测性是辅助分析，两者不等价：

- `B → S_D`：预测目标是检测器分数，使用来源留出的 ridge 回归，以逐序列 R² / Spearman 后做来源宏平均。
- `B → Y` 与 `(B,S_D) → Y`：目标是异常标签，用相同时间点的留出对数损失差计算 CDU。

高分数可预测性不能证明没有新增标签信息；不可预测分数也不一定有效（可能是噪声）。CDU 不把 ridge 残差作为输入，不能把这两项画成必经的残差化流水线。

## 已纳入正文的新增证据

1. 匹配指标：同一 probe 下 detector-only utility `U_D=L0-LD` 与 CDU 的 Spearman 为 linear 0.9667、spline 0.6667、HGB 0.5000。表 2 纳入 spline U_D 和 spline/HGB CDU，所有数值均来自匹配训练抽样和全量测试。
2. 五种子：spline 九检测器排序完全一致；SubPCA、M2N2、POLY 的未校正区间五次均为正。这是抽样稳定性，不是独立数据集重复，也不证明与全量训练等价。
3. 七组基底族删除：固定原抽样和 probe，排名相关性 0.9167–1.0000。含完整基底共八种定义，SubPCA/POLY 正区间为 8/8，M2N2 为 7/8。移除 next-point deviation 会交换 SubPCA/M2N2 次序。
4. 来源影响：删除任意单一评价来源、但不重训时，spline SubPCA/POLY/M2N2/TranAD 的均值仍为正。
5. 多重比较：27 项共享来源 max-bootstrap 区间仅 spline POLY 为正；另一种探索性检验（来源 t-test + Holm27）无一在 0.05 拒绝，POLY p=0.0547。两种方法均保留，不择优汇报，且都不消除 LOSO 训练集重叠依赖。
6. 分数预测：MOMENT-ZS/FT 的来源宏平均 R² 为 0.904/0.799，M2N2/TranAD 为 0.054/-0.002。它解释的是分数可预测性，不是“解释了多少异常信息”。残差 VUS 保留在证据文件，不作为新的主张。

## 仍然明确保留的事实

- 图 2 / 表 1 是全量训练线性协议；其九个区间均含零。
- 新表 2 是抽样训练匹配分支，不替换旧协议，不追认 spline 为预注册主 probe。
- 原 Fast noise 有微小显著正估计；不能写成原协议所有验收条件均通过。
- 匹配 spline 负对照区间覆盖零；linear duplicate 有微小负偏移，HGB 负对照为浮点量级；不宣称全部满足字面零覆盖。
- 基底重新 rank 后逐元素不变，故不能声称修复了 detector/basis 绝对尺度不匹配。
- 不声称架构因果归因、精确 CMI 估计、改进检测器训练、普遍优于 VUS，或所有方法显著 beyond-basis。

## 数字来源

| 正文内容 | 文件（项目根目录相对路径） |
|---|---|
| 全量线性、Raw VUS | `paper/evidence/fast_main/MAIN_RESULTS.csv` |
| 匹配 probe CDU 与对照 | `paper/evidence/rank_probe_extension/DETECTORS.csv`、`CONTROLS.csv` |
| detector-only 与 CDU | `paper/evidence/cdu_followup/DETECTOR_ONLY_VS_CDU.csv`、`METRIC_RANK_CORRELATION.csv` |
| 五种子 | `paper/evidence/cdu_followup/SPLINE_FIVE_SEED_SUMMARY.csv`、`SPLINE_SEED_RANK_CORRELATION.csv` |
| 基底族消融 | `paper/evidence/cdu_followup/SPLINE_BASIS_COMPLETED.csv`、`protocol_followup_results/basis_spline_seed0_*/` |
| 多重比较与来源影响 | `paper/evidence/source_inference/MULTIPLICITY.csv`、`SOURCE_INFLUENCE.csv`、`METHODS_AND_RESULTS.md` |
| 分数回归 | `paper/evidence/score_decomposition/DETECTOR_DECOMPOSITION_SUMMARY.csv` |

## 编译

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File icassp/build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File icassp/build_zh.ps1
```

旧报告和生成表不删除；当前稿件引用 `matched_followup` 与 `matched_utility`，避免旧汇总脚本覆盖新叙述。

## 第二轮：按审稿风险重组（覆盖上述旧版图表布局说明）

当前结果文字改为 `sections/results_revised.tex` 及中文对应文件，统一表为 `tables/unified_results.tex`。旧文件保留，不参与编译。

- 引言从“定义一个量”改为明确 TSAD 的评价缺口、适配要求和使用场景；不主张新的信息恒等式。
- Table 1 汇总九个模型 Raw/来源宏平均 Raw、匹配 spline U_D，以及 full linear 与 matched linear/spline/HGB CDU。并列所有分支，不将 spline 追认为预注册主协议。
- Fig. 2 左侧是相同 spline/log-loss/source weighting 的 U_D 与 CDU，右侧是三个模型全部配对在三个 probe 下的区间。旧 VUS 散点和单独线性表保留在文件系统。
- Controls 保留真实数值和 noise 零覆盖偏差，去除项目内部“gate/验收”术语。不作 bias subtraction 或统一噪声阈值解释。
- 加入 AI 辅助使用披露。作者/单位、最终投稿元数据及披露准确性仍需作者核定。

### 新增的轻量离线统计

比较族在 `scripts/prepare_paper_revision.py` 中明确固定为 POLY/MOMENT-FT/MOMENT-ZS 的三个配对 × linear/spline/HGB，共九项。选择动机来自已观察的相近 Raw 表现，因此是探索性比较，不是事前独立验证。

每项输入是已保存的 23 来源 CDU 均值之差；20000 次共享来源 bootstrap，seed=2024，输出逐项 percentile CI 与联合九项 centered max-standardized interval。不重训，不重算 score/VUS，不隐藏未显著项。它不能消除重叠训练集及来源相关性。

| Spline 配对 | 平均差 bits | 未校正 95% CI | 九项联合区间 |
|---|---:|---|---|
| POLY − MOMENT-FT | 0.005050 | [0.001722, 0.008601] | [0.000361, 0.009739] |
| POLY − MOMENT-ZS | 0.005932 | [0.002411, 0.009608] | [0.001057, 0.010807] |
| MOMENT-FT − MOMENT-ZS | 0.000882 | [0.000216, 0.001553] | [-0.000010, 0.001774] |

Linear 与 HGB 的全部三个配对未校正区间均含零。因此结论是 spline 下观察到配对差异，而非与 probe 无关的普遍排序。

文件：`paper/evidence/paired_contrasts/PAIRED_CDU_CONTRASTS.csv`、`SOURCE_DELTAS.csv`、`METHOD.json`；后者记录输入 SHA-256、比较族、抽样与解释限制。
