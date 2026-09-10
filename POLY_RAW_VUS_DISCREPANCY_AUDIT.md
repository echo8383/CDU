# POLY Raw-VUS discrepancy

`0.389270589096` is the pinned R0 report value: cached historical-compatible POLY score evaluated with window selected from raw input data. `0.422519085874` was produced later by `offline_metrics_completed.py`, which incorrectly selected evaluation window from the POLY score curve itself. It is not a detector/normalization/score-cache change and is not a valid pinned Raw VUS. The audited CSV is the sole formal value.
