# Stage-2 score-cache audit duplicate-row note

During protocol-v1 input freezing, `layer2_results/STAGE2_SCORE_CACHE_AUDIT.csv` was found to contain 6,300 relevant rows for 9 detectors x 350 series. Each detector-series has one valid `cache_exists=True, status=PASS` row and one stale `cache_exists=False, status=FAIL, error=missing cache` row produced by an older incorrect path lookup.

This does not indicate that the current score files are missing. `STAGE2_AUDIT_INVENTORY.csv` records all nine score caches as audited, and the unique PASS rows contain the current score hashes.

Protocol v1 does not silently trust or deduplicate this historical table. `scripts/build_protocol_v1_input_manifest.py`:

1. requires exactly one `cache_exists=True, status=PASS` row per detector-series;
2. directly computes SHA-256 for every one of the 3,150 current `.npy` files;
3. requires every direct hash to equal its unique PASS audit hash;
4. records the stale-row count in `protocol_v1_input_manifest.json`.

The historical CSV is preserved unchanged as provenance evidence.
