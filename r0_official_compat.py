"""Official TSB-AD evaluator compatibility for Gate R0 only.

This module does not run CDU.  It restores the historical lower-bound guard
that was used when the official leaderboard VUS table was produced.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import argrelextrema
from statsmodels.tsa.stattools import acf


def find_length_rank_official_compat(data, rank: int = 1) -> int:
    """Historical TSB-AD ``find_length_rank`` behavior.

    The historical implementation falls back to 125 when the selected ACF
    period is below 6 (equivalently, the local-max lag is below 3) or above
    300.  The current checkout removed the lower-bound check.
    """
    data = np.asarray(data).squeeze()
    if len(data.shape) > 1:
        return 0
    if rank == 0:
        return 1
    data = data[: min(20000, len(data))]
    base = 3
    auto_corr = acf(data, nlags=400, fft=True)[base:]
    local_max = argrelextrema(auto_corr, np.greater)[0]
    try:
        sorted_local_max = np.argsort(
            [auto_corr[lcm] for lcm in local_max]
        )[::-1]
        max_local_max = sorted_local_max[0]
        if rank == 2:
            for i in sorted_local_max[1:]:
                if i > sorted_local_max[0]:
                    max_local_max = i
                    break
        elif rank == 3:
            id_tmp = None
            for i in sorted_local_max[1:]:
                if i > sorted_local_max[0]:
                    id_tmp = i
                    break
            if id_tmp is not None:
                for i in sorted_local_max[id_tmp:]:
                    if i > sorted_local_max[id_tmp]:
                        max_local_max = i
                        break
        final_period = int(local_max[max_local_max] + base)
        if final_period < 6 or final_period > 300:
            return 125
        return final_period
    except Exception:
        return 125


def patch_model_wrapper(model_wrapper_module) -> None:
    """Patch only the imported helper used by unsupervised wrappers."""
    model_wrapper_module.find_length_rank = find_length_rank_official_compat

