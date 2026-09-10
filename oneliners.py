"""One-liner 异常分基底：零参数、纯 numpy。

严格按 ICLR 2026 "When Foundation Models Are One-Liners" 的定义实现：

  Var-w    : score[i + floor(w/2)] = Var(T[i : i+w])
  Last-w   : score[i + w]          = (mean(T[i : i+w]) - x[i+w])^2
  Centered-w: 同 Last-w 但把分数放在窗口中心

外加几个同样零参数的常见统计量，用于把基底张得更宽（消融时可分组）。
所有函数返回与输入等长的一维分数数组，越大越异常。
"""
import numpy as np


def _sliding(x, w):
    """长度 n 的一维数组 -> (n-w+1, w) 的滑窗视图（零拷贝）。"""
    return np.lib.stride_tricks.sliding_window_view(x, w)


def _place(vals, n, offset):
    """把 len(vals) 的窗口统计量放回长度 n 的分数数组，两端用边缘值填充。"""
    s = np.full(n, np.nan)
    s[offset:offset + len(vals)] = vals
    # 边缘填充：保持与 TSB-AD 的等长约定，且不引入人造尖峰
    first = np.nanargmax(~np.isnan(s)) if np.isnan(s[0]) else 0
    last = n - 1 - (np.nanargmax(~np.isnan(s[::-1])) if np.isnan(s[-1]) else 0)
    s[:first] = s[first]
    s[last + 1:] = s[last]
    return s


def var_w(x, w):
    """滑窗方差，分数落在窗口中心。对应重构型模型的塌陷目标。"""
    n = len(x)
    if w >= n:
        return np.zeros(n)
    v = _sliding(x, w).var(axis=1)
    return _place(v, n, w // 2)


def last_w(x, w):
    """一步预测平方误差：用窗口均值预测下一点。对应预测型模型的塌陷目标。"""
    n = len(x)
    if w + 1 >= n:
        return np.zeros(n)
    m = _sliding(x[:-1], w).mean(axis=1)      # 窗口 i..i+w-1 的均值
    tgt = x[w:]                                # 待预测点 i+w
    e = (m - tgt) ** 2
    return _place(e, n, w)


def centered_w(x, w):
    """同 last_w，但分数放到窗口中心（对长异常段更对称）。"""
    n = len(x)
    if w + 1 >= n:
        return np.zeros(n)
    m = _sliding(x[:-1], w).mean(axis=1)
    e = (m - x[w:]) ** 2
    return _place(e, n, w // 2)


def range_w(x, w):
    """滑窗极差 max-min。"""
    n = len(x)
    if w >= n:
        return np.zeros(n)
    sw = _sliding(x, w)
    return _place(sw.max(axis=1) - sw.min(axis=1), n, w // 2)


def absdiff(x, w=1):
    """一阶差分绝对值（w 步）。最朴素的点异常检出器。"""
    n = len(x)
    d = np.abs(np.diff(x, n=1))
    if w > 1:
        k = np.ones(w) / w
        d = np.convolve(d, k, mode='same')
    return _place(d, n, 1)


def mad_w(x, w):
    """滑窗中位数绝对偏差，方差的稳健版本。"""
    n = len(x)
    if w >= n:
        return np.zeros(n)
    sw = _sliding(x, w)
    med = np.median(sw, axis=1, keepdims=True)
    return _place(np.median(np.abs(sw - med), axis=1), n, w // 2)


def spec_entropy_w(x, w, step=None):
    """滑窗谱熵（负号取反：熵越低=越规则=越不异常）。

    为控制开销按 step 下采样窗口起点再线性插值回原长。
    """
    n = len(x)
    if w >= n:
        return np.zeros(n)
    step = step or max(1, w // 8)
    starts = np.arange(0, n - w + 1, step)
    out = np.empty(len(starts))
    for j, s in enumerate(starts):
        seg = x[s:s + w]
        seg = seg - seg.mean()
        p = np.abs(np.fft.rfft(seg)) ** 2
        tot = p.sum()
        if tot <= 0:
            out[j] = 0.0
            continue
        p = p / tot
        p = p[p > 0]
        out[j] = -(p * np.log(p)).sum()
    # 插值回每个窗口中心
    centers = starts + w // 2
    grid = np.arange(n)
    full = np.interp(grid, centers, out)
    return full


# ---- 基底定义 --------------------------------------------------------------
# 分组便于消融：'recon' 对应重构型塌陷，'pred' 对应预测型塌陷，'other' 补充
WINDOWS = [8, 16, 32, 64, 96, 128, 256]
PRED_W = [1, 2, 3, 8, 16, 32, 64]


def build_basis(x, windows=None, pred_w=None, include=('recon', 'pred', 'other')):
    """返回 (names, B)，B 形状 (m, n)，每行一条 one-liner 分数曲线。"""
    windows = windows or WINDOWS
    pred_w = pred_w or PRED_W
    n = len(x)
    names, rows = [], []

    if 'recon' in include:
        for w in windows:
            if w < n:
                names.append(f'Var-{w}'); rows.append(var_w(x, w))
        for w in windows:
            if w < n:
                names.append(f'Range-{w}'); rows.append(range_w(x, w))
    if 'pred' in include:
        for w in pred_w:
            if w + 1 < n:
                names.append(f'Last-{w}'); rows.append(last_w(x, w))
        for w in [3, 16, 64]:
            if w + 1 < n:
                names.append(f'Centered-{w}'); rows.append(centered_w(x, w))
    if 'other' in include:
        for w in [1, 4, 16]:
            names.append(f'AbsDiff-{w}'); rows.append(absdiff(x, w))
        for w in [32, 128]:
            if w < n:
                names.append(f'MAD-{w}'); rows.append(mad_w(x, w))
        for w in [64, 256]:
            if w < n:
                names.append(f'SpecEnt-{w}'); rows.append(spec_entropy_w(x, w))

    B = np.vstack(rows)
    B = np.nan_to_num(B, nan=0.0, posinf=0.0, neginf=0.0)
    return names, B
