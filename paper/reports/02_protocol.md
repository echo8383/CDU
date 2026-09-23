# 实验协议与实现：以当前代码为准

本报告对应 `CDU-protocol-fast-v1`，读取日期 2026-09-14。正式协议见 [docs/PROTOCOL.md](../../docs/PROTOCOL.md)。主执行代码为 [run_protocol_fast.py](../../scripts/run_protocol_fast.py)，共用计算函数来自 `evaluate_cdu_protocol_v1.py`；文件名带 v1 不代表 Fast 仍执行 inner CV。

## 1. 数据流与执行结构

```text
350-series frozen index + source_groups.json
  |
  +-- basis cache (T x 31) + labels (T)
  |     +-- one shared LOSO baseline -> L_null, L_basis
  |
  +-- detector cache (T) -> label-free average ranks
        +-- source LOSO, detector-only probe -> L_detector
        +-- same source LOSO, basis+score probe -> L_basis_detector
                |
                +-- per-series losses and CDU
                +-- per-source means
                +-- 23-source macro + paired source bootstrap
```

本轮训练的是 evaluation probe（评价探针），不重新训练 9 个 TSAD detector。每条 detector 分数缓存仅加载一次用于当前任务；Raw VUS 后处理也使用同一 detector instance。缓存名的序号来自原始 benchmark，可能大于 350；人口由 `uni_vuspr.csv` 的 350 个唯一 filename 定义，而不是编号 1 到 350。

## 2. 数据来源及 23 个分组

数据路径：`Datasets/TSB-AD-U/`；冻结索引：`uni_vuspr.csv`；分组：`source_groups.json`；basis 元数据：`protocol_v1_input_manifest.json`。运行 evaluator 时标签从 basis NPZ 的 `label` 字段读取，因此服务器不必携带原始 CSV。

| Source | 序列数 | Source | 序列数 | Source | 序列数 |
|---|---:|---|---:|---|---:|
| CATSv2 | 1 | Daphnet | 1 | Exathlon | 30 |
| IOPS | 15 | LTDB | 8 | MGAB | 8 |
| MITDB | 7 | MSL | 7 | NAB | 23 |
| NEK | 8 | OPPORTUNITY | 27 | Power | 1 |
| SED | 2 | SMAP | 17 | SMD | 33 |
| Stock | 8 | SVDB | 18 | SWaT | 1 |
| TAO | 2 | TODS | 13 | UCR | 70 |
| WSD | 20 | YAHOO | 30 | 总计 | 350 |

“Source”在这里是冻结映射中的 benchmark 来源组。它并不自动证明 23 个组统计独立，也不意味着检测器预训练语料从未包含相关数据。Source LOSO 防止相同来源的 sibling series 同时进入 probe 的训练和测试；它不能消除已缓存 detector 的预训练数据重叠。

## 3. 31 个统计基底的明确组成

以下名字和列顺序从 input manifest 核对。窗口统计的构造参照历史 `layer2_pilot.py` 和 `oneliners.py`，可从 archive tag 或本机 `_archive/` 取回；当前实验直接读取冻结表示，不重建 basis。

| Family | 参数 | 个数 | 历史生成逻辑 |
|---|---|---:|---|
| Var | 8,16,32,64,96,128,256 | 7 | 窗口总体方差，放在窗口中心 |
| Range | 同上 | 7 | 窗口 max-min，放在窗口中心 |
| Last | 1,2,3,8,16,32,64 | 7 | 前 w 点均值与下一点的平方差，放在目标点 |
| Centered | 3,16,64 | 3 | 同样的预测平方差，按既有定义放在窗口中心；不是重新定义为中心点重构误差 |
| AbsDiff | 1,4,16 | 3 | 相邻点绝对差；w>1 时对差分作长度 w 的均值卷积 |
| MAD | 32,128 | 2 | 窗口相对中位数的绝对偏差中位数 |
| SpecEnt | 64,256 | 2 | 去均值窗口的 FFT 能量分布熵，稀疏窗口后插值 |

