"""Create a lightweight paper handoff from existing files, without fitting models.

Snapshots summarize local observations only; absent remote files are not failures.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[1]
DETECTORS = ['SubPCA', 'POLY', 'MOMENT_FT', 'MOMENT_ZS', 'M2N2', 'TranAD', 'TimesNet', 'FITS', 'AnomalyTransformer']
CONTROLS = ['duplicate_Var-96', 'independent_noise', 'complementary_alpha_2']


def main():
    now = datetime.now().astimezone()
    dest = ROOT / 'paper' / 'evidence' / now.strftime('%Y-%m-%d')
    dest.mkdir(parents=True, exist_ok=True)
    evidence = []

    def read_csv(path):
        evidence.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        return pd.read_csv(path)

    mapping = json.loads((ROOT / 'source_groups.json').read_text(encoding='utf-8'))['series_to_source']
    sources = pd.Series(mapping, name='source_dataset').value_counts().sort_index()
    sources.rename_axis('source_dataset').reset_index(name='n_series').to_csv(dest / 'source_composition.csv', index=False)
    expected = set(mapping)
    baseline = read_csv(ROOT / 'protocol_fast_results' / 'shared_baseline' / 'PER_SERIES.csv').set_index('series_id')
    if set(baseline.index) != expected or not baseline.index.is_unique:
        raise ValueError('Baseline coverage mismatch')
    status, completed = [], []
    for name in DETECTORS + CONTROLS:
        folder = ROOT / 'protocol_fast_results' / 'main' / name
        checkpoints = list((folder / 'by_source').glob('*.csv'))
        state = 'PARTIAL_LOCAL' if checkpoints else 'NOT_OBSERVED_LOCALLY'
        if (folder / 'SUMMARY.csv').is_file():
            frame = read_csv(folder / 'PER_SERIES.csv')
            summary = read_csv(folder / 'SUMMARY.csv')
            per_source = read_csv(folder / 'PER_SOURCE.csv')
            loss_cols = ['L_null', 'L_basis', 'L_detector', 'L_basis_detector', 'CDU']
            if len(frame) != 350 or set(frame.series_id) != expected or frame.series_id.nunique() != 350:
                raise ValueError(f'{name}: invalid coverage')
            if not np.isfinite(frame[loss_cols].to_numpy()).all():
                raise ValueError(f'{name}: non-finite losses')
            if not (frame.protocol_version == 'CDU-protocol-fast-v1').all():
                raise ValueError(f'{name}: wrong protocol')
            ordered_base = baseline.loc[frame.series_id]
            for col in ['L_null', 'L_basis']:
                np.testing.assert_allclose(frame[col], ordered_base[col], atol=1e-14, rtol=0)
            np.testing.assert_allclose(frame.CDU, frame.L_basis-frame.L_basis_detector, atol=1e-14, rtol=0)
            groups = frame.groupby('source_dataset').CDU.mean()
            if len(groups) != 23 or len(per_source) != 23:
                raise ValueError(f'{name}: missing sources')
            np.testing.assert_allclose(groups.mean(), summary.CDU.iloc[0], atol=1e-14, rtol=0)
            row = summary.iloc[0].to_dict()
            row['positive_sources'] = int((groups > 0).sum())
            row['summary_source'] = (folder / 'SUMMARY.csv').relative_to(ROOT).as_posix()
            completed.append(row)
            state = 'COMPLETE_LOCAL_ARITHMETIC_CHECKED'
        status.append({'experiment': name, 'local_checkpoint_count': len(checkpoints), 'status': state})
    pd.DataFrame(status).to_csv(dest / 'run_status.csv', index=False)
    pd.DataFrame(completed).to_csv(dest / 'fast_completed.csv', index=False)
    old = ROOT / 'layer2_results' / 'STAGE2_AUDITED_LEADERBOARD.csv'
    if old.is_file():
        read_csv(old).to_csv(dest / 'historical_stage2.csv', index=False)
    controls = []
    for path in sorted((ROOT / 'protocol_v1_results' / 'controls').glob('*/SUMMARY.csv')):
        for row in read_csv(path).to_dict('records'):
            row['summary_source'] = path.relative_to(ROOT).as_posix()
            controls.append(row)
    pd.DataFrame(controls).to_csv(dest / 'historical_nested_controls.csv', index=False)
    for path in [ROOT/'source_groups.json', ROOT/'protocol_v1_input_manifest.json', ROOT/'docs/PROTOCOL.md', ROOT/'scripts/run_protocol_fast.py', ROOT/'scripts/evaluate_cdu_protocol_v1.py', ROOT/'scripts/run_protocol_v1_controls.py']:
        evidence.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    metadata = {'as_of': now.isoformat(), 'scope': 'Local files only; not a fresh remote status check or a full score-cache audit',
                'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'versions': {'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},
                'sources': evidence}
    (dest/'manifest.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(pd.DataFrame(status).to_string(index=False))
    print(f'Evidence saved: {dest}')


if __name__ == '__main__':
    main()
