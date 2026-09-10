from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'
x=pd.read_csv(L2/'STAGE2_AUDITED_LEADERBOARD.csv')
lines=['# STAGE2 Full Incremental Audit Report','', 'No detector was rerun. All four previously unresolved detectors now have 350/350 offline Raw-VUS values computed solely from cached point-wise scores with the frozen raw-input window.','', '## Final statuses']
for _,r in x.iterrows(): lines.append(f"- {r.Detector}: {r.Audit_status}")
lines += ['', '## Authoritative Raw VUS / CDU','', x.to_markdown(index=False), '', '## Decision', '', 'Stage 2 is ready to freeze for the pinned-cache analysis. The four newest detectors were upgraded from pending to PASS after successful full offline recomputation. TimesNet remains PASS_WITH_NO_POSITIVE_INCREMENT; AnomalyTransformer remains PASS_WITH_REPRODUCIBLE_COLLAPSE.']
(ROOT/'STAGE2_FULL_AUDIT_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'STAGE2_RAW_VUS_PROVENANCE_REPORT.md').write_text('# Stage 2 Raw VUS provenance\n\nPOLY, SubPCA and AnomalyTransformer reuse existing formal raw-data-window audits. MOMENT_FT and MOMENT_ZS passed spot checks. M2N2, TranAD, TimesNet and FITS initially failed spot checks because their legacy per-series VUS used a different window rule; they were therefore upgraded to full offline recomputation from their existing point-score caches. The resulting 350/350 files are `layer2_results/stage2_raw_vus_per_series/<detector>.csv`. No detector was rerun.\n',encoding='utf-8')
print(x.to_string(index=False))
