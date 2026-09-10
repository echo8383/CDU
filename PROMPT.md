# 任务：实现 Conditional Detection Utility (CDU) —— TSAD 去平凡化评估框架

你是一个研究工程助手。请在本仓库中实现下述实验，产出可直接进论文的表与图。
**代码用英文标识符，注释与最终报告用中文。** 每完成一个阶段就自检并汇报，不要一次写完全部再跑。

---

## 0. 一句话目标

现行 TSAD 评估无法区分「模型真的学到了复杂异常结构」与「模型其实只是在算滑窗方差」。
我们要构建一个度量：**在已知一组零参数平凡统计量的前提下，某检测器还额外提供了多少异常排序信息。**

已有的负面结果作为动机（不需要你复现，仅供理解）：ICLR 2026 "When Foundation Models Are
One-Liners" 发现 MOMENT / Chronos / TimesFM / Time-MoE / TSPulse 的零样本异常分与零参数
one-liner 的逐序列相关系数达 0.86–0.99，Cohen's d 近零；机理是窗口内 z-normalization 使
重构分退化为窗口方差的代理，而单步预测使异常进入上下文后「不再意外」。

---

## 1. 数据

**主数据集 TSB-AD-U**（350 条单变量评测序列）：

- 下载：`https://www.thedatum.org/datasets/TSB-AD-U.zip`（约 73 MB，解压得 `TSB-AD-U/`，含 870 个 CSV）
- 评测子集的文件名清单 + 官方逐序列成绩：仓库内 `uni_vuspr.csv`（350 行 × 40 列）
  - `file` 列即需要用的 350 个 CSV 文件名（其余 520 个是 tuning split，**不要用**）
  - 32 个检测器列：`Sub-IForest, IForest, Sub-LOF, LOF, POLY, MatrixProfile, KShapeAD, SAND,
    Series2Graph, SR, Sub-PCA, Sub-HBOS, Sub-OCSVM, Sub-MCD, Sub-KNN, KMeansAD, AutoEncoder,
    CNN, LSTMAD, TranAD, AnomalyTransformer, OmniAnomaly, USAD, Donut, TimesNet, FITS, OFA,
    Lag-Llama, Chronos, TimesFM, MOMENT (ZS), MOMENT (FT)`
  - 元信息列：`ts_len, anomaly_len, num_anomaly, avg_anomaly_len, anomaly_ratio,
    point_anomaly, seq_anomaly`
- CSV 格式：第一列是数值通道，最后一列名为 `Label`（0/1）。读入后 `.dropna()`。
- **预处理约定**：按 TSB-AD 默认对整条序列做 z-score 归一化。

**已核实的数据事实**（用于自检，若你算出的与此矛盾说明读错了数据）：

| 项 | 值 |
|---|---|
| 评测序列数 | 350，与 `uni_vuspr.csv` 的 `file` 列完全匹配，无缺失 |
| 序列长度 | min 1000 / median 18227 / max 900000 |
| 异常占比 | median 0.0215 |
| 点异常序列 / 序列型异常 | 49 / 322 |
| 官方均值 VUS-PR 榜首 | Sub-PCA 0.4234，次席 KShapeAD 0.4008 |
| 官方榜末 | AnomalyTransformer 0.1195 |
| 分族均值 | 统计 0.3105 / 神经网络 0.2674 / 基础模型 0.3079 |
| 逐序列 oracle 选择均值 | 0.7944（即模型选择的理论上限比最优单模型高 87.6%） |

**重要限制**：`uni_vuspr.csv` 只有标量分数，**没有 32 个检测器的分数曲线** $s(t)$。
定义 A 只需标量即可算；定义 C/D 需要曲线。曲线获取方式见 §6。

---

## 2. 平凡基底 B

仓库内 `oneliners.py` 已实现并验证，共 31 条曲线，直接用 `build_basis(x)`。
严格按 ICLR 2026 的定义：

- `Var-w`：`score[i + floor(w/2)] = Var(T[i : i+w])`，w ∈ {8,16,32,64,96,128,256}
- `Last-w`：`score[i + w] = (mean(T[i : i+w]) - x[i+w])^2`，w ∈ {1,2,3,8,16,32,64}
- `Centered-w`：同 Last 但分数置于窗口中心，w ∈ {3,16,64}
- `Range-w`：滑窗极差，w 同 Var
- `AbsDiff-w`（w ∈ {1,4,16}）、`MAD-w`（{32,128}）、`SpecEnt-w`（{64,256}）

