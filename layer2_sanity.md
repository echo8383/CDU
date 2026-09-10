# Layer 2 CDU 第一阶段审计

## 范围

本阶段只完成 350 条序列的 point-wise trivial basis 缓存，以及 CDU probe 的 synthetic/control 验证；尚未抓取或比较真实 detector 曲线。

缓存目录：`layer2_results/basis_scores/`，共 350 个 `.npz`；每个文件包含 `(T,31)` 的 rank-normalized basis、标签和 basis 名称。

## Probe 定义

使用 whole-series 5-fold OOF regularized logistic regression：`M0(Y|B)` 与 `M1(Y|B,S)`。训练阶段使用 `class_weight='balanced'`，评估阶段保留真实标签比例。每条序列先计算平均 bit log-loss 差，再对序列等权平均。输出 `CDU_bits = L0-L1` 与 `NCDU = CDU/L0`。

## 控制结果（20 条 pilot 序列）

| control | L0 (bits) | L1 (bits) | CDU (bits) | NCDU |
|---|---:|---:|---:|---:|
| Var96 self-copy | 0.873648 | 0.873714 | −0.000065 | −0.000067 |
| 100×Var96+7 | 0.873648 | 0.873714 | −0.000065 | −0.000067 |
| Random | 0.873648 | 0.873640 | +0.000008 | +0.000004 |
| AddedSignal λ=0 | 0.873648 | 0.873714 | −0.000065 | −0.000067 |
| AddedSignal λ=0.1 | 0.873648 | 0.441048 | +0.432600 | +0.492275 |
| AddedSignal λ=0.25 | 0.873648 | 0.236560 | +0.637088 | +0.726700 |
| AddedSignal λ=0.5 | 0.873648 | 0.148984 | +0.724664 | +0.827040 |
| AddedSignal λ=1 | 0.873648 | 0.103575 | +0.770073 | +0.878354 |

结论：self-copy、monotonic-copy、random 均接近 0；added signal CDU 严格单调上升。第一轮 control gate：PASS。

## Synthetic known-CMI

在已知生成模型中令标签依赖 `B + λZ`，把 `S=Z` 输入 M1。5-fold OOF CDU：

| λ | CDU (bits) |
|---:|---:|
| 0 | −0.000075 |
| 0.1 | +0.001445 |
| 0.25 | +0.009699 |
| 0.5 | +0.039242 |
| 1 | +0.134584 |

λ=0 近零，且随 λ 单调增加：PASS。

## 当前限制

1. 真实 detector 的 point-wise score curves 尚未生成，因此不能报告真实 detector CDU、置信区间、probe robustness 或 grouped CDU。
2. 当前实现缓存的 basis 为 rank-normalized `(T,31)`；raw robust-scaled robustness 尚未运行。
3. controls 使用 20 条序列以快速验证估计器；正式控制应在全量序列重复，并做 series-level bootstrap。
