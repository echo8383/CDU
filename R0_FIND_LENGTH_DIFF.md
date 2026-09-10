# R0 `find_length_rank` compatibility audit

## Current implementation

At repository commit `8b363e350ae047a8115a594d1e9da64aae09b852`,
`TSB_AD/utils/slidingWindows.py::find_length_rank`:

1. squeezes the input and returns `0` for a multi-dimensional result;
2. returns `1` for `rank=0`;
3. computes ACF on the first 20,000 samples with `nlags=400`, `fft=True`;
4. finds local maxima after `base=3` and selects the highest ranked one;
5. returns `local_max[idx] + 3`, except when that value is greater than 300,
   in which case it returns 125; exceptions also return 125.

The current code therefore permits a selected period below 6. For
`039_WSD_id_11_WebService_tr_1746_1st_1846.csv`, it returns 4.

## Official-compatible implementation

The evaluator used for the official leaderboard had the same ACF and ranking
logic, but applied the additional guard before returning the period:

```python
final_period = local_max[max_local_max] + base
if final_period < 6 or final_period > 300:
    return 125
return final_period
```

Equivalently, the historical source checked the local-maximum lag with
`local_max[idx] < 3` before returning. Because `base=3`, this is the same
behavior for the relevant data: periods below 6 fall back to 125.

## Exact behavioral difference

The only behavioral difference is the missing lower-bound fallback. It changes
short-period ACF selections into the fixed fallback window 125. It does not
change input data, detector HP, score orientation, or preprocessing.

Git evidence:

```text
cd66bc1  Fix logic bug discarding periods smaller than 5
```

That commit changed the old `<3 or >300` guard to only `final_period > 300`.

## Compatibility implementation in this project

`r0_official_compat.py` exposes `find_length_rank_official_compat` and patches
the runner's imported helper only for the R0 reproduction process. It uses the
official seed, raw feature data, official HP dictionary, and official VUS
window. No CDU code is invoked.