分组标签用于消融：`recon`（Var/Range，对应重构型塌陷）、`pred`（Last/Centered，对应预测型
塌陷）、`other`。所有函数返回与输入等长的一维数组，越大越异常，无 NaN/Inf。

---

## 3. 度量定义（核心，按重要性排序）

记 $y$ 为标签，$s$ 为待测检测器分数曲线，$B = \{b_1..b_m\}$ 为基底，
$D(\cdot)$ 为检测质量泛函（用官方 VUS-PR）。**全部在秩空间工作**：
理由是 VUS-PR 对 $s$ 的任何严格单调变换完全不变，故秩空间不是近似而是精确；
任何非秩不变的操作都在测量 VUS-PR 看不见的东西。

### 定义 D（主指标 1）：分层条件效用 CDU-stratified —— 不拟合任何模型

1. 取基底最优组合的分数 $\hat s$（见下方「基底组合」）。
2. 按 $\hat s$ 的分位数把所有时间戳分入 $K$ 个箱（建议 $K \in \{5,10,20\}$，报告敏感性）。
3. 在**每个箱内部**计算 $s$ 对异常/正常的 Mann-Whitney U 统计量（等价箱内 AUC）。
4. 按箱内正负样本对数加权合并，得到条件 AUC $\mathrm{cAUC}(s \mid \hat s)$。
5. $\mathrm{CDU}_{\text{strat}} = \mathrm{cAUC}(s \mid \hat s) - 0.5$。

语义：**在平凡基底认为同等可疑的点里，$s$ 还能不能把真异常排在正常之上。**
这是流行病学意义上标准的「控制 B」。优点是零拟合、无过拟合风险、可解释。
注意箱内可能没有正样本或没有负样本，这些箱必须跳过并记录跳过比例。

### 定义 E（主指标 2）：嵌套增量效用 CDU-nested

拟合两个嵌套排序器并比较：

- $M_B$：用 $B$ 的秩作特征预测 $y$
- $M_{B \cup \{s\}}$：特征加入 $s$ 的秩

$\mathrm{CDU}_{\text{nest}} = D(M_{B \cup \{s\}}) - D(M_B)$

**必须交叉拟合**（按时间分块的 K-fold，禁止随机打散，避免时序泄漏），用袋外预测算 $D$。
排序器要**受限**（带强正则的 logistic，或单参数单调混合），否则容量本身会制造虚假增量。
优点：基底项留在模型里，因此**不惩罚「与基底一致」**——这是它相对定义 C 的关键优势。

### 定义 A（诊断/消融）：gap-excess

$$E_A = D(s) - \max_{b \in B} D(b)$$

只需标量分数，可在无曲线时算。**但有向上有偏的陷阱，见 §4。**

### 定义 C（仅作反面教材，不要当主指标）：残差 VUS-PR

$r = s - \hat s$，报 $D(r)$。
**必须在报告中明确指出它的缺陷**：$r$ 在基底高估处为负；更严重的是，若某真异常点同时被
$s$ 与 $\hat s$ 正确打高分，则该处 $r \approx 0$，于是 $D(r)$ **因为模型在真异常上与基底
一致而惩罚它**。请实现它并用实验展示这个失效（这本身是论文的一个论点）。

### 基底组合 $\hat s$ 的两种取法

- **单条最优**：$\arg\max_b D(b)$
- **凸组合**：在秩空间搜 $\hat s = \sum_j w_j \cdot \mathrm{rank}(b_j)$，$w \in \Delta^{m-1}$
  （Dirichlet 随机搜索 + 顶点，或用交叉拟合的受限回归）

凸组合是更强的对手：一个检测器若连基底的凸组合都赢不过，说明它几乎没有超出平凡统计量的信息。

---

## 4. 必须处理的统计陷阱（每一条都要在代码里显式处理并在报告中说明）

