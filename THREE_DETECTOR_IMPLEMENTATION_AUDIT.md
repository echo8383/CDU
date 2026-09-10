# TranAD / FITS / M2N2 implementation audit

Audit date: 2026-08-28.  Benchmark execution is delegated to TSB-AD commit
`8b363e350ae047a8115a594d1e9da64aae09b852`; the standalone repositories are
used only to verify model provenance and are not used for data loading.

| detector | standalone source | TSB-AD implementation | execution type | score construction | benchmark adaptation |
|---|---|---|---|---|---|
| TranAD | `baseline/TranAD`, `7ffb98d0c18189cc3d9ab732b4cb0278200a0af0` | `TSB_AD/models/TranAD.py`, `run_TranAD` | train-then-score | decoder-2 final-window mean squared reconstruction error, edge padding | filename-derived train prefix, full evaluation sequence, MinMaxScaler in `fit` |
| FITS | `baseline/FITS`, `d040bb015b6299da26d879b90dd19c80fb72c160` | `TSB_AD/models/FITS.py`, `run_FITS` | train-then-score | frequency-interpolation reconstruction MSE at final window position, edge padding | TSB-AD `ReconstructDataset`; internal reversible instance normalization |
| M2N2 | `baseline/M2N2`, `616b2270b6f2eab88ee5caa37c45507d2d041d22` | `TSB_AD/models/M2N2.py`, `run_M2N2` | train-then-score + online test-time adaptation | per-time reconstruction MSE; right-edge padding | train prefix, threshold from train reconstruction errors, online adaptation on test windows; fresh model per series |

All three are present in TSB-AD's supervised pool. Labels are not passed to
training, thresholding, or adaptation. The wrappers call only this pinned
dispatcher and return a one-dimensional continuous score (`higher = more
anomalous`); they contain no VUS/CDU logic.

The standalone TranAD and FITS loaders/evaluation scripts target their own
benchmarks and therefore are not substituted for the TSB-AD loader. M2N2's
standalone protocol confirms the online adaptation concept; TSB-AD's concrete
implementation is the benchmark definition used here.
