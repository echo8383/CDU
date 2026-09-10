# SubPCA / AnomalyTransformer interim audit

This is a parallel lightweight audit only: score cache integrity, score-label-basis alignment, manifest hash parity, and three-series fixed-seed reproducibility. It intentionally does not recompute full VUS or CDU while the POLY full recomputation is occupying memory.

| detector           |   series | length_alignment_pass   | basis_label_alignment_pass   | finite_ratio_all_one   | any_constant_score   | manifest_hash_match   | repro_samples_hash_match   | full_VUS_CDU_recompute               |
|:-------------------|---------:|:------------------------|:-----------------------------|:-----------------------|:---------------------|:----------------------|:---------------------------|:-------------------------------------|
| SubPCA             |      350 | True                    | True                         | True                   | False                | True                  | True                       | PENDING (POLY audit continues first) |
| AnomalyTransformer |      350 | True                    | True                         | True                   | True                 | True                  | True                       | PENDING (POLY audit continues first) |

## Interim conclusion

- **SubPCA:** all 350 cached curves have exact score/label/basis alignment, finite scores, manifest-hash parity, and the three fixed-seed reruns reproduce the cache exactly. No constant-score series was found. This is a cache-integrity/reproducibility PASS-candidate; full Raw-VUS/CDU recomputation is still pending.
- **AnomalyTransformer:** all 350 cached curves pass alignment, finiteness, manifest-hash parity, and the three fixed-seed reruns reproduce exactly. Two series have constant scores (zero variance): `531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv` and `536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv`. This is flagged as detector-output collapse for follow-up, not a length/alignment failure.
- The POLY full audit process terminated during its VUS pass before producing the final audit tables; no CDU was run by the interim audit.