**陷阱 1：基底选择的向上偏差。**
$\max_{b \in B} D(b)$ 是在同一份数据上对 $m=31$ 个带噪估计取最大值，因此**向上有偏**，
导致 $E_A$ 系统性**低估**模型的真实增量。这与 best-of-$N$ 选种子刷分是同一个统计机制。
**修法**：把基底选择也交叉拟合——在held-out部分挑最优基底，在另一部分评估；
或报告偏差校正版本。请同时给出未校正与校正后的数值，展示偏差幅度。

**陷阱 2：VUS-PR 不可加。**
$D(s) \ne D(\hat s) + D(r)$，一般情况完全不成立，因为 PR 曲线经由排序—扫阈值—求面积得到。
不要在任何地方假设方差分解式的可加性。

**陷阱 3：PR 的地板效应。**
随机分的 VUS-PR 被异常占比托底（我实测：3.3% 异常占比下随机分得 0.0535）。
因此绝对值不可跨序列直接平均比较，报告时需同时给出相对基线的提升。

**陷阱 4：秩空间下的线性拟合只能捕捉单调关系。**
若 $s$ 与某 $b_j$ 是非线性单调关系，OLS 的 $R^2$ 会低估依赖强度。
考虑用等距回归（isotonic）或非参数方式拟合，并在消融中比较 OLS vs isotonic 的差异。

**陷阱 5：时序泄漏。**
任何交叉拟合都必须按时间分块，不得随机打散。

---

## 5. 自检清单（阴性/阳性对照，这是最重要的部分）

**任何一条不通过就说明实现有错，必须先修再往下做。**

1. **阴性对照（关键）**：把基底中的某条曲线（如 `Var-96`）本身当作「待测检测器」输入。
   所有 CDU 指标必须 ≈ 0（定义 A 精确为 0 或负）。若显著为正，说明有泄漏或偏差未处理。
2. **阳性对照**：构造 $s = \mathrm{rank}(\text{Var-96}) + \lambda \cdot \mathbb{1}[\text{真异常}]$，
   $\lambda$ 从 0 扫到 1。CDU 必须随 $\lambda$ 单调上升，且 $\lambda=0$ 时为 0。
3. **随机对照**：纯随机分的 CDU 必须 ≈ 0，且其 VUS-PR ≈ 异常占比。
4. **族区分度（决定论文成败）**：ICLR 那篇的关键细节是——非 TSFM 检测器与 one-liner 基线
   的相关性**低**，正是这一点证明「塌陷是 TSFM 特有的，而非基线本身强」。
   因此你的 CDU 必须保留可见的族间差距：Sub-PCA / KShapeAD / Series2Graph 这类应当**仍保有
   可观的正 CDU**（阴性对照组），而 MOMENT / Chronos 应当掉得明显（阳性对照组）。
   **若所有方法的 CDU 都被打成零，是度量坏了，不是所有方法都平凡。** 这条必须显式检验。
5. **基底量级**：单独跑基底，`Var-96` 的均值 VUS-PR 应在 0.4 量级，`Last-3` 在 0.2–0.3 量级
   （ICLR 报 0.42 / 0.28；我在 12 条子集上得 Var-96 = 0.51、Last-3 = 0.17，全量应更接近前者）。

---

## 6. 获取 32 个检测器的分数曲线（定义 C/D/E 需要）

`uni_vuspr.csv` 只有标量。要曲线需自己跑 TSB-AD：

```bash
pip install TSB-AD          # 或 git clone https://github.com/TheDatumOrg/TSB-AD 后 pip install -e .
```

```python
from TSB_AD.model_wrapper import run_Unsupervise_AD
from TSB_AD.evaluation.metrics import get_metrics
output = run_Unsupervise_AD('IForest', data)   # 返回逐点分数数组
```

检测器分两池：`Unsupervise_AD_Pool` 与 `Semisupervise_AD_Pool`（后者需在无异常前缀上 fit），
见 `TSB_AD/model_wrapper.py`；超参用 `TSB_AD/HP_list.py` 的 `Optimal_Uni_algo_HP_dict`。
**优先级**：先跑统计类（快，且是阴性对照组）与 MOMENT/Chronos（阳性对照组），
足以支撑核心结论；其余可后补。基础模型的依赖见 `TSB_AD/models/README.md`。

