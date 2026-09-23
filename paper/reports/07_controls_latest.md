# Fast controls and paper synchronization

Updated: 2026-09-16T18:05:36.113083+08:00

Nine detector primary runs are reused; detector training and primary probes were not rerun.

| Control | Sources | Status |
|---|---:|---|
| duplicate_Var-96 | 23/23 | COMPLETE_VALIDATED |
| independent_noise | 23/23 | COMPLETE_VALIDATED |
| complementary_alpha_2 | 23/23 | COMPLETE_VALIDATED |

| Control | CDU (bits) | 95% CI | Diagnostic expectation |
|---|---:|---|---|
| duplicate_Var-96 | 4.61124238148e-06 | [-1.2625701953e-06, 1.24380353778e-05] | PASS |
| independent_noise | 7.68546556308e-06 | [1.33909832011e-06, 1.56691463454e-05] | NOT_MET |
| complementary_alpha_2 | 0.10345103958 | [0.0745671322602, 0.133206089217] | PASS |

Checks: expected series IDs per source; 350 unique series; finite losses; fixed C=0.1; held-out source absent from training; shared L0/LB and time-point counts; per-series CDU=L_B-L_BD; 23-source macro means; independently regenerated 10,000-replicate paired bootstrap.

Source influence is reaggregation of existing OOF losses without fitting new probes. It is not evidence of robustness to different probe families or basis definitions.

Remaining nonlinear-probe and basis-family experiments have not been executed. They require an explicit separate fixed configuration and their own controls; no results are invented.

The old QUEUE_STATUS.json is not a global completion signal: use the control-specific 350-series summary and by-source files.
