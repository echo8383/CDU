"""Explicit historical POLY compatibility entry point.

The official merged leaderboard predates commit f2bf6b3 (``fix norm``).  At
that boundary POLY did not min-max normalize its input in ``fit``.  This
module keeps modern/default behavior untouched and exposes only the historical
detector path used by the R0 audit.
"""
from __future__ import annotations
import numpy as np

from TSB_AD.models.POLY import POLY

MODE = "official_historical"
HISTORICAL_HP = {"periodicity": 1, "power": 4}

def run_poly_historical(data: np.ndarray, *, window: int, power: int = 4) -> np.ndarray:
    """Run pre-f2bf6b3 POLY behavior on raw full feature data.

    The historical implementation's only relevant behavioral difference for
    this detector is ``normalize=False``.  Input is otherwise passed exactly
    as the official unsupervised runner passes it; POLY itself squeezes the
    single feature and returns one point score per input row.
    """
    clf = POLY(power=power, window=int(window), normalize=False)
    clf.fit(np.asarray(data, dtype=float))
    return np.asarray(clf.decision_scores_, dtype=float).ravel()
