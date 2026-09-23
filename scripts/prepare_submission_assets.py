"""Render submission tables/figures from saved evidence. No model fits or metrics.

Supersedes prepare_paper_revision.py for the current manuscript layout; the older
script and its contrast evidence remain available for historical reproduction.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from scipy.stats import spearmanr
from prepare_paper_revision import STYLE, PROBES

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'icassp/figures'
raw = pd.read_csv(ROOT/'paper/evidence/fast_main/MAIN_RESULTS.csv').set_index('Detector')
det = pd.read_csv(ROOT/'paper/evidence/rank_probe_extension/DETECTORS.csv').set_index(['probe','detector'])
util = pd.read_csv(ROOT/'paper/evidence/cdu_followup/DETECTOR_ONLY_VS_CDU.csv').set_index(['probe','detector'])
decomp = pd.read_csv(ROOT/'paper/evidence/score_decomposition/DETECTOR_DECOMPOSITION_SUMMARY.csv').set_index('detector')
ranks = det.CDU.unstack('probe')[PROBES].rank(ascending=False)
assert set(raw.index) == set(STYLE) == set(ranks.index) == set(decomp.index)
assert len(det) == len(util) == 27 and np.isfinite(det[['CDU','CI_low','CI_high']]).all().all()
assert all(set(ranks.index[ranks[p] <= 4]) == {'SubPCA','M2N2','POLY','TranAD'} for p in PROBES)


def save(fig, name):
    fig.savefig(FIG/f'{name}.pdf', bbox_inches='tight', pad_inches=.045)
    fig.savefig(FIG/f'{name}.png', dpi=200, bbox_inches='tight', pad_inches=.045)
    plt.close(fig)


def table(zh):
    caption = ('九组固定检测器分数的主要 spline 结果。VUS-PR 为序列宏平均；$U_D$ 与 CDU 以比特计量；括号为名次，方括号为 95\\% 来源 Bootstrap 区间。' if zh else
               'Primary spline results for nine fixed detector scores. VUS-PR is series-macro; $U_D$ and CDU are in bits. Parentheses give ranks; brackets give source-bootstrap 95\\% intervals.')
    header = r'Detector & VUS-PR (rank) & $U_D$ (rank) & CDU [95\% CI] & CDU rank \\'
    lines = [r'\begin{table*}[!t]' if zh else r'\begin{table*}[t]', r'\centering', r'\small', r'\caption{'+caption+'}',
             r'\label{tab:main}', r'\setlength{\tabcolsep}{7pt}', r'\begin{tabular}{ccccc}',
             r'\toprule',header,r'\midrule']
    for d in raw.sort_values('Raw_VUS',ascending=False).index:
        r = det.loc[('spline',d)]
        raw_rank = int(raw.Raw_VUS.rank(ascending=False).loc[d])
        utility_rank = int(util.xs('spline').detector_utility.rank(ascending=False).loc[d])
        values = [d.replace('_','-'), f'{raw.loc[d,"Raw_VUS"]:.4f} ({raw_rank})',
                  f'{util.loc[("spline",d),"detector_utility"]:.5f} ({utility_rank})',
                  f'{r.CDU:.5f} [{r.CI_low:.5f}, {r.CI_high:.5f}]',
                  str(int(ranks.loc[d,'spline']))]
        lines.append(' & '.join(values)+r' \\')
    lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table*}'])
    suffix = '_zh' if zh else ''
    (ROOT/f'icassp/tables/primary_results{suffix}.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def comparisons(zh):
    plt.rcParams.update({'font.family':'Microsoft YaHei' if zh else 'DejaVu Serif',
                         'font.size':7.7, 'pdf.fonttype':42,'axes.spines.top':False,
                         'axes.spines.right':False})
    fig,axs = plt.subplots(1,3,figsize=(7.05,2.73))
    fig.subplots_adjust(left=.065,right=.99,bottom=.27,top=.9,wspace=.46)
    a,b,c = axs
    for d,(color,marker) in STYLE.items():
        y = det.loc[('spline',d),'CDU']
        for ax,x in [(a,util.loc[('spline',d),'detector_utility']),(b,decomp.loc[d,'source_macro_R2'])]:
            ax.scatter(x,y,s=38 if d in {'SubPCA','M2N2','POLY','TranAD','MOMENT_FT','MOMENT_ZS'} else 31,
                       marker=marker,color=color,edgecolors='#414B53',linewidths=.6,zorder=3)
        c.plot(range(3),ranks.loc[d],color=color,marker=marker,markersize=5,
               linewidth=1,markeredgecolor='#555555',markeredgewidth=.3)
    a.set(xlim=(-.002,.044),ylim=(-.0015,.018),xlabel='$U_D$ (bits)',ylabel='CDU (bits)')
    b.set(xlim=(-.12,.98),ylim=(-.0015,.018),
          xlabel='分数重构 $R^2$' if zh else 'Score reconstruction $R^2$')
    a.set_xticks([0,.01,.02,.03,.04],['0','.01','.02','.03','.04']); b.set_xticks([0,.5,1.0])
    for ax in [a,b]:
        ax.set_yticks([0,.005,.01,.015],['0','.005','.010','.015'])
        ax.tick_params(labelsize=7.2)
    matched_rho = spearmanr(util.xs('spline').detector_utility.reindex(raw.index),
                            det.xs('spline').CDU.reindex(raw.index)).statistic
    a.text(.03,.96,rf'$\rho={matched_rho:.3f}$',transform=a.transAxes,va='top',fontsize=7.7)
    b.text(.03,.96,r'$\rho=-0.167$',transform=b.transAxes,va='top',fontsize=7.7)
    # Directly label the detectors carrying the main comparison; the legend
    # preserves the complete nine-model key without relying on color alone.
    offsets = {'SubPCA':(-42,6),'M2N2':(3,5),'TranAD':(-9,10),
               'POLY':(3,6),'MOMENT_FT':(4,11),'MOMENT_ZS':(-24,13)}
    for d,(dx,dy) in offsets.items():
        label = {'SubPCA':'SubPCA','M2N2':'M2N2','TranAD':'TranAD',
                 'POLY':'POLY','MOMENT_FT':'M-FT','MOMENT_ZS':'M-ZS'}[d]
        a.annotate(label,(util.loc[('spline',d),'detector_utility'],det.loc[('spline',d),'CDU']),
                   xytext=(dx,dy),textcoords='offset points',fontsize=7,
                   arrowprops=dict(arrowstyle='-',color='#777777',lw=.45),color='#333333')
    for d,dx,dy in [('MOMENT_FT',-30,10),('MOMENT_ZS',-34,9),('M2N2',3,5)]:
        b.annotate({'MOMENT_FT':'M-FT','MOMENT_ZS':'M-ZS','M2N2':'M2N2'}[d],
                   (decomp.loc[d,'source_macro_R2'],det.loc[('spline',d),'CDU']),
                   xytext=(dx,dy),textcoords='offset points',fontsize=7,
                   arrowprops=dict(arrowstyle='-',color='#777777',lw=.45),color='#333333')
    c.axhspan(.5,4.5,color='#78B6C8',alpha=.16,zorder=0)
    c.set(xlim=(-.2,2.2),ylim=(9.6,.4),ylabel='CDU 排名' if zh else 'CDU rank')
    c.set_xticks(range(3),['Linear','Spline','HGB']); c.set_yticks(range(1,10))
    c.tick_params(labelsize=7.2)
    titles = (['(a) 同一指标，不同问题','(b) 可重构性 ≠ 标签效用','(c) 条件排序跨探针稳定'] if zh else
              ['(a) Same metric, different question','(b) Reconstructibility ≠ label utility',
               '(c) Conditional ranks are stable'])
    for ax,title in zip(axs,titles):
        ax.set_title(title,fontsize=7.8,loc='left',pad=9)
    handles = [Line2D([],[],linestyle='none',marker=m,color=col,label=d.replace('_','-'),markersize=5)
               for d,(col,m) in STYLE.items()]
    fig.legend(handles=handles,ncol=5,loc='lower center',frameon=False,fontsize=7.3,
               columnspacing=.95,handletextpad=.35,bbox_to_anchor=(.5,.01))
    save(fig,'conditional_comparison'+('_zh' if zh else ''))


def protocol(zh):
    plt.rcParams.update({'font.family':'Microsoft YaHei' if zh else 'DejaVu Serif',
                         'pdf.fonttype':42})
    fig,ax = plt.subplots(figsize=(3.35,1.74))
    ax.set(xlim=(0,10),ylim=(0,6.5)); ax.axis('off')
    blue, coral = '#466F87', '#E48578'
    def box(x,y,w,h,txt,face,edge,fs=7.3):
        ax.add_patch(FancyBboxPatch((x,y),w,h,
                     boxstyle='round,pad=0.07,rounding_size=0.10',
                     fc=face,ec=edge,lw=.8))
        ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=fs)
    def arrow(x1,y1,x2,y2):
        ax.annotate('',xy=(x2,y2),xytext=(x1,y1),
                    arrowprops=dict(arrowstyle='->',lw=.8,color='#6A737A'))
    box(3.4,5.58,3.2,.72,'序列 $x(t)$' if zh else 'Series $x(t)$',
        '#F4F6F7','#71808A',8)
    box(.45,4.25,3.25,.69,'检测分数 $S_D$' if zh else 'Detector $S_D$',
        '#FBEDEB',coral,7.3)
    box(6.3,4.25,3.25,.69,'统计参考 $B$' if zh else 'Statistics $B$',
        '#EAF2F6',blue,7.3)
    arrow(4.1,5.51,2.2,5.02); arrow(5.9,5.51,7.9,5.02)
    box(.22,2.16,4.35,1.65,'', '#FFF9F7',coral)
    box(5.43,2.16,4.35,1.65,'', '#F7FAFB',blue)
    ax.text(2.4,3.43,'独立评价' if zh else 'Standalone',ha='center',fontsize=7.6,
            weight='bold',color=coral)
    ax.text(7.6,3.43,'条件评价' if zh else 'Conditional',ha='center',fontsize=7.6,
            weight='bold',color=blue)
    ax.text(2.4,2.83,r'$S_D\rightarrow q_D\rightarrow L_D$',ha='center',fontsize=7.6)
    ax.text(2.4,2.38,r'$U_D=L_0-L_D$',ha='center',fontsize=7.4)
    ax.text(7.6,2.99,r'$B\rightarrow q_B\rightarrow L_B$',ha='center',fontsize=7.3)
    ax.text(7.6,2.48,r'$(B,S_D)\rightarrow q_{BD}\rightarrow L_{BD}$',ha='center',fontsize=7.2)
    ax.text(5,1.66,'相同留出点、探针族和权重' if zh else 'Matched held-out points, probe family, weights',
            ha='center',fontsize=6.8,color='#4F5E68')
    box(1.55,.32,6.9,.93,r'$\mathrm{CDU}=L_B-L_{BD}$',
        '#EAF2F6',blue,9)
    save(fig,'protocol'+('_zh' if zh else ''))


def technical_methods():
    text = '''# Accompanying methods and complete numerical results

This document retains details compressed out of the four-page manuscript.
The spline setting is the main presentation of an already completed multi-probe
comparison, not a claim that spline was prospectively selected before all results.
No detector was rerun for this revision. All tables below use saved evidence;
completed normalization and reference-strength robustness results are documented
in `paper/reports/REFERENCE_ROBUSTNESS_20260923.md` and quoted in the manuscript.

## Statistical reference

The 31 fixed scorer definitions come from the project implementation
`_archive/pre_fast_cleanup_2026-09-14/root/oneliners.py`. Variance and next-point
mean deviation are motivated by the One-Liners study; the other families are
project reference extensions, not a claim that all 31 originate in that paper.
Let a window start at i, have width w, and mean mu_i. Zero-based placements:

| Family | Definition | Widths | Placement |
|---|---|---|---|
| Variance (7) | Mean squared deviation from mu_i (ddof=0) | 8,16,32,64,96,128,256 | i+floor(w/2) |
| Range (7) | Window max minus min | same as variance | i+floor(w/2) |
| Next-point deviation (7) | (mu_i-x[i+w])^2 | 1,2,3,8,16,32,64 | i+w |
| Center-placed deviation (3) | Same next-point error, placed earlier; not deviation of the center observation | 3,16,64 | i+floor(w/2) |
| Absolute difference (3) | abs(x[t]-x[t-1]), optionally smoothed with a length-w uniform convolution (`same`) | 1,4,16 | starts at index 1 |
| Median absolute deviation (2) | Median absolute distance to window median | 32,128 | i+floor(w/2) |
| Spectral entropy (2) | -sum(p log p), p from normalized demeaned-window rFFT power | 64,256 | centers; stride w/8 and linear interpolation |

Window scorers extend the nearest valid score at both edges. Spectral entropy
uses natural logarithms, assigns zero for zero spectral power, and interpolates
with endpoint extension. These centered/full-curve operations are offline.
All scored inputs use within-series average ranks; constant curves map to 0.5.
Features summarize dispersion, local prediction error/change, and spectral
irregularity; they are a declared reference, not an exhaustive statistical model.

## Data grouping and weighting

The source token is matched by `^\\d+_([^_]+)_` in each series identifier.
For a held-out source, all its series are excluded from probe training. The 350
series and 23 groups are exactly those in `source_groups.json`.
Uniform sampling without replacement retains m_i=min(T_i,2048) training points.
The same sampled indices are used for every matched probe and condition. Each
retained point has weight N_s/(G_train*n_g*m_i), where N_s is the retained total.
Full-data linear training replaces m_i with T_i. Test curves remain complete.
Sample weights are not additional class balancing.

## Predictor settings and uncertainty

Logistic: liblinear, inverse L2 strength C=0.1, max_iter=300, tol=1e-4,
random_state=2024, fit_intercept=True, intercept_scaling=1, class_weight=None.
Spline: degree=3, fixed knots [0,1/3,2/3,1], include_bias=False,
extrapolation=constant; same logistic settings.
HGB: learning_rate=0.1, max_iter=32, max_leaf_nodes=7, max_depth=3,
min_samples_leaf=100, l2_regularization=1, max_bins=31,
early_stopping=False, random_state=2024. No hyperparameter search.
Probabilities are clipped to [1e-7,1-1e-7] for log-loss in bits.
Ridge score reconstruction uses alpha=1, cap2048, complete test curves and
source-macro averages of per-series R2 and Spearman; it predicts rank scores.

Single-utility percentile intervals: 10,000 paired source-bootstrap resamples,
seed2024. Paired detector contrasts: 20,000 shared draws, seed2024, plus a joint
nine-contrast centered max-standardized bootstrap interval. The nine contrasts
are all pairs of POLY/MOMENT_FT/MOMENT_ZS under linear/spline/HGB. These were
exploratory, motivated by observed similar VUS, not a preregistered family.
The separate 27-test family concerns individual CDU versus zero, not detector
differences. It includes max-bootstrap intervals and one-sided source t-tests
with Holm adjustment as exploratory sensitivity checks. Neither bootstrap nor
Holm removes dependence due to overlapping LOSO training; fits are not repeated.

Controls: exact Var-96 rank-feature copy; independent standard-normal noise;
rank(Z+2Y) with independent standard-normal Z. Noise is deterministically seeded
by control name/series identity. Synthetic labels are used only in calibration.
Duplicating a feature can change L2 penalty geometry; no noise bias subtraction.

## Complete numerical tables
'''
    mapping = json.loads((ROOT/'source_groups.json').read_text(encoding='utf-8'))
    groups = pd.DataFrame(list(mapping['source_counts'].items()),columns=['source','n_series'])
    assert groups.n_series.sum()==350 and len(groups)==23
    tables = [('Source groups',groups),('Full-data linear results and both VUS aggregations',raw.reset_index()),
              ('All matched-probe CDU estimates and intervals',det.reset_index().drop(columns=['source'])),
              ('All detector-only utilities and matched CDU',util.reset_index()),
              ('Score reconstruction and residual decomposition',decomp.reset_index())]
    for title,path in [('Controls','rank_probe_extension/CONTROLS.csv'),
                       ('Paired differences','paired_contrasts/PAIRED_CDU_CONTRASTS.csv'),
                       ('Multiplicity and source influence','source_inference/MULTIPLICITY.csv'),
                       ('Five-seed summary','cdu_followup/SPLINE_FIVE_SEED_SUMMARY.csv'),
                       ('Reference removals','cdu_followup/SPLINE_BASIS_COMPLETED.csv')]:
        frame = pd.read_csv(ROOT/'paper/evidence'/path)
        tables.append((title,frame.drop(columns=['source'],errors='ignore')))
    for title,frame in tables:
        text += '\n### '+title+'\n\n'+frame.to_markdown(index=False,floatfmt='.8g')+'\n'
    text += '''\n## Interpretation and revision provenance

Negative estimates and the full-data linear noise interval excluding zero are
retained. Positive paired POLY/MOMENT spline contrasts do not imply the same
significance under other probes; see the complete contrast table. Rank agreement
does not establish invariance of individual effects or simultaneous significance.
The main manuscript retains the absolute-utility multiplicity finding in concise
form. No original evidence files are removed or overwritten by this asset script.

Bibliographic verification used the official ACL page for conditional probing
(https://aclanthology.org/2021.emnlp-main.122/) and the publisher abstract for the
related drift study (https://www.sciencedirect.com/science/article/pii/S1568494626018089).
The latter supports the forecast-error/window-statistics description; this is
not a claim to have reviewed all of that paper's supplementary experiments.
'''
    (ROOT/'paper/reports/TECHNICAL_METHODS.md').write_text(text,encoding='utf-8')


if __name__=='__main__':
    for zh in [False,True]:
        table(zh); comparisons(zh); protocol(zh)
    technical_methods()
    print('Rendered main tables, three-panel comparisons, paired-probe diagrams, and complete methods. No fits.')
