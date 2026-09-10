"""去平凡化：把 one-liner 基底能解释的部分从异常分里扣掉。

核心难点：VUS-PR 非线性，不能靠"线性投影后分数守恒"来定义 excess。
本模块给出三个层次的定义，从弱到强，互为交叉验证：

  A. gap-excess   —— excess = VUS-PR(s) - max_b VUS-PR(b)
                     最直白，但只说"比最好的平凡量强多少"，不排除 s 与 b 同源。

  B. rank-residual —— 在秩空间上把 s 对基底做最小二乘回归，取残差再算 VUS-PR。
                     这是主定义：秩空间回归对 VUS-PR 的单调变换不敏感，
                     且残差保留了"基底解释不了的排序信息"。

  C. cond-excess  —— 条件增益：以基底最优线性组合为基准分，检验 s 是否
                     在基准分之外还能提升检出（用分层的 partial Spearman 与
                     残差 VUS-PR 双指标刻画）。

工程上还必须处理：分数尺度不可比（各检测器量纲不同）→ 全部转秩；
异常占比极低导致 PR 有地板 → 报告相对基线的提升而非绝对值。
"""
import numpy as np
from scipy import stats


def to_rank(s):
    """转为 [0,1] 的秩，处理并列。对任何单调变换不变。"""
    r = stats.rankdata(s, method='average')
    return (r - 1) / max(len(r) - 1, 1)


def _lstsq_resid(y, X):
    """y (n,) 对 X (n,m) 做含截距最小二乘，返回残差与 R^2。"""
    A = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    resid = y - pred
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1.0 - (resid ** 2).sum() / ss_tot if ss_tot > 0 else 0.0
    return resid, pred, r2, coef


def rank_residual_score(s, B):
    """主定义 B：秩空间残差分。

    s: (n,) 待审检测器分数
    B: (m,n) 基底曲线
    返回 (residual_score, r2, basis_pred)
      residual_score 已平移为非负（VUS-PR 只依赖排序，平移无影响）
    """
    y = to_rank(np.nan_to_num(s, nan=0.0))
    X = np.column_stack([to_rank(np.nan_to_num(b, nan=0.0)) for b in B])
    resid, pred, r2, _ = _lstsq_resid(y, X)
    return resid - resid.min(), r2, pred


def basis_best(B, label, metric_fn):
    """基底中单条曲线的最好成绩，以及最好那条的名字索引。"""
    vals = [metric_fn(np.nan_to_num(b, nan=0.0), label) for b in B]
    vals = np.array([v if np.isfinite(v) else 0.0 for v in vals])
    return float(vals.max()), int(vals.argmax()), vals


def basis_combo(B, label, metric_fn, n_iter=200, seed=0):
    """基底凸组合的近似最优成绩（随机搜索 + 单纯形顶点）。

    比单条更强的对手：一个检测器若连基底的凸组合都赢不过，
    说明它几乎没有超出平凡统计量的信息。
    """
    rng = np.random.default_rng(seed)
    Br = np.vstack([to_rank(np.nan_to_num(b, nan=0.0)) for b in B])
    best = -np.inf
    # 顶点（等价于单条）
    for i in range(Br.shape[0]):
        v = metric_fn(Br[i], label)
        if np.isfinite(v):
            best = max(best, v)
    # 随机凸组合
    for _ in range(n_iter):
        w = rng.dirichlet(np.ones(Br.shape[0]) * 0.35)
        v = metric_fn(w @ Br, label)
        if np.isfinite(v):
            best = max(best, v)
    return float(best)


def partial_spearman(s, ref, B):
    """s 与 ref(=label 的某种代理) 在扣除基底后的偏相关。

    这里用于诊断：s 相对基底的"增量方向"是否还与标签一致。
    """
    y = to_rank(s)
    X = np.column_stack([to_rank(b) for b in B])
    ry, _, _, _ = _lstsq_resid(y, X)
    rz, _, _, _ = _lstsq_resid(to_rank(ref), X)
    if ry.std() == 0 or rz.std() == 0:
        return 0.0
    return float(stats.spearmanr(ry, rz).statistic)


def evaluate_detector(s, label, B, metric_fn, combo_iter=150, seed=0):
    """对单个检测器算出完整的一组去平凡化指标。"""
    s = np.nan_to_num(np.asarray(s, dtype=float), nan=0.0)
    raw = metric_fn(s, label)

    b_best, b_idx, b_all = basis_best(B, label, metric_fn)
    b_combo = basis_combo(B, label, metric_fn, n_iter=combo_iter, seed=seed)

    resid, r2, pred = rank_residual_score(s, B)
    resid_vus = metric_fn(resid, label)

    # 与基底最优单条的秩相关（诊断"同源性"）
    rho_best = float(stats.spearmanr(to_rank(s), to_rank(B[b_idx])).statistic)
    # 与基底最优线性组合（回归拟合值）的秩相关
    rho_fit = float(stats.spearmanr(to_rank(s), pred).statistic)

    return {
        'raw': float(raw),
        'basis_best': b_best,
        'basis_combo': b_combo,
        'gap_excess': float(raw - b_best),          # 定义 A
        'gap_excess_combo': float(raw - b_combo),
        'resid_vus': float(resid_vus),              # 定义 B（主）
        'basis_r2': float(r2),                      # 基底对 s 的解释度
        'rho_basis_best': rho_best,
        'rho_basis_fit': rho_fit,
        'basis_best_idx': b_idx,
    }