仓库内 `vus_eval/` 是官方 VUS-PR 实现的可用副本（只依赖 numpy + sklearn），
用 `generate_curve(label, score, slidingWindow=100, 'opt', thre=250)`，返回元组末位是 VUS-PR。
**主结果必须用 `thre=250`**，否则与官方排行榜不可比。

---

## 7. 计算成本（已实测，据此规划）

在一条长 18049 的序列上：构造 31 条 one-liner 曲线耗时 **0.289 s**；单次 VUS-PR 调用
（`thre=250`）耗时 **0.552 s**。即每条序列的 31 次 VUS-PR 约 17.1 s，**度量占 98% 耗时，
曲线构造只占 1.7%**。

结论与对策：

- **GPU 无用**。VUS-PR 是在 250 个容忍窗口上串行重算 range-based PR 曲线，是标量循环 +
  标签膨胀，没有可并行的稠密矩阵运算。不要试图 GPU 化。
- **并行化序列维度**，350 条彼此独立，`multiprocessing` 按核数开进程，这是唯一有效的加速。
- `thre` 影响：250 → 0.482 s 得 0.1821；100 → 0.205 s 得 0.1549；50 → 0.099 s 得 0.1410。
  **改 thre 不是精度损失而是定义改变**，可用小 thre 做快速迭代，主结果必须回到 250。
- 长序列（max 900000）下若内存吃紧，官方有 `version='opt_mem'` 分支。

---

## 8. 产出物

1. `results/basis_vuspr.csv` — 350 × 31 逐序列基底成绩
2. `results/cdu.csv` — 每个检测器 × 各定义（A / C / D / E）的值 + 胜率 + 与基底的秩相关
3. `results/rerank.csv` — 原始 VUS-PR 榜 vs CDU 榜的名次对照与变化
4. `results/layered.csv` — 按点异常（n=49）/ 序列型异常（n=322）分层的 CDU
   （**必须分层**：方差基线在点异常上天然强、长序列异常上天然弱，聚合数字会掩盖机理）
5. `results/sanity.md` — §5 全部自检的通过情况与数值
6. **核心图**：横轴原始 VUS-PR，纵轴 CDU，四象限散点，按族着色，标注检测器名。
   右下角（原始高、CDU 低）即「虚胖模型」区。
7. `report.md` — 中文报告：方法、陷阱处理、结果、以及明确的 limitation 段落

图表要求：无 chartjunk，去顶右边框，网格极淡或无，色盲友好调色板（Okabe–Ito），
中文标签需显式设置 CJK 字体（`matplotlib.rcParams['font.sans-serif']`，
并置 `axes.unicode_minus = False`），把 `findfont` / `Glyph missing` 警告当失败处理。

---

## 9. 执行顺序

1. 装环境、下数据、核对 §1 的数据事实 → 汇报
2. 跑基底得 `basis_vuspr.csv`，核对 §5.5 量级 → 汇报
3. 实现定义 A + 全部自检 §5.1/5.2/5.3 → 汇报（**自检不过不许继续**）
4. 拉检测器曲线（先统计类 + MOMENT/Chronos）
5. 实现定义 D、E、C，跑 §5.4 族区分度检验 → 汇报
6. 出表、出图、写报告

每阶段汇报时给出关键数字，不要只说「完成」。遇到与 §1 或 §5 矛盾的结果，
**停下来报告矛盾**，不要自行调参掩盖。

---

## 10. 论文层面的定位（帮助你做取舍）

三层结构，价值递增：Diagnosis（证明多少 SOTA 分数可被平凡统计解释）→ Metric（CDU）→
Method（triviality-aware training）。前两层是本任务范围。

若要延伸到第三层，注意一个反直觉的点：**不要把损失写成
$L = L_{AD} + \lambda|\mathrm{corr}(s, \hat s)|$**。若异常本身就是方差尖峰，正确的检测器
本应与滑窗方差高度相关，强制去相关会迫使模型为了「创新」而丢弃真正有用的简单信号。
正确的目标不是「不得学习平凡信息」，而是「在保留平凡信息的同时必须提供额外信息」——
即分解 $s = s_{\text{triv}} + s_{\text{res}}$，令 $s_{\text{triv}} = \Pi_B(s)$，
单独训练 $s_{\text{res}}$ 去最大化条件互信息 $I(y; s_{\text{res}} \mid B)$。
