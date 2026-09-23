# 实验报告：已完成结果、待完成任务与证据边界

证据截止：2026-09-14 20:20 左右（Asia/Shanghai）。本报告是本机读取快照，不是三台机器的实时监控。数值快照和 SHA-256 位于 [paper/evidence/2026-09-14](../evidence/2026-09-14/)。

## 1. 当前结论

已建立 350-series × 9-detector 的 score 资产和历史审计，Fast source-LOSO shared baseline 已完成。本机 SubPCA 完成全部 23 来源，POLY 正在运行，MOMENT_FT 已在同一进程中排队。其他六个 detector 分配给协作者和 AutoDL；本机暂时没有它们的 Fast 汇总文件，不能据此判断远端未运行或失败。

最早的新协议结果已经说明：不能把旧实验的显著性直接搬进论文。SubPCA 新 CDU 为 0.0112224 bits，95% CI 跨 0，正增量只覆盖 12/23 source。basis-only utility 略负。这两点应保留在给指导者的材料中，而不是等全部实验完毕后再决定是否披露。

## 2. 三代协议应怎样区分

| 项目 | 历史 Stage 2 | nested v1 | 当前 Fast v1 |
|---|---|---|---|
| 外层单位 | 随机 whole series，5/10-fold | 23-source LOSO | 23-source LOSO |
| 主 probe | 历史 L2 logistic，balanced class weight | 无 class weight 的 logistic | 无 class weight 的 logistic |
| C | 历史固定设置 | train 内 grouped inner 5-fold 选择 | 所有条件固定 0.1 |
| Utility | 主要 Basis 与 Basis+score | 四个 loss | 四个 loss |
| 聚合 | series macro | source macro | source macro |
| Bootstrap | series-level | source-cluster | source-cluster |
| Detector rank ties | 旧路径存在 ordinal tie handling | average ranks | average ranks |
| 论文地位 | 历史动机／审计证据 | 历史诊断与协议比较 | 待完成的主实验 |

这几项同时改变，故不能把旧新 CDU 差额全部归因于 source leakage。若要隔离某一变化的贡献，需要单因素敏感性实验；当前不额外启动它。

## 3. 历史 Stage 2 正式审计表（不作 Fast 主表）

来源：`layer2_results/STAGE2_AUDITED_LEADERBOARD.csv`。以下是从文件读取的最新历史审计值，优先于聊天里的早期数值。

| Detector | Raw VUS | CDU 5-fold bits | CDU 10-fold bits | 历史状态 |
|---|---:|---:|---:|---|
| SubPCA | 0.4224126371 | 0.0599955633 | 0.0616257387 | PASS |
| POLY | 0.3892705891 | 0.0085033878 | 0.0084723910 | PASS |
| MOMENT_FT | 0.3864086329 | 0.0018936371 | 0.0014756143 | PASS |
| MOMENT_ZS | 0.3832290128 | 0.0003243254 | 0.0002452919 | PASS |
| M2N2 | 0.2870471522 | 0.0294041893 | 0.0295112542 | PASS |
| TranAD | 0.2754033860 | 0.0217128269 | 0.0220818171 | PASS |
| TimesNet | 0.2627459749 | -0.0002688658 | -0.0002017638 | PASS_WITH_NO_POSITIVE_INCREMENT |
| FITS | 0.2463691755 | 0.0006707968 | 0.0004828229 | PASS |
| AnomalyTransformer | 0.1117688782 | -0.0001995232 | -0.0001141956 | PASS_WITH_REPRODUCIBLE_COLLAPSE |

历史 M2N2/TranAD/TimesNet/FITS Raw 值已随正式 cache-only Raw VUS 审计更新，不能继续使用早期的 0.2875865/0.2764059/0.2518573/0.2363177。该修正发生在已有历史审计中，本次没有重新运行 detector 或重算 350 条 VUS。

历史 POLY 0.42252 与正式 0.3892705891 的差异应查旧 `POLY_RAW_VUS_DISCREPANCY_AUDIT.md`；本次只接受正式表作为历史结果，不从聊天重新推测 normalization/window 根因。相关文件可从 `archive/pre-paper-cleanup-2026-09-14` 恢复。

旧表中 POLY/MOMENT 的 Raw 接近而 CDU 不同，M2N2/TranAD 的 CDU rank 高于 Raw rank，是新实验的动机；它们是否在 Fast source-LOSO 下成立仍待全表。不能将其写成新协议已验证的 observation。

## 4. nested v1 正式 controls：完整结果与早期测试不能混淆

来源目录：`protocol_v1_results/controls/`；下面三行都有 350 series / 23 source 汇总。

| Control | CDU bits | source-cluster 95% CI | 正 source 数 | bootstrap macro>0 比例 |
|---|---:|---|---:|---:|
| exact_duplicate_Var-96 | -0.000003391268 | [-0.000009019325, 0.000000559652] | 8/23 | 0.0616 |
| independent_noise | 0.000005208100 | [0.000000156154, 0.000012315473] | 16/23 | 0.9801 |
| complementary_alpha_0p25 | 0.002233609508 | [0.001586302349, 0.002902354308] | 22/23 | 1.0000 |

