# 2026-09-15 论文初稿更新与实验交接

阅读入口：[main.pdf](../../icassp/main.pdf)，LaTeX 入口：[main.tex](../../icassp/main.tex)。

## 当前交付

- 4 页技术正文＋第 5 页参考文献，使用官方 spconf 与 IEEEbib，不改字号、边距压页。
- 摘要、引言、相关工作、定义、协议、设置、九模型结果、局限与训练展望已写入。
- Fig. 1：基底与 augmented probe 的条件评价流程。
- Fig. 2：全部九个 detector 的 CDU 点估计与 95% source-bootstrap 区间。
- Table 1：Raw VUS、source-macro Raw VUS、CDU、点估计排名、positive sources 与 CI。无 L_D/U_D 列；完整数据原封保留。

## 实验仍在运行

PID 67620，队列为 duplicate → noise → alpha=2。检查时 duplicate 完成 13/23 sources，stderr 为空；后两项由同一进程自动接续。本次未重复启动，也未运行新 detector。

~~~powershell
Get-Content protocol_fast_results\logs\fast_controls_20260915_155849.stdout.log -Tail 20 -Wait
~~~

中断后（确认原进程已退出）：

~~~powershell
python -u scripts\run_protocol_fast.py --controls duplicate noise alpha2 --resume --continue-on-error
~~~

九个主实验已完成。controls 尚未完成，正文明确标注待完成，没有填入假数字或使用旧 nested controls 代替。

## 数据与解释

权威汇总：[MAIN_RESULTS.csv](../evidence/fast_main/MAIN_RESULTS.csv)。
同目录有 PER_SERIES、PER_SOURCE、CACHE_RAW_LINK、RANK_ASSOCIATIONS 与 manifest。

九模型 CI 均包含零。Raw/CDU 排名相关性为 0.516667；同损失 detector-only utility/CDU 为 0.966667。两种 Raw aggregation 的排名相同。正文聚焦相对声明基底的条件评价，不把排名分歧当作条件评价独特增值的证据。CDU-guided training 仅作未来研究。

## 图表与参考来源

使用 [ICASSP 2027 官方 Paper Kit](https://cmsworkshops.com/ICASSP2027/papers/paper_kit.php) 的双栏与第五页要求。
阅读 [ICASSP 2025 SALMon 评测论文](https://arxiv.org/html/2409.07437v3) 的结构作为参考：先界定评价问题，再用概念图与紧凑比较表承载证据；不复制措辞，也不声称它获奖。
数据图采用点＋区间，保留全部负值与不确定性。

已补充 VUS、MOMENT、M2N2、TranAD、TimesNet、FITS、Anomaly Transformer 的出处。近邻论文 Kai-Chen Yang 的作者经 Crossref DOI 元数据核对，引用 2026-09-07 online pre-proof（后续卷期日期可不同）。

## 投稿前缺口

1. 作者、单位和联系信息待用户提供。
2. 三个 Fast controls 结果与解读待完成。
3. 第二 probe / basis sensitivity 尚无本协议结果，不写成做过。
4. 需要作者审核定位与叙事；当前引用清单不能替代所有相关文献全文审查。

## 更新与编译

~~~powershell
python scripts\render_paper_figures.py
powershell -NoProfile -ExecutionPolicy Bypass -File icassp\build.ps1
~~~

本轮只重新绘图和编译，没有更改实验协议、detector cache、CDU estimator 或旧 Stage 2 结果。
