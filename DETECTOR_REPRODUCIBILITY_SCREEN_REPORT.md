# Detector Reproducibility Screening

## Scope

Pinned R0-Reproducibility smoke screen only. No CDU, no detector performance comparison, and no hard-subset evaluation were run. Each candidate was executed twice with seed 2024 on four fixed in-scope series (NAB, WSD, MSL, SMD); score-hash equality, exact length, finite scores, and local VUS parity were required.

## Result

- Passed 4/4 samples: IForest, LOF, MatrixProfile, Sub_HBOS, Sub_IForest, Sub_KNN, Sub_LOF.
- Existing full-350 R0 pass: POLY.
- Candidate pool for *full* R0 (not yet CDU-eligible): POLY, IForest, LOF, MatrixProfile, Sub_HBOS, Sub_IForest, Sub_KNN, Sub_LOF.
- Failed candidates: KShapeAD (3/4), Series2Graph (0/4).

## Failures

- `KShapeAD` / `141_MSL_id_2_Sensor_tr_500_1st_550.csv`: `ValueError('could not convert string to float: "An error occurred while running the model \'run_KShapeAD\': Cannot take a larger sample than population when \'replace=False\'"')`
- `Series2Graph` / `001_NAB_id_1_Facility_tr_1007_1st_2014.csv`: `ValueError('could not convert string to float: "An error occurred while running the model \'run_Series2Graph\': No module named \'TSB_AD.models.Series2Graph\'"')`

Historical leaderboard VUS is retained only as a provenance column. The reproducibility gate does not require historical-table equality.

Per-run results: `data/detector_reproducibility_screen.csv`.
Summary: `data/detector_reproducibility_screen_summary.csv`.