历史 `_place` 逻辑按相应 offset 放回逐点数组，两端用最近已有值延拓。中心窗口、序列内 rank、频域窗口可能使用未来点，因此当前目标是 retrospective/offline evaluation（回顾性离线评价），不声称 streaming detection。

必须区分两种 transformation：

- **Detector**：当前代码明确采用 average ranks，\(s'_t=(\operatorname{rank}_{avg}(s_t)-0.5)/T\)，相同分数取平均名次，全常数序列映射到 0.5。不会使用标签来变换分数。
- **Basis**：当前程序直接读取缓存中的 31 列 float32，不再统一重新 rank。历史生成器包含 stable double-argsort 的 ordinal rank；不能在论文中笼统写成“basis 和 detector 所有 ties 都已 average-rank 修复”。缓存级 tie provenance、由稳定排序带来的潜在时间顺序编码，需要作为具体限制记录。若后续决定修改此表示，属于新的协议版本，不能静默并入当前运行。

历史 basis 构造还包括原序列 `dropna()`、全序列 z-score；这些不是当前运行再次执行的预处理。实际表示以缓存与其 hash 为准。Input manifest 记录 provenance 不等于每次 resume 都重新校验全部输入 hash。

## 4. 冻结的九个 detector

SubPCA、POLY、MOMENT_FT、MOMENT_ZS、M2N2、TranAD、TimesNet、FITS、AnomalyTransformer。通常缓存位于 `layer2_results/detector_scores/<name>/<series_id>.npy`；POLY 特例为 `layer2_results/poly_pinned_scores/`。

Fitting、training、fine-tuning 或 test-time adaptation 都属于先前 score 生成阶段。本论文应引用 detector configs/wrappers 和已有 Stage 2 provenance，并把 benchmark adapter 与原始论文模型区分开；本报告没有重做模型训练审计。ZS 与 FT 是两个独立缓存，不能合并。

AnomalyTransformer 的以下退化序列继续保留：`531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv`、`536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv`。它们的 score constant 行为有既有诊断依据。注意：“某一 held-out series 的 score 常数”不意味着全局训练出的 detector-only probe 在该 series 上必然等于 null prior；不能把局部 \(L_D=L_0\) 当作必然恒等式。

## 5. Outer LOSO 的实际过程

对每个来源 g：将全部属于 g 的序列作为 test，其余 22 个来源作为 train。在 train 上拟合 basis、detector、basis+detector 的对应探针；只在 test 上输出每条序列 loss。每条序列只出现一次 outer test。

Fast 主协议的 C 全局固定为 0.1，**不运行 inner grouped CV**。旧 nested v1 才使用 5-fold source-grouped inner CV 和 \(C\in\{0.01,0.1,1,10\}\)。固定 C 的选择已经作为运行策略冻结；不应在论文中声称未实际执行的嵌套调参，或声称事后制定的内容全部为预注册。

## 6. Probe 与样本权重

实际调用：

```python
LogisticRegression(C=0.1, penalty='l2', solver='liblinear',
                   class_weight=None, max_iter=300, random_state=2024)
```

默认 `fit_intercept=True`、`tol=1e-4`、`intercept_scaling=1`。liblinear 的 intercept 实现有其正则化行为，不应把它当作完全无惩罚的解析先验模型。Null 单独由训练标签的加权均值计算。

设 train 总点数为 N，来源数为 G，每个来源有 n_g 条序列，序列长度为 T_i。每点权重为：

\[
w_{it}=\frac{N}{G n_g T_i}.
\]

因此 source 等权，source 内 series 等权，series 内 timestamp 等权，且权重总和为 N。这一 N 倍缩放对正则化的有效强度有意义，不能在文字中只写“和为 1 的 sample weights”。不同 outer fold 的 N 可能不同；这是实际代码设置，应明确披露。

## 7. 四个 loss 和三个主要 utility

二元概率 loss（单位 bits）：

\[
\ell(y,p)=-y\log_2p-(1-y)\log_2(1-p),\qquad p\leftarrow\operatorname{clip}(p,10^{-7},1-10^{-7}).
\]

Null 概率使用 outer train 的上述加权 anomaly prevalence；不能用 held-out source 标签估计先验。Basis 输入 31 维；Detector 输入 1 维；Basis+Detector 输入 32 维。训练 target 始终是标签，标签不进入真实 detector 的特征构造。

每条序列先对时间点平均 loss，然后计算 \(U_B=L_0-L_B\)、\(U_D=L_0-L_D\)、\(U_{BD}=L_0-L_{BD}\)、\(\mathrm{CDU}=L_B-L_{BD}\)。共享 baseline 每来源只拟合一次并保存，之后所有 detector 按 `series_id` 复用相同 L0/LB。

计算量：共享 baseline 23 次 fit；每 detector 两个 probe × 23 source = 46 次 fit；9 detector 加 baseline 共 437 次 fit。三个完整 Fast controls 再加 138 次 fit。Null 不需要拟合分类器。控制组的计算与真实 detector 使用相同 `run_records` 路径。

## 8. 聚合与不确定性

每个来源：\(L_g=\frac1{n_g}\sum_i L_i\)；全局：\(L=\frac1{23}\sum_g L_g\)。这是 source-macro，不是将所有点混在一起的 micro-average，也不是直接对 350 条序列等权。

Paired source-cluster bootstrap：先保留每来源的配对差 \(\Delta_g=L_{B,g}-L_{BD,g}\)，在 23 个来源上有放回抽 23 个索引，重复 10,000 次，seed=2024。每次计算平均差；2.5% 和 97.5% 分位数形成 percentile CI。

`positive_source_fraction` 是 23 个 source 中 CDU>0 的比例；`bootstrap_prob_source_macro_positive` 是 10,000 次 bootstrap mean>0 的比例。后者不是 Bayesian posterior probability，也不是自动有效的显著性 p-value。CI 不通过时间点 bootstrap 构造，且不重新拟合模型；它不完整反映拟合方差、重叠训练折的依赖或 source 人口选择的不确定性。

## 9. Raw VUS 与论文主表

Raw VUS 保留原冻结 metric/window 的含义，应离线追溯到同一 score cache。主表应同时备有 350-series macro Raw VUS 和 23-source macro Raw VUS，以检查权重造成的 rank shift。后者需要已有 per-series VUS 与 source mapping join，不能直接由总体 Raw 均值推得。

本轮只建立写作与证据快照；还没有完成 9 个 Fast CDU 与 source-macro Raw VUS 的最终整合。旧 Stage 2 Raw 数字可以作有来源的参考，但不能把旧 CDU 插入 Fast 主表。

## 10. Controls 和执行保障

Duplicate 为 manifest 固定列 Var-96 的精确复制；noise 使用 version、series_id 和 control_name 的 hash 生成稳定噪声，再 rank；Fast synthetic control 固定 \(S=\operatorname{rank}(Z+2Y)\)。Synthetic 专门使用标签注入信息，所以必须标为 calibration，不是可部署 detector。只跑 alpha=2 一个点，不能据此宣称已经在 Fast 协议验证 dose-response；完整 alpha 曲线属于旧 nested 实验。

Negative controls 的近零表现用于解释探针敏感性。L2 正则化下复制特征会改变参数惩罚几何，因此 duplicate 不是必然精确为 0。不能拿 control 均值手工扣除 detector CDU。

现有 runner 按 source 原子保存 CSV/JSON；resume 检查版本字符串、数量、唯一 ID 数量和数值有限。它没有完整验证 checkpoint 的每个输入 hash，因此“任意更换代码/config 后均会拒绝续跑”不是现有实现能力。在运行期间固定代码、输入与结果目录；本轮队列只调用现有 runner，没有改变其统计定义。

`--continue-on-error` 的粒度是 detector/control 任务：某个 source 报错会结束当前任务，再尝试下一个任务；不是在同一 detector 内跳过该 source 而生成完整结果。恢复后可从已有 source checkpoint 继续。启动命令中的 `--resume` 保留兼容接口，当前 runner 实际总会检查已有 checkpoint。
