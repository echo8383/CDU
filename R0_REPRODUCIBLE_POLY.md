# R0-Reproducible POLY

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

- Rows: 350
- PASS: 350
- FAIL: 0
- Deterministic hash mismatches: 0
- Length mismatches: 0
- Non-finite runs: 0
- Max local VUS implementation difference: 0
- Mean local VUS implementation difference: 0
- **R0-Reproducibility: PASS (350/350)**

## Historical provenance (not a gate)

`official_historical_vus`, `pinned_vus`, and `historical_vus_abs_diff` remain in the CSV. Differences from the historical merged leaderboard are provenance divergence only and are not mixed into the pinned detector CDU result.

Full per-series audit: `layer2_results/poly_reproducibility_350.csv`