Duplicate 的 CI 跨 0。Noise 的量级很小，但 CI 下界严格大于 0，因此不能声称它通过了“两个负控制 CI 均包含 0”的原始验收标准；更不能把 bootstrap 比例误称为 positive-series ratio。这个结果可能涉及有限样本、正则化、probe 选择或推断近似，但本次没有做因果定位。

alpha=0.25 显示加入已知标签信号可以获得正增量。然而本机只观察到这一 alpha 的完整 SUMMARY；其他 alpha 的协作者运行结果尚未在本次本地读取得到。不能从这一行宣称完整 monotonic dose-response 已核实。

这些 controls 属于有 inner CV 的旧协议。它们值得保留，并且不能证明固定 C 的 Fast controls 已经通过。Fast 三个 controls 的脚本已准备，执行对象是 duplicate、noise、alpha2；其中 alpha2 是校准点，不是新的 detector。

## 5. 当前 Fast baseline 与 SubPCA

Baseline 日志：`protocol_fast_results/logs/local_baseline.stdout.log`；完成 23/23，350/350，总耗时 01:17:24。汇总见 `shared_baseline/PER_SERIES.csv`。

SubPCA 完整结果来自 `protocol_fast_results/main/SubPCA/`。本次轻量检查确认：350 个唯一 series、有限 loss、与 shared baseline 的 L0/LB 一致、逐行 CDU=L_B-L_BD、source mean 与 SUMMARY 的宏均值一致。没有重拟合任何 probe，也没有把这项算术检查称为全量 provenance 重新审计。

| 字段 | 当前 Fast 数值 | 含义 |
|---|---:|---|
| L_null | 0.336955875353 | 来源等权的 null loss |
| L_basis | 0.337447370647 | 基底探针 loss |
| L_detector | 0.319341760274 | SubPCA-only probe loss |
| L_basis_detector | 0.326224970074 | basis+SubPCA loss |
| U_B | -0.000491495294 | basis 比训练先验略差 |
| U_D | 0.017614115079 | detector-only predictive utility |
| CDU | 0.011222400573 | basis 已知后加入 detector 的增量 |
| CDU 95% CI | [-0.003978205529, 0.029214034903] | 来源配对 bootstrap 区间 |
| positive_source_fraction | 0.521739130435 | 12/23 个来源增量为正 |
| bootstrap_prob_source_macro_positive | 0.9139 | 10,000 次 source bootstrap 均值>0 的比例 |

这里 L_detector 比 L_basis_detector 低，说明“加更多特征”在固定正则化及跨来源预测中不保证更好。CDU 是相对 L_basis 定义的，因此这与正 CDU 不矛盾。两者都是有限预测程序的结果，不是总体信息单调性定理的反例。

本次允许的表述：SubPCA 的 Fast CDU 点估计为正，但不能排除零或负的 source-macro 增量。不能借 0.9139 写出“91.39% 的概率真实 CMI>0”，也不能仅凭该值宣称统计显著。

## 6. 当前执行分工

| 机器 | 已分配的 detector | 本次可以确认的状态 |
|---|---|---|
| 本机 | SubPCA → POLY → MOMENT_FT | PID 53556；SubPCA 完成，快照时 POLY 11/23，MOMENT_FT 随后运行 |
| AutoDL | TranAD → TimesNet → FITS | 用户此前日志已证明缓存齐全并启动；本次没有远端实时读取 |
| 协作者 | AnomalyTransformer → MOMENT_ZS → M2N2 | 已有分工；本次没有远端实时读取 |
| 本机后续待确认 | Fast duplicate → noise → alpha2 | `scripts/queue_fast_controls.ps1` 已准备并 dry-run；尚未挂入自动队列 |

正在运行的实验不会因新增论文文件而改变。未经确认不把远端 detector 再排到本机，避免重复计算和结果目录冲突。

## 7. 什么完成后可以填论文主表

收齐九个同协议 detector 的 PER_SERIES、PER_SOURCE、SUMMARY；验证每个恰好 350 条、23 source，且 L0/LB 来自一致 baseline。不同机器各自拟合 baseline 时，应实际比较数值与版本，不能只凭都写着 C=0.1 就假定相同。

接着从现有 per-series VUS 生成 source-macro Raw VUS，与 \(U_D\)、CDU 一起汇总；最后重建 ranks、相关系数和图。Fast control 文件另列，记录微小非零和区间。不需要重新运行 detector。

在此之前，正式论文的八个未知行和相关系数全部留空。不能用旧表补齐；不能把未看到的远端输出当成 0；也不能只报告 SubPCA 这一行来代表九个 detector 的结论。

## 8. 证据路径与复核范围

`paper/evidence/2026-09-14/` 包括 `historical_stage2.csv`、`historical_nested_controls.csv`、`fast_completed.csv`、`source_composition.csv`、`run_status.csv` 和 `manifest.json`。manifest 记录这次读取的来源文件 SHA-256、git HEAD、Python/NumPy/pandas/SciPy/scikit-learn 版本和时间。

历史 controls 中的 CI 在本次只从文件读取；没有重算 bootstrap。Fast 完整行做了 loss 和聚合一致性检查，但没有重算全部模型或逐文件 score hashes。这种范围足以支持当前写作交接，不应标为一次新的 end-to-end audit PASS。
