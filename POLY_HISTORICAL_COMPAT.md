# POLY historical compatibility mode

Mode name: `official_historical`.

The target artifact is
`benchmark_exp/benchmark_eval_results/uni_mergedTable_VUS-PR.csv`, whose
POLY-141 value is reproduced by the pre-`f2bf6b3c672b5de9eb5b684c142574e3602bfb76`
implementation. That commit (`fix norm`, 2024-11-06) added `normalize=True`
and min-max scaling inside `POLY.fit`. The historical mode explicitly passes
`normalize=False`; the modern/default POLY behavior is not changed.

Other parity settings are frozen to the official unsupervised protocol:

- repository detector code at `8b363e350ae047a8115a594d1e9da64aae09b852`;
- historical-compatible `find_length_rank` (including the 125 fallback);
- `Optimal_Uni_algo_HP_dict['POLY'] = {'periodicity': 1, 'power': 4}`;
- seed 2024;
- TSB-AD-U-Eva file list;
- `pd.read_csv(...).dropna()` and full feature matrix `df.iloc[:, 0:-1]`;
- no train/test split for the unsupervised POLY branch;
- official VUS-PR `generate_curve(..., slidingWindow=selected_window)`.

The explicit entry point is `poly_historical_compat.run_poly_historical`.
