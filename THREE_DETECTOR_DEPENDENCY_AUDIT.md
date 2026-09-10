# Dependency audit

Pinned benchmark runtime (observed): Python 3.12.7, numpy 1.26.4, pandas 2.2.2,
scipy 1.13.1, scikit-learn 1.5.1, torch 2.13.0+cu126, CUDA available (RTX 4060
Laptop GPU). TSB-AD commit: `8b363e350ae047a8115a594d1e9da64aae09b852`.

| repository | declared requirements relevant here | assessment |
|---|---|---|
| TranAD | numpy, pandas, scipy ecosystem, scikit-learn, tqdm, dgl, matplotlib, `xlrd==1.2.0` | no pinned torch conflict in requirements; TSB-AD implementation imports successfully in current environment; DGL is not used by the TranAD wrapper |
| FITS | `torch==2.7.0`, `numpy==1.26.4`, `pandas==2.2.3`, `scikit_learn==1.5.2`, tqdm | minor version drift from current runtime; TSB-AD FITS imports and smoke-runs; do not overwrite the frozen environment |
| M2N2 | exported environment includes `torch==1.9.1`, `torchvision==0.10.1`, `numpy==1.24.3`, `pandas==2.1.2`, `scikit-learn==1.3.2`, `scipy==1.11.3` | clear conflicts with current CUDA/Python stack; use the TSB-AD compatibility implementation in the current environment or isolate a dedicated environment if later failures occur; never bulk-install this file into CDU env |

Decision: TranAD and FITS are compatible in the current pinned runtime for
smoke validation. M2N2 is marked **compatibility-patch / isolated-environment
candidate**; its smoke test nevertheless passes through TSB-AD without changing
the current environment.
