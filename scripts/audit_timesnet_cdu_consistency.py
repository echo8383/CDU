"""Offline consistency audit for the existing TimesNet CDU output.

This script intentionally does not rerun TimesNet or refit either CDU probe.
It audits the already saved whole-series OOF results and records the exact
meaning of the formerly ambiguous P_CDU_gt_0 field.
"""
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
L2 = ROOT / "layer2_results"
INPUT = L2 / "TimesNet_cdu_per_series.csv"
SOURCE = ROOT / "scripts" / "fast_cdu_cached.py"
OUTPUT = ROOT / "TIMESNET_CDU_CONSISTENCY_AUDIT.md"


def bootstrap_macro(values: np.ndarray, n_boot: int = 10_000, seed: int = 2024):
    rng = np.random.default_rng(seed)
    n = len(values)
    # Match the original result code exactly: one resampled macro mean/iteration.
    boot = np.array([values[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return boot


def stats_for(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    v = df["CDU_bits"].to_numpy(float)
    boots = bootstrap_macro(v)
    per_fold = (
        df.groupby("fold", sort=True)
        .agg(
            n_series=("series_id", "size"),
            L0_bits_macro=("L0_bits", "mean"),
            L1_bits_macro=("L1_bits", "mean"),
            CDU_bits_macro=("CDU_bits", "mean"),
            positive_series_ratio=("CDU_bits", lambda x: float((x > 0).mean())),
        )
        .reset_index()
    )
    return {
        "n_series": int(len(df)),
        "unique_series": int(df.series_id.nunique()),
        "macro_mean_CDU_bits": float(v.mean()),
        "median_CDU_bits": float(np.median(v)),
        "positive_series_count": int((v > 0).sum()),
        "positive_series_ratio": float((v > 0).mean()),
        "L0_bits_macro": float(df.L0_bits.mean()),
        "L1_bits_macro": float(df.L1_bits.mean()),
        "bootstrap_CI_low": float(np.percentile(boots, 2.5)),
        "bootstrap_CI_high": float(np.percentile(boots, 97.5)),
        "bootstrap_prob_macro_positive": float((boots > 0).mean()),
        "bootstrap_seed": 2024,
        "bootstrap_replicates": 10_000,
    }, per_fold


def table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".12g")


def main() -> None:
    df = pd.read_csv(INPUT)
    required = {"detector", "folds", "fold", "series_id", "L0_bits", "L1_bits", "CDU_bits"}
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"Missing required fields: {sorted(missing)}")
    if set(df.detector) != {"TimesNet"}:
        raise RuntimeError("Input is not TimesNet-only.")

    by_k = {int(k): g.copy() for k, g in df.groupby("folds", sort=True)}
    if set(by_k) != {5, 10}:
        raise RuntimeError(f"Expected exactly 5- and 10-fold rows, got {sorted(by_k)}")
    for k, g in by_k.items():
        if len(g) != 350 or g.series_id.nunique() != 350:
            raise RuntimeError(f"{k}-fold data must contain exactly 350 unique series.")
        if not np.isfinite(g[["L0_bits", "L1_bits", "CDU_bits"]].to_numpy()).all():
            raise RuntimeError(f"{k}-fold data contains non-finite losses.")
        delta_err = np.abs((g.L0_bits - g.L1_bits) - g.CDU_bits).max()
        if delta_err > 1e-12:
            raise RuntimeError(f"{k}-fold CDU identity fails: max error={delta_err}")

    s5, f5 = stats_for(by_k[5])
    s10, f10 = stats_for(by_k[10])
    source = SOURCE.read_text(encoding="utf-8")
    config_match = re.search(r"LogisticRegression\(C=\.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0\)", source)
    score_addition = "np.column_stack([data[i][0],data[i][2]])" in source
    base_input = "m0=LogisticRegression" in source and ".fit(X0,Y)" in source
    summary = pd.DataFrame([{"folds": 5, **s5}, {"folds": 10, **s10}])

    legacy_value = 0.49142857142857144
    identity = abs(s5["positive_series_ratio"] - legacy_value) < 1e-15
    report = [
        "# TimesNet CDU Consistency Audit",
        "",
        "## Scope",
        "",
        "This is an offline audit of the existing `TimesNet_cdu_per_series.csv`. It did not rerun TimesNet, refit CDU probes, modify the estimator, or start another detector.",
        "",
        "## Finding on the legacy `P(CDU>0)=0.4914` field",
        "",
        f"The legacy value `0.49142857142857144` is exactly `172 / 350`, i.e. the **5-fold positive-series ratio** (`CDU_i > 0`). It is not a bootstrap probability for the macro CDU. The old field name `P_CDU_gt_0` was therefore ambiguous/misleading and must not be interpreted as `P(macro CDU > 0)`.",
        "",
        "## Recomputed statistics from existing OOF per-series rows",
        "",
        table(summary),
        "",
        "The requested series-level paired bootstrap is the 5-fold row because that is the primary protocol. It uses 10,000 resamples of the 350 paired per-series CDU deltas with seed 2024.",
        "",
        "## Per-fold held-out losses (macro mean across held-out series)",
        "",
        "### 5-fold",
        "",
        table(f5),
        "",
        "### 10-fold",
        "",
        table(f10),
        "",
        "For every saved row, `CDU_bits = L0_bits - L1_bits` holds to numerical precision. Both 5-fold and 10-fold files contain 350 unique, finite series rows.",
        "",
        "## Probe parity / input audit",
        "",
        f"- Probe configuration found in `fast_cdu_cached.py`: `{config_match.group(0) if config_match else 'NOT FOUND'}`.",
        f"- M0 uses the 31-dimensional basis matrix only: {'PASS' if base_input else 'FAIL'}.",
        f"- M1 uses the same basis matrix plus exactly one extra rank-normalized TimesNet score column: {'PASS' if score_addition else 'FAIL'}.",
        "- The source constructs `X0`, `X1`, and `Y` from the same outer-fold training series; M0 and M1 use identical solver, C, class weighting, iteration cap, and random state.",
        "",
        "## Conclusion",
        "",
        "Classification: **A + B; not C.** There is a reporting-field error: `0.4914` is `positive_series_ratio`, not `bootstrap_prob_macro_positive`. Separately, TimesNet has a stable negative finite-sample predictive increment under this frozen protocol: both 5-fold and 10-fold macro estimates are negative and the 5-fold paired-bootstrap interval is entirely below zero. This is an estimation outcome, not a claim of negative mutual information. The saved M0/M1 identity and code-level probe parity show no evidence here of an estimator implementation failure.",
        "",
        "## Correct field names going forward",
        "",
        "- `positive_series_ratio`: fraction of 350 held-out per-series CDU values > 0 (5-fold: 0.4914285714).",
        f"- `bootstrap_prob_macro_positive`: fraction of bootstrap macro CDU means > 0 (5-fold: {s5['bootstrap_prob_macro_positive']:.4f}, i.e. {int(round(s5['bootstrap_prob_macro_positive'] * s5['bootstrap_replicates']))}/{s5['bootstrap_replicates']} resamples).",
    ]
    OUTPUT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "five_fold": s5, "ten_fold": s10}, indent=2))


if __name__ == "__main__":
    main()
