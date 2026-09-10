# Conditional Detection Utility（CDU）实验报告

## 方法

在 TSB-AD-U 的 350 条评测序列上，先按 TSB-AD 约定对每条序列做整体 z-score。平凡基底由 31 条零参数滑窗统计量组成（Var、Range、Last、Centered、AbsDiff、MAD、SpecEnt）。所有比较在秩空间解释；主诊断定义 A 为检测器逐序列 VUS-PR 减去该序列基底最优 VUS-PR。

基底最优的同一数据选择会产生 best-of-31 向上偏差，因此同时报告未校正值和按连续时间块 5 折 held-out 选择基底后的校正值。定义 D（分层条件 AUC）与定义 E（受限 logistic 的嵌套增量）仅在存在逐点分数曲线时计算，不以标量成绩伪造。

## 数据核对

- 350/350 文件匹配；长度 min/median/max = 1000/18227/900000。
- 点异常 49 条，序列型异常 322 条；异常占比中位数 0.02154。
- 当前可聚合完整基底成绩：350/350；未完成行不进入 gap 均值。

## 结果（定义 A）

分族平均 A_gap_crossfit：{'基础模型': -0.0882, '神经网络': -0.1287, '统计': -0.0856}。

A_gap_crossfit 前五名：
- Sub-PCA：+0.0273
- KShapeAD：+0.0047
- POLY：-0.0063
- Series2Graph：-0.0080
- MOMENT (FT)：-0.0104

图 `results/cdu_scatter.png` 的右下区域表示原始 VUS-PR 较高但 CDU 较低的虚胖模型。完整数值见 `results/cdu.csv`、`results/rerank.csv` 与 `results/layered.csv`。

## 统计陷阱与限制

- VUS-PR 是排序面积，不能写成基底分与残差分的可加分解；残差 VUS-PR 只作反面教材。
- 低异常率带来 PR 地板效应，跨序列解读同时参考异常占比和相对基底提升。
- 所有嵌套拟合使用连续时间块，禁止随机打散。秩空间线性模型只表达单调依赖，非线性关系需另行等距回归消融。
- 当前仓库没有预存 32 个检测器逐点分数曲线；因此 D/E/C、阳性 λ 扫描与随机逐点 CDU 留为空值并在 `sanity.md` 标记，后续接入 TSB-AD 曲线即可复用同一分析脚本。
- 标量 VUS-PR 只能做按序列时间顺序的 held-out 聚合；严格的同一序列内时间块 cross-fit 需逐点曲线，不能从标量矩阵反推。