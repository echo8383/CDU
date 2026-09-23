# CDU 主图重绘设计稿

## 一句话目标

让读者在十秒内理解：我们不重新训练九个 detector 来比谁分数高，而是在同一统计参考下，比较“有无 detector score”时对未见来源标签的预测损失，从而得到参考基底相对的增量效用。

主图应体现 TSAD 的任务结构，不只是两个 logistic 方块。增加的每个模块都应解释一个必要关系；不画没有运行的网络、训练闭环或虚构的信息分解。

## 建议版式：双栏通宽，三个主区域＋一条底部协议带

阅读方向从左到右，上部是一条独立的 accuracy 分支，中部是条件评价主路径，下部是共同的跨来源评估约束。

### A. Frozen TSAD outputs（冻结的 TSAD 输出）

最左侧画一条短时间序列，异常事件区域用浅灰背景标记，旁边注明 input illustration（输入示意），不要把手画曲线冒充真实实验。

从序列引出两个已经冻结的输出：

1. Declared statistical basis B：用小型多行曲线表示 31 个统计 scorer，旁注 variance / range / difference / entropy 等实际 family。
2. Detector score S_D：用一条独立曲线表示待评价 detector；下面标注 9 pinned detector instances。九个 detector 是被逐一评价，不要画成九模型集成。

另一条支路为 anomaly labels Y。标签不连入 score generation 或 rank normalization，只连到训练侧 probe 的监督端、测试侧 loss 计算端和 VUS 评价端。

加小字 Frozen scores / No detector retraining。不要在核心图里列文件名、hash、manifest、PID；这些是工程记录，不是核心方法。

### B. Two evaluation questions（两种评价问题）

上部窄支路：

S_D + Y → frozen VUS evaluator → Raw VUS

标题：How accurate is the anomaly ranking?（异常排序有多准确？）

中部宽主路径：

B → reference probe q_B → held-out L_B

B + S_D → augmented probe q_BD → held-out L_BD

标题：What does the score add beyond B?（给定 B 后新增了什么？）

两支 probe 用相同外框、相同大小，输入端只在第二支额外突出一列 S_D，旁注 Same probe family and fixed C。要表达唯一输入差异，不是第二支模型容量被宣称更高级。

在 score 到 probe 的接口旁放小框：label-free average-rank transform；明确它作用于 detector score。B 用 frozen cached preprocessing，不能把现有全部 basis 画成统一重新 average-rank 处理。

### C. Paired output（配对输出）

两个 loss 汇入差值模块：

CDU(D | B) = L_B − L_BD

差值模块下接：

source-wise Δ_g → source macro mean → paired source-bootstrap CI

顶部 Raw VUS 支路和 CDU 支路最终并排形成两张卡片：

- Standalone detection accuracy
- Basis-conditioned predictive utility

不要画“VUS 被 CDU 替代”的箭头，也不把近零 CDU 标为模型没有任何信息。

### 底部：Source-held-out protocol（跨来源协议）

用 23 个小 source 块表示一次 LOSO fold：22 个训练来源＋1 个留出来源，留出来源用边框强调。箭头标注 Rotate held-out source。

画清两条互不跨越的标签通道：

- Train-source labels → fit probes。
- Test-source labels → evaluate fixed probes only。

中间使用隔离线，文字 Test source excluded from fitting。当前主协议固定 C=0.1，没有 inner CV，不要把旧 nested-CV 画进主图。

底部放三个短标签：

Same timestamps · Same source weights · Same basis

层次汇总用小型三层图标表达 timestamp mean → series mean within source → equal source mean。不画 timestamp bootstrap。

## 是否加入 controls 和未来训练

Controls 可以放一个非常小的旁注：duplicate / independent noise / synthetic signal，标成 calibration inputs，连接现有评价入口；当前尚未验收时不能画 PASS 对勾。

不建议把 Stage 3 training 画进主图，会让读者误以为本文已验证训练方法。若一定展示，只能在最右侧独立虚线框写 Future direction: CDU-guided learning，并注明 not evaluated。四页版本优先省掉，留给正文展望。

## Fig. 2 与主图的分工

Fig. 1 解释“如何测”；Fig. 2 展示“测到什么”，不要重复放两张近似流程图。

新的 Fig. 2 为双面板：

- 左：横轴 series-macro Raw VUS，纵轴 source-macro CDU，全部九模型真实点估计；不 jitter 移点。
- 右：同九模型 CDU 的 95% source-bootstrap CI。

左图虚线分界为九模型中位数：Raw VUS=0.287047，CDU=0.000469 bits；这只是便于读图的相对分区，不是及格线、噪声地板或显著性界限。

M2N2 正好位于 Raw VUS 中位数竖线，AnomalyTransformer 位于 CDU 中位数横线，必须保留在边界，不人为移动制造象限归属。四象限若配文字，用 relatively higher/lower VUS/CDU，不能写有能力/没能力。九个区间都包含零。

真正的 rank change 用表和正文精确说明：M2N2 为 5→2，TranAD 为 6→3；散点图展示数值关系，不等同于排名图或显著差异检验。

## 视觉交付

- 白底，深蓝用于 B 和参考支路，暖橙用于新增 score；浅灰表示锁定或 held-out 边界。颜色必须配文字/线型。
- 少量分区标题、细线箭头；信息层级靠位置、对齐和分组，不靠渐变、3D 或大量图标。
- 正文阅读尺寸下，图中文字约 8–9 pt；不要为了塞模块降到不可读字号。
- 导出 vector PDF 或 SVG，字体嵌入；不要截屏后塞回 LaTeX。
- 主图建议高 1.8–2.1 英寸、双栏通宽。替换当前单栏占位主图后，需要重新平衡四页正文，不能直接叠加。

## 可直接给绘图者的英文说明

Design a publication-quality, two-column overview for conditional evaluation of frozen time-series anomaly scores. Show a declared 31-score statistical reference B, a single candidate detector score S_D from a nine-instance pool, and separate training/test label paths. Contrast a compact Raw VUS branch with the paired conditional branch: B → q_B → L_B and (B,S_D) → q_BD → L_BD, followed by CDU = L_B − L_BD. A bottom protocol band must show 23-source leave-one-source-out evaluation, identical test timestamps, fixed logistic probes, source-macro aggregation, and paired source-bootstrap uncertainty. Keep detector execution outside probe fitting. Do not depict inner CV, successful controls, a trained ensemble, or CDU-guided training as completed work. Use restrained vector graphics, readable labels, and explicit data-flow boundaries.
