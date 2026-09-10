# STAGE2 Full Incremental Audit Report

No detector was rerun. All four previously unresolved detectors now have 350/350 offline Raw-VUS values computed solely from cached point-wise scores with the frozen raw-input window.

## Final statuses
- SubPCA: PASS
- POLY: PASS
- MOMENT_FT: PASS
- MOMENT_ZS: PASS
- M2N2: PASS
- TranAD: PASS
- TimesNet: PASS_WITH_NO_POSITIVE_INCREMENT
- FITS: PASS
- AnomalyTransformer: PASS_WITH_REPRODUCIBLE_COLLAPSE

## Authoritative Raw VUS / CDU

|   Raw_rank |   CDU_rank | Detector           |   Raw_VUS |   CDU_5fold_bits |   CDU_10fold_bits |   CDU_CI_low |   CDU_CI_high |   positive_series_ratio |   bootstrap_prob_macro_positive | Audit_status                    | Audit_source                                                               |
|-----------:|-----------:|:-------------------|----------:|-----------------:|------------------:|-------------:|--------------:|------------------------:|--------------------------------:|:--------------------------------|:---------------------------------------------------------------------------|
|          1 |          1 | SubPCA             |  0.422413 |      0.0599956   |       0.0616257   |  0.0545811   |   0.0655465   |                0.914286 |                          1      | PASS                            | audit_raw_vus_per_series.csv; SUBPCA_PINNED_AUDIT.md                       |
|          2 |          4 | POLY               |  0.389271 |      0.00850339  |       0.00847239  |  0.00734496  |   0.00962584  |                0.811429 |                          1      | PASS                            | audit_raw_vus_per_series.csv; POLY_RAW_VUS_DISCREPANCY_AUDIT.md            |
|          3 |          5 | MOMENT_FT          |  0.386409 |      0.00189364  |       0.00147561  |  0.00108241  |   0.00272325  |                0.765714 |                          1      | PASS                            | MOMENT_FT_audited_per_series_vus.csv + cache spot audit                    |
|          4 |          7 | MOMENT_ZS          |  0.383229 |      0.000324325 |       0.000245292 |  0.00010958  |   0.000587259 |                0.585714 |                          0.9998 | PASS                            | MOMENT_ZS_audited_per_series_vus.csv + cache spot audit                    |
|          5 |          2 | M2N2               |  0.287047 |      0.0294042   |       0.0295113   |  0.0268678   |   0.0320523   |                0.977143 |                          1      | PASS                            | stage2_raw_vus_per_series/M2N2.csv (350/350 cache-only recomputation)      |
|          6 |          3 | TranAD             |  0.275403 |      0.0217128   |       0.0220818   |  0.0190118   |   0.0244874   |                0.825714 |                          1      | PASS                            | stage2_raw_vus_per_series/TranAD.csv (350/350 cache-only recomputation)    |
|          7 |          9 | TimesNet           |  0.262746 |     -0.000268866 |      -0.000201764 | -0.000431833 |  -0.000112892 |                0.491429 |                          0.0006 | PASS_WITH_NO_POSITIVE_INCREMENT | stage2_raw_vus_per_series/TimesNet.csv + TIMESNET_CDU_CONSISTENCY_AUDIT.md |
|          8 |          6 | FITS               |  0.246369 |      0.000670797 |       0.000482823 |  0.000469384 |   0.000870894 |                0.677143 |                          1      | PASS                            | stage2_raw_vus_per_series/FITS.csv (350/350 cache-only recomputation)      |
|          9 |          8 | AnomalyTransformer |  0.111769 |     -0.000199523 |      -0.000114196 | -0.000614935 |   0.000200234 |                0.485714 |                          0.1647 | PASS_WITH_REPRODUCIBLE_COLLAPSE | audit_raw_vus_per_series.csv; ANOMALYTRANSFORMER_WRAPPER_AUDIT.md          |

## Decision

Stage 2 is ready to freeze for the pinned-cache analysis. The four newest detectors were upgraded from pending to PASS after successful full offline recomputation. TimesNet remains PASS_WITH_NO_POSITIVE_INCREMENT; AnomalyTransformer remains PASS_WITH_REPRODUCIBLE_COLLAPSE.
