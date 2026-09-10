# POLY full R0 / Layer-2 status

## Status: STOPPED at P1

The requested P2 CDU run was **not started** because full POLY Gate-R0 parity did not pass.

The official-compatible runner used:

- TSB-AD commit `8b363e350ae047a8115a594d1e9da64aae09b852`;
- seed 2024;
- `Optimal_Uni_algo_HP_dict['POLY'] = {'periodicity': 1, 'power': 4}`;
- historical-compatible `find_length_rank`;
- TSB-AD-U-Eva file list and `dropna()` full feature data.

The run was resumable and reached 51/350 records before the first strict failure. The first 44 records passed at machine precision. The run was stopped immediately at the first failure as required.

## Failing sequence

| series_id | length | window | official VUS | reproduced VUS | abs diff | finite ratio | deterministic score hash |
|---|---:|---:|---:|---:|---:|---:|---|
| `141_MSL_id_2_Sensor_tr_500_1st_550.csv` | 2264 | 264 | 0.927581382367 | 0.699803801586 | 0.227777580781 | 1.0 | `4a778112ae65dfcc176c19c8c7ea4242c25397618cfa7576a5b5eb718151cf23` |

The same sequence was run twice with seed 2024 and produced the identical score hash and VUS. Thus the discrepancy is deterministic, not random variance. Recomputing with the default window 100 gives VUS 0.587032435586, so the failure is not caused by window selection. Score length and finiteness are exact; the residual is in detector/provenance parity for this series.

## P2 gate

`poly_full_cdu_per_series.csv` and `poly_full_controls.csv` were intentionally **not generated**. No CDU was run before 350/350 R0 PASS.

See `layer2_results/poly_full_r0.csv` for the resumable audit and `layer2_results/poly_full_r0_failures.csv` for the exact failure row.
