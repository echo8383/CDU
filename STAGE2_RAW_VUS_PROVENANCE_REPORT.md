# Stage 2 Raw VUS provenance

POLY, SubPCA and AnomalyTransformer reuse existing formal raw-data-window audits. MOMENT_FT and MOMENT_ZS passed spot checks. M2N2, TranAD, TimesNet and FITS initially failed spot checks because their legacy per-series VUS used a different window rule; they were therefore upgraded to full offline recomputation from their existing point-score caches. The resulting 350/350 files are `layer2_results/stage2_raw_vus_per_series/<detector>.csv`. No detector was rerun.
