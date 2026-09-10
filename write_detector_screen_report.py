from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent; d=ROOT/'data'; r=pd.read_csv(d/'detector_reproducibility_screen.csv'); s=pd.read_csv(d/'detector_reproducibility_screen_summary.csv')
passed=s.loc[s.status=='PASS','detector'].tolist(); failed=s.loc[s.status!='PASS',['detector','passed','screened']]
lines=['# Detector Reproducibility Screening','', '## Scope','', 'Pinned R0-Reproducibility smoke screen only. No CDU, no detector performance comparison, and no hard-subset evaluation were run. Each candidate was executed twice with seed 2024 on four fixed in-scope series (NAB, WSD, MSL, SMD); score-hash equality, exact length, finite scores, and local VUS parity were required.','', '## Result','', f'- Passed 4/4 samples: {", ".join(passed)}.', '- Existing full-350 R0 pass: POLY.', '- Candidate pool for *full* R0 (not yet CDU-eligible): '+', '.join(['POLY']+passed)+'.', '- Failed candidates: '+', '.join(f"{x.detector} ({int(x.passed)}/{int(x.screened)})" for _,x in failed.iterrows())+'.', '', '## Failures','']
for det in failed.detector:
    x=r[(r.detector==det)&(r.status!='PASS')].iloc[0]
    lines.append(f'- `{det}` / `{x.series_id}`: `{x.error}`')
lines += ['', 'Historical leaderboard VUS is retained only as a provenance column. The reproducibility gate does not require historical-table equality.', '', 'Per-run results: `data/detector_reproducibility_screen.csv`.', 'Summary: `data/detector_reproducibility_screen_summary.csv`.']
(ROOT/'DETECTOR_REPRODUCIBILITY_SCREEN_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
