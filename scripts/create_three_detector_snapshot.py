"""Create a transparent current-results snapshot without refitting anything."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
L2 = ROOT / "layer2_results"
OUT = L2 / "THREE_DETECTOR_CURRENT_SNAPSHOT.csv"

SOURCES = {
    "POLY": L2 / "audit_cdu_per_series" / "POLY.csv",
    "SubPCA": L2 / "audit_cdu_per_series" / "SubPCA.csv",
    "TimesNet": L2 / "TimesNet_cdu_per_series.csv",
}
RAW = {
    "POLY": (0.3892705890960274, "AUDITED: pinned cache + raw-data evaluation window"),
    "SubPCA": (0.435273624406006, "PRELIMINARY: legacy offline metric; final raw-window audit pending final report"),
    "TimesNet": (0.25185733660958126, "PRELIMINARY: legacy offline metric; final raw-window audit not run"),
}


def boot(x):
    rng = np.random.default_rng(2024)
    return np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(10_000)])


def main():
    rows = []
    for detector, path in SOURCES.items():
        d = pd.read_csv(path)
        for folds in (5, 10):
            x = d[d.folds == folds].copy()
            if len(x) != 350 or x.series_id.nunique() != 350:
                raise RuntimeError(f"{detector} {folds}-fold incomplete")
            v = x.CDU_bits.to_numpy(float)
            b = boot(v)
            raw, raw_status = RAW[detector]
            rows.append({
                "Detector": detector,
                "folds": folds,
                "series": len(x),
                "Raw_VUS": raw,
                "Raw_VUS_status": raw_status,
                "L0_bits_macro": x.L0_bits.mean(),
                "L1_bits_macro": x.L1_bits.mean(),
                "CDU_bits_macro": v.mean(),
                "CDU_bits_median": np.median(v),
                "CDU_min": v.min(),
                "CDU_max": v.max(),
                "positive_series_count": int((v > 0).sum()),
                "positive_series_ratio": (v > 0).mean(),
                "bootstrap_CI_low": np.percentile(b, 2.5),
                "bootstrap_CI_high": np.percentile(b, 97.5),
                "bootstrap_prob_macro_positive": (b > 0).mean(),
                "per_series_source": str(path),
            })
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(OUT)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
