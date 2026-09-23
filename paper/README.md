# CDU 论文讨论材料

这份材料面向第一次接触项目的导师、合作者和论文指导者。当前英文论文入口为 [../icassp/main.tex](../icassp/main.tex)，中文阅读版为 [../icassp/main_zh.tex](../icassp/main_zh.tex)。论文主线是衡量检测器分数在已声明统计参考之外新增多少标签预测效用；九检测器主实验和分数重构已完成。2026-09-23 新完成的六组参考/分数接口稳健性结果见 [REFERENCE_ROBUSTNESS_20260923.md](reports/REFERENCE_ROBUSTNESS_20260923.md)。

建议按以下顺序阅读：

1. [研究问题与贡献边界](reports/01_research_brief.md)：论文要回答什么、与已有工作的关系、哪些结论仍待验证。
2. [完整实验协议](reports/02_protocol.md)：数据、31 个 basis、四个 loss、LOSO、权重、bootstrap 和实现限制。
3. [实验结果与证据清单](reports/03_evidence.md)：已核实的旧结果、新结果、controls、运行状态和缺口。
4. [论文框架与逐段计划](reports/04_writing_plan.md)：四页安排、每段论点、证据要求及给指导者的 prompt。

论文正文按章节拆成 `../icassp/sections/*.tex`，已有完整的 Abstract、Introduction、Related Work、Method、Experimental Setup、Results 和 Discussion。主表和图由冻结证据生成；旧 Stage 2 与新 source-held-out 数字不混用。

`paper/icassp2027/` 是先前基于 IEEEtran 和 nested CV 的历史草稿，保留用于追溯，**不再是当前编译入口**。

`evidence/2026-09-14/` 保存本次阅读的轻量 CSV 和来源 SHA-256。它们是可分享的证据快照，不替代完整 score cache，也不代表重新审计了所有 detector。

刷新本机状态快照（不训练模型、不计算新的 CDU）：

```powershell
python scripts\snapshot_paper_evidence.py
```

刷新会更新当天 evidence 目录；报告文字需同时核对后修订，不能让旧文字自动成为新结果的解释。
