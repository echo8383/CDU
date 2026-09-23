# 研究说明：在声明的统计基底之外，异常分数还有多少预测效用？

日期：2026-09-14。性质：供论文指导的技术备忘录；不是最终实验结论。

## 1. 给第一次阅读者的概览

本项目研究时间序列异常检测（time-series anomaly detection，TSAD）的评价。我们已经缓存 9 个检测器在固定 350 条单变量序列上的逐点异常分数，并建立 31 维低复杂度统计基底。现在使用同一组异常标签，比较只读统计基底的预测探针与同时读取基底、检测器分数的探针，在严格留出的 source dataset 上谁的概率预测更好。

二者 held-out log-loss 的差值称为 conditional detection utility（CDU，条件检测效用）。它回答的是“给定这份基底与这类探针，检测器还能提供多少额外预测效用”。它不取代 Raw VUS，不等同于检测器本身的部署精度，也不解释网络内部机制。

当前最重要的事实是：本机已完成 Fast 协议的 SubPCA，其 CDU 为 0.0112224 bits，source-cluster 95% CI 为 [-0.0039782, 0.0292140]。因此现阶段不能说新协议已验证显著正增量，更不能先写出 9 个检测器的最终排名分离。其他结果仍在本机、协作者或 AutoDL 上运行／待同步。

## 2. 为什么需要第二条评价轴

Raw VUS-PR 描述一个异常分数与异常标签的对应质量。低复杂度统计分数可能已经捕捉到很大一部分异常结构，因此两个 Raw VUS 接近的检测器可能包含高度重复的信息，也可能各自提供不同的信息。Standalone performance（独立表现）本身无法区分这两种情形。

简单计算 detector 与 basis 的 score correlation 也不充分。相关性衡量分数曲线是否相似，不能回答它们的差异是否与异常标签有关。一条随机曲线可以非常不同，却没有预测用途。CDU 把“是否不同”换成“在已知基底后，差异是否改善 held-out 概率预测”。

研究问题固定为：

> Given a declared low-complexity statistical basis, how much additional label-relevant predictive utility is supplied by a detector score under a stated evaluation protocol?

这里的 declared（预先声明）是关键：CDU 是相对量。更换 basis、probe、来源人口或归一化都可能改变结果，不能把它写成 detector 的绝对固有能力。

## 3. 理论量、估计量与可允许的解释

Population target（总体目标）是 Bayes 风险差：

\[
\mathrm{CDU}^{*}(D\mid B)=\mathcal R^*(B)-\mathcal R^*(B,S_D).
\]

在同一联合分布上、使用二元 log-loss 并允许 Bayes-optimal predictor 时，它等于条件互信息 \(I(Y;S_D\mid B)\)。这是标准的信息论联系，不能包装成新发现。

实际程序运行固定的 L2 logistic probe，以 source-grouped cross-fitting 的留出 loss 计算：

\[
\widehat{\mathrm{CDU}}_{\mathcal Q}=\widehat L_B-\widehat L_{BD}.
\]

它是 probe-relative operational estimate（相对于探针的操作性估计）。正则化、有限样本、来源间分布变化、概率校准与表示尺度都影响它。尤其 LOSO 测量的是向未见来源的迁移预测效用，不能声称它无偏或精确估计混合分布上的 CMI。

允许的结论应贴近量本身：“在声明的 basis 和固定 probe 下，加入该 detector score 改善了／没有检测到改善 source-held-out label prediction。”如果区间跨 0，使用 “no detectable positive conditional utility under this protocol”。

不能从 CDU 推出 Transformer、预训练或某种网络组件造成了额外能力；不能由 CDU 近零推出原始 score 不含任何额外信息；不能将负数解释成负互信息。

## 4. 与最接近已有工作的关系

这不是从零发明“新增信息”的数学定义。必须在 related work 中明确讨论以下邻近工作：

- [Hewitt et al., Conditional probing, EMNLP 2021](https://arxiv.org/abs/2109.09234)：明确在基线信息上条件化，研究表示中的额外可用信息；与我们的结构非常接近。
- [Xu et al., A Theory of Usable Information, ICLR 2020](https://arxiv.org/abs/2002.10689)：解释信息可用性如何依赖观察者的预测函数族。
- [Williamson et al., JASA 2023](https://arxiv.org/abs/2004.03683)：以完整特征与去掉特征后的 oracle predictiveness 差定义变量重要性，并发展推断方法。本项目没有实现该文的全部统计推断程序，不能沿用其理论保证。
- [Liu and Paparrizos, TSB-AD, NeurIPS 2024](https://papers.nips.cc/paper_files/paper/2024/hash/c3f3c690b7a99fba16d0efd35cb83b2c-Abstract-Datasets_and_Benchmarks_Track.html)：提供本研究所依托的 benchmark 背景；本项目人口是已有冻结索引中的 350 条，不能把它称为该工作的全部 1,070 条数据。
- [Zhu et al., When Foundation Models are One-Liners, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/cf70320e93c08b39b1b29a348097a376-Abstract-Conference.html)：以低复杂度基线检验 TSAD 表现，构成本项目动机的一部分。我们的额外问题是 beyond-basis predictive utility，而非再次证明模型不如简单方法。

因此可争取的贡献是：将 conditional probing 组织成面向 TSAD score 的统一、可复用评价协议，并处理 source 分组、四个 matched losses、基底声明、score provenance 与不确定性；再用完整的 9-detector 结果展示该协议实际揭示了什么。不能先宣称新的 CMI estimator 或新的普适信息论指标。

## 5. 四个 loss 为什么重要

同时输出 Null、Basis、Detector、Basis+Detector 的 loss，可以把“metric semantics（指标语义）不同”的影响隔离出来：

| 量 | 定义 | 回答的问题 |
|---|---|---|
| Raw VUS-PR | 从 frozen detector score 得到的 range-aware 指标 | 检测器曲线本身的异常检测质量如何？ |
| \(U_D\) | \(L_0-L_D\) | 只给 probe detector score，能改善多少概率预测？ |
| \(U_B\) | \(L_0-L_B\) | 声明的统计基底在同一协议下有多少效用？ |
| CDU | \(L_B-L_{BD}\) | 基底已知后，score 再增加多少效用？ |

真正有说服力的比较应包括 \(U_D\) 与 CDU：二者使用相同 log-loss、相同来源权重与相同 split。单看 Raw VUS 与 CDU 排名不同，不足以排除 metric 或 aggregation 差异。

## 6. 给指导者的具体决策问题

首先请判断“TSAD 条件预测效用协议 + 来源分组实证”是否有足够的 ICASSP 定位，而不是把 CMI 恒等式当作贡献。其次请看 source-macro 结果及其区间是否支持 rank separation、只支持描述性双轴评价，或者主要揭示 domain transfer 的不稳定性。

当前 basis-only 的 source-macro utility 约为 -0.0004915 bits。这意味着固定线性探针对未见来源的基底预测略差于训练先验；不能将它描述为“基底已经解决大部分标签信息”。需要完整结果后讨论 domain heterogeneity 和 probe 限制。

最终建议只使用一个主故事。若统计证据强，写“相似独立表现对应不同的条件增量”；若区间宽，写“条件评价暴露了独立排名未呈现的效用与不确定性”；若探针依赖大，写“能力归因依赖声明的参照表示与预测函数族”。选择应由完整实验支持。
