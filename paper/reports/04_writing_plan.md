# ICASSP 论文框架、逐段任务与指导 prompt

## 1. 稿件定位

拟题：**Beyond Standalone Accuracy: Conditional Predictive Utility for Time-Series Anomaly Detectors**。

类型：评价方法与 benchmark 实证。主轴是声明参照表示之后的增量预测评价。不是新 TSAD 网络，不声称 CMI 恒等式原创，不恢复 Stage 3 ensemble，也不以“某模型优于某模型多少倍”为中心。

准备两个有证据约束的叙事方向：如果完整 Fast 结果显示稳定分离，讨论 standalone utility 与 conditional utility 的区别；如果区间宽或分离不稳，讨论依赖来源、探针和基底的评价及其不确定性。不以保持旧排名作为实验成功标准。

## 2. 官方格式与目录

当前 [ICASSP 2027 Paper Kit](https://cmsworkshops.com/ICASSP2027/papers/paper_kit.php) 给出：最多四页技术内容，可选第五页仅用于参考文献、资助说明和 ethical compliance statement；非双盲，最终须填作者。截止日期列为 2026-09-16。本次只准备格式和稿件，不执行投稿。

根目录 `icassp/` 是当前编辑入口：官方 spconf.sty、IEEEbib.bst、main.tex、math_commands.tex、references.bib、分段 sections 和 build.ps1。官方模板页面链接的示例头部仍写 ICASSP-2026；保存的是 2027 Paper Kit 当前链接的原始文件，未自行改官方样式。

`paper/` 是交接材料；旧 `paper/icassp2027/` 保留但不作当前稿件。这样指导者可以只读 Markdown，作者可以直接打开与截图类似的独立 LaTeX 目录。

## 3. 四页篇幅安排

| 内容 | 目标篇幅 | 必须完成的论证 |
|---|---:|---|
| Abstract + Introduction | 约 0.7 页 | 为什么独立精度无法回答 beyond-basis 问题 |
| Related work | 约 0.25 页 | 正面区别 conditional probing/V-information 与本文贡献 |
| Method + protocol | 约 1.1 页 | 理论量和估计量、四 loss、LOSO、权重、bootstrap |
| Setup + 主表 | 约 0.95 页 | 冻结人口、31 basis、9 cache、完整主结果 |
| Results discussion + diagnostics | 约 0.7 页 | matched metric/aggregation、controls、来源异质性 |
| Limitations + conclusion | 约 0.3 页 | 按证据约束解释 |

这些是写作预算，不是把尚未完成的实验压缩成结论。初稿可以少于四页；最终版再按表格和图形实际占用调整，不缩字体、挤页边距来补长度。

## 4. 按段落撰写的清单

### Abstract：一段，100–150 words

第 1–2 句提出 standalone performance 无法回答 beyond-basis contribution。第 3–4 句给出 conditional log-loss comparison、frozen statistical basis、source-held-out evaluation。第 5 句说清 estimator 是 probe-relative。最后 1–2 句必须由完整 Fast 主结果填入，不能先写排名逆转或显著性。当前 LaTeX 摘要明确标为 working draft。

### Introduction：四段

第一段：TSAD benchmark 已有统一评估，但单一性能坐标仍没有回答输出是否提供非重复的信息。用 TSB-AD 与 one-liner 工作作背景，不夸大成所有现代 detector 都等于统计基线。

第二段：用逻辑说明不同曲线不等于有用信息，独立性能相近不等于信息相同。提出 conditional predictive question；这里可以用一个文字例子，不构造未经实验支持的数字。

第三段：借鉴 conditional probing，给 basis 与 basis+score 两个 probe 的比较，并加入 detector-only utility 排除 metric-semantics 解释。明确评价的是输出，不对模型机制归因。

第四段：列三项可核实贡献：TSAD score 评价协议、来源分组的四-loss实现、九个冻结 detector 的完整实证。第三项只在实验收齐后写具体 findings。不要写“首次发现 CMI 与 log-loss 的联系”。

### Related Work：两段

第一段讨论 TSB-AD 和低复杂度 TSAD 基线；本研究在 benchmark score 之上问额外预测信息。第二段讨论 V-information、conditional probing、predictive variable importance；承认数学结构已有，将贡献限定在 TSAD 的 operational protocol 和实证。当前引用先覆盖这五个核心来源，九个 detector 原论文仍需逐条补齐；缺引用不能由 wrapper 文件代替。

### Method：五段

第一段定义 \(Y,B,S_D\) 和风险差，简要写出 Bayes log-loss 的 CMI 联系。第二段定义实际 cross-fitted estimator，强调 source transfer 与有限 probe 不等于精确 CMI。第三段给四个 loss 与三个 utility。第四段描述 source LOSO 和固定 C，无 inner CV。第五段写层次权重、source macro、配对 bootstrap、负值保留。

实现细节中 average-rank 修正只明确保证 detector branch；basis branch 是 frozen cached representation。该差别要在可复现材料中公开，不能写出不存在的统一 transformation。

### Setup：三段

第一段声明固定 350-series/23-source 子集并引用索引，不把 TSB-AD 全库缩写成只有 350 条。第二段给 31 basis families 与九个 detector/cache 定义，解释 two collapse series 保留。第三段冻结 probe/seed、四种 output、Raw VUS 两种 aggregation、controls。说明无新的 detector training。

### Results：四段，等待全表

第一段报告完整 9 个主结果以及来源区间；第二段比较 \(U_D\) 与 CDU；第三段检查 benchmark Raw 与 source-macro Raw 的 rank shifts；第四段报告 controls 与 source heterogeneity。所有 detector 全部保留，未显著的也保留；不能用近零分母倍数代替效应量。

当前只有 SubPCA 完整结果。结果稿中该行只能是“已完成的初步结果”，其 CI 跨 0 不支持显著正增量。当前旧 nested noise 的 CI 略正，须在诊断说明中明确；Fast controls 未完成不应写 through all controls。

### Limitations：两段

第一段：basis/probe/归一化依赖；source 数少且数量不均；source-cluster bootstrap 不包含重新拟合不确定性，fold 训练集合有重叠。第二段：offline score 的未来上下文、cache/provenance边界、预训练数据重叠未知、来源标签跨库定义差异。不要将局部 score 常数误认为全局 probe 必须输出训练先验。

### Conclusion：一段

第一句回到条件评价问题；第二句只填全实验支持的发现；最后一句说它是补充维度。尚无结果时不能写 “we demonstrate substantial ranking reversals under source-held-out evaluation”。

## 5. 三个论文对象

Figure 1：两个 probe 的输入和 held-out loss 比较。当前可先用 LaTeX 框图表达，后续与 Raw-VUS/CDU scatter 合并；散点只能从最终汇总生成。

Table 1：九 detector 的 Raw VUS、\(U_D\)、CDU、source CI、positive sources。内部完整表另存 source-macro Raw VUS、所有 ranks 和四个 losses；不必把所有字段硬挤入四页。

一个小 diagnostics 区域：Fast duplicate/noise/alpha2 的结果。若第二 probe 或 basis sensitivity 没完成，就不画对应空洞的 robustness 表，也不能在摘要称做了 robust evaluation across probes。

## 6. 发给论文指导者的 prompt

> 我们正在准备一篇 ICASSP 2027 的 TSAD evaluation paper。请先读 `paper/reports/01_research_brief.md`、`02_protocol.md`、`03_evidence.md`，再看 `icassp/sections/`。当前实证只将 Fast v1 作为主协议：350 个 frozen series、23-source LOSO、31 个 frozen statistical basis features、9 个 frozen detector caches、固定 C=0.1 的无 class-weight logistic probe，以及 source-macro log-loss 与 paired source bootstrap。
>
> 论文目标是在声明基底后评价 detector score 的 additional predictive utility，而不是提出新 detector 或精确 CMI estimator。请特别检查与 Hewitt et al. conditional probing 和 V-information 的关系，帮助判断 TSAD-specific protocol 与实证贡献是否充分。
>
> 请给出：四页论证结构、每段的中心论点、最需要的一张主表和图、哪些 claim 需要删除或降级，以及 reviewer 最可能攻击的三点。请不要根据旧 Stage 2 数字填新主表，不要假定 pending 实验成功。当前 SubPCA Fast CDU=0.0112224 bits，CI 跨 0；旧 nested noise 的 CI 略正，两者都必须正视。我们希望根据完整结果决定措辞，而不是倒推规则以维持原来的故事。

## 7. 实验继续时可以做的工作

现在可以定稿符号、方法描述、basis/score provenance 附表与相关工作；可以完成模板编译和作者信息准备。等结果收齐后，再填写结果段、图和 abstract 最后一句。所有实验目录保持现状，不因文稿编辑改 scorer、probe 或 source mapping。
