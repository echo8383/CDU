# Detector Environment Lock

- TSB-AD repository: `D:\CSIES\AI4Energy\others\TSB-AD`
- Git commit: `8b363e350ae047a8115a594d1e9da64aae09b852`
- Seed: `2024`
- Dataset: the 350-series `TSB-AD-U` order in `uni_vuspr.csv`; hashes are recorded in the existing difficulty tables.
- Input protocol: `pd.read_csv(...).dropna()`, features are `df.iloc[:, 0:-1].values.astype(float)`, labels are `Label`; training prefix comes from the filename's `tr_<index>` component.
- Window protocol: `find_length_rank_official_compat` is patched into the TSB-AD wrapper. It is detector-relevant only for wrappers that ask for periodicity.
- Python: current pinned Anaconda interpreter.
- numpy: `1.26.4`; pandas: `2.2.2`; scipy: `1.13.1`; scikit-learn: `1.5.1`; torch: `2.13.0+cu126`.

## Detector modes

| Detector | Source wrapper | Mode |
|---|---|---|
| SubPCA | `run_Sub_PCA` | fit-then-score on the full evaluation sequence (unsupervised) |
| AnomalyTransformer | `run_AnomalyTransformer` | train-then-score: filename-derived train prefix → full evaluation sequence |
| TimesNet | `run_TimesNet` | train-then-score: filename-derived train prefix → full evaluation sequence |
| MOMENT_ZS | `run_MOMENT_ZS` | inference-only / zero-shot on full evaluation sequence; checkpoint `AutonLab/MOMENT-1-base` |
| MOMENT_FT | `run_MOMENT_FT` | train-then-score: fine-tune train prefix → full evaluation sequence; checkpoint `AutonLab/MOMENT-1-base` |

`MOMENT_ZS` and `MOMENT_FT` are separate detector instances. Score sweeps cache only point-wise scores; Raw VUS, Hard-VUS and CDU must read that same cache and must not re-run a detector.
