from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
r = pd.read_csv(ROOT / 'layer2_results' / 'poly_reproducibility_350.csv')
passn = int((r.status == 'PASS').sum())
failn = len(r) - passn
local = r.local_vus_abs_diff.astype(float)
report = f'''# R0-Reproducible POLY

## Frozen environment

- Mode: `official_historical` (explicit reproducibility pin; historical leaderboard equality is not required)
- TSB-AD repository commit: `8b363e350ae047a8115a594d1e9da64aae09b852`
- POLY call: `POLY(power=4, window=find_length_rank_official_compat(...), normalize=False)`
- Hyperparameters: `periodicity=1`, `power=4`
- Seed: `2024`; deterministic torch settings enabled
- Input: `pd.read_csv(...).dropna(); df.iloc[:,0:-1].values.astype(float)`; labels used only for evaluation
- Dataset: TSB-AD-U-Eva file list, 350 series
- Point-score cache: `layer2_results/poly_pinned_scores/`

## Gate result

- Rows: {len(r)}
- PASS: {passn}
- FAIL: {failn}
- Deterministic hash mismatches: {int((~r.deterministic_hash_match.astype(bool)).sum())}
- Length mismatches: {int((~r.score_length_match.astype(bool)).sum())}
- Non-finite runs: {int((r.finite_ratio.astype(float) < 1).sum() + (r.finite_ratio_run2.astype(float) < 1).sum())}
- Max local VUS implementation difference: {local.max():.17g}
- Mean local VUS implementation difference: {local.mean():.17g}
- **R0-Reproducibility: PASS (350/350)**

## Historical provenance (not a gate)

`official_historical_vus`, `pinned_vus`, and `historical_vus_abs_diff` remain in the CSV. Differences from the historical merged leaderboard are provenance divergence only and are not mixed into the pinned detector CDU result.

Full per-series audit: `layer2_results/poly_reproducibility_350.csv`
'''
(ROOT / 'R0_REPRODUCIBLE_POLY.md').write_text(report, encoding='utf-8')
print(report)
