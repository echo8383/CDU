# R0 POLY-170 targeted audit

The first new historical-compatibility failure is:

`170_MITDB_id_1_Medical_tr_17675_1st_17775.csv`

It has length 500,000, historical-compatible window 125, and official POLY
VUS-PR `0.0804445512259431`. The explicit historical mode (`normalize=False`,
power 4, raw input, seed 2024) reproduces `0.053049309338847335`, giving an
absolute difference of `0.027395241887095766`.

The historically older power-2 variant was also tested and gives
`0.05254856276590952` (difference `0.027895988460033577`), so changing to the
initial HP does not reconstruct the official value. The mismatch is therefore
not explained by the confirmed normalization boundary or by the documented HP
history. This classifies the unresolved provenance as **F: official result
cannot be reconstructed from the available artifacts** for this sequence,
unless additional historical score files/runner code are recovered.

The run was stopped; no CDU was run. Sequence 141 remains fixed by historical
compatibility, but full POLY R0 remains FAIL because 170 fails the unchanged
`1e-6` criterion.
