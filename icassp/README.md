# ICASSP 2027 active manuscript

当前主线改为 benchmark blind spot：独立表现不能说明检测器在统计参考之外增加了什么。英文投稿入口为 `main.tex`，`main_zh.tex` 为中文阅读版；`scripts/prepare_submission_assets.py` 从冻结证据生成主表和图。九模型分数重构、normalization/reference-strength 稳健性实验均已完成，不重跑 detector，也不改变主结果。新增实验的完整数值和 min-max 敏感性见 `../paper/reports/REFERENCE_ROBUSTNESS_20260923.md`。

当前编辑入口为 `main.tex`。文件结构与一个独立会议模板一致：

```text
icassp/
  main.tex
  spconf.sty                  official style, unmodified
  IEEEbib.bst                 official bibliography style, unmodified
  math_commands.tex
  references.bib
  sections/                  section-by-section working prose
  template/official_example.tex
  build.ps1
  TEMPLATE_SOURCE.md
```

2026-09-19 更新：九个 detector 的全量 Fast 结果与三个对照均已完成；正文已加入匹配抽样 linear/spline/HGB、detector-only 效用、五种子 spline 稳定性、七组 spline 基底族消融、来源敏感性与多重比较检查，以及分数可预测性辅助分析。英文与中文阅读版均为 4 页技术正文＋第 5 页参考文献。作者与吉林大学联系邮箱已填写。完成不等同于所有诊断通过，正文保留原 Fast noise 偏差及探针/来源不确定性。

2026-09-20 根据逐句审阅意见更新：当前实际引用 sections/focused_abstract.tex、sections/focused_body.tex、sections/results_revised.tex 和 tables/primary_results.tex。中文使用同名 _zh 文件。旧 unified_results、matched_followup、focused_results、matched_utility 及编号章节已移入本机忽略的 `_archive/2026-09-23-icassp-legacy/`，不参与当前编译。英文主入口为 main.tex、PDF 为 main.pdf；中文入口为 main_zh.tex、PDF 为 main_zh.pdf。

Fig. 1 为记号一致的配对 CDU 协议图。Fig. 2 依次展示相同 log-loss 下的 $U_D$/CDU、统计参考对 detector score 的来源留出重构 $R^2$/CDU、三种探针排名；对应正文的三个主发现。Table 1 聚焦 spline 主结果，展示 VUS-PR、$U_D$、CDU、三种名次与来源级置信区间。完整 linear/HGB、对照和统计检验保留在 `../paper/reports/TECHNICAL_METHODS.md` 与原证据文件中。

当前图表生成命令为 `python scripts/prepare_submission_assets.py`：只排版已保存数字，不训练模型、不重新计算指标。旧 `prepare_paper_revision.py` 保留以追溯配对分析，不再作为当前版式的生成入口。审阅采纳记录见 `../paper/reports/REVIEW_ADOPTION_20260920.md`；此前证据索引见 `../paper/reports/MANUSCRIPT_UPDATE_20260919.md`。

Windows 编译：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File icassp\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File icassp\build_zh.ps1
```

Linux / Overleaf：选 main.tex 为主文件；本地命令：

```bash
cd icassp
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

最终 `main.pdf` 和 `main_zh.pdf` 纳入 Git，供克隆后直接阅读；LaTeX 中间文件仍被忽略。指导者建议先看 [paper/README.md](../paper/README.md)，尤其协议和证据报告。旧 `paper/icassp2027` 不再是当前草稿。
