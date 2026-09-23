"""Offline manuscript contrasts and vector figures; never fits a model.

Exploratory family fixed in this script before computing intervals:
all three pairs in the previously discussed POLY/MOMENT-FT/MOMENT-ZS trio,
under all three matched probes. No selection by interval outcome.
"""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/evidence/paired_contrasts'
PAIRS = [('POLY', 'MOMENT_FT'), ('POLY', 'MOMENT_ZS'), ('MOMENT_FT', 'MOMENT_ZS')]
PROBES = ['linear', 'spline', 'hgb']
STYLE = {'SubPCA':('#6E8FB2','o'), 'POLY':('#7DA494','s'),
         'MOMENT_FT':('#EAB67A','^'), 'MOMENT_ZS':('#9F8DB8','v'),
         'M2N2':('#C16E71','D'), 'TranAD':('#78B6C8','P'),
         'TimesNet':('#D8ACC1','X'), 'FITS':('#98AF1E','h'),
         'AnomalyTransformer':('#E5A79A','*')}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = ROOT/'paper/evidence/source_inference/SOURCE_CDU_MATRIX.csv'
    x = pd.read_csv(src, index_col=0).sort_index()
    assert len(x)==23 and x.index.is_unique and np.isfinite(x.to_numpy()).all()
    arrays = [x[f'{p}/{a}'].to_numpy()-x[f'{p}/{b}'].to_numpy()
              for p in PROBES for a,b in PAIRS]
    values = np.column_stack(arrays)
    rng = np.random.default_rng(2024)
    draws = rng.integers(0,23,(20000,23))
    means = values.mean(0)
    boots = values[draws].mean(1)
    se = values.std(0,ddof=1)/np.sqrt(23)
    assert (se>0).all()
    q = np.quantile(np.max(np.abs((boots-means)/se),axis=1), .95)
    rows = []
    for j,(p,a,b) in enumerate((p,a,b) for p in PROBES for a,b in PAIRS):
        lo,hi = np.quantile(boots[:,j],[.025,.975])
        rows.append(dict(probe=p,detector_A=a,detector_B=b,delta_CDU=means[j],
            ci_low=lo,ci_high=hi,simultaneous9_low=means[j]-q*se[j],
            simultaneous9_high=means[j]+q*se[j],n_sources=23,
            positive_sources=int((values[:,j]>0).sum())))
    result = pd.DataFrame(rows)
    result.to_csv(OUT/'PAIRED_CDU_CONTRASTS.csv',index=False)
    pd.DataFrame(values,index=x.index,columns=[f'{r["probe"]}/{r["detector_A"]}-{r["detector_B"]}' for r in rows]).to_csv(OUT/'SOURCE_DELTAS.csv')
    (OUT/'METHOD.json').write_text(json.dumps(dict(
        exploratory=True,pairs=PAIRS,probes=PROBES,seed=2024,resamples=20000,
        input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        interval='paired source percentile; plus joint nine-contrast centered max-standardized bootstrap',
        limitation='Conditional on saved OOF fits; source dependence and overlapping training are not removed.'),indent=2),encoding='utf-8')
    print(result.to_string(index=False))
    raw = pd.read_csv(ROOT/'paper/evidence/fast_main/MAIN_RESULTS.csv').set_index('Detector')
    det = pd.read_csv(ROOT/'paper/evidence/rank_probe_extension/DETECTORS.csv').set_index(['probe','detector'])
    util = pd.read_csv(ROOT/'paper/evidence/cdu_followup/DETECTOR_ONLY_VS_CDU.csv').set_index(['probe','detector'])
    for zh in [False,True]:
        caption = ('冻结分数的统一来源留出评价。Raw/Raw$_s$ 为序列/来源宏平均 VUS。其余列为比特：全量训练线性 CDU（Full），以及匹配 2048 点上限训练的线性（Lin）、spline（Spl）、HGB CDU；$U_D$ 使用匹配 spline。加粗仅表示未校正来源区间为正。' if zh else
            'Source-held-out evaluation of frozen scores. Raw/Raw$_s$: series/source-macro VUS. Utilities are in bits: full-data linear CDU (Full), matched cap-2048 linear (Lin), spline (Spl), and HGB CDU; $U_D$ uses matched spline. Bold marks positive unadjusted source intervals only.')
        table = [r'\begin{table*}[t]',r'\centering',r'\small',r'\caption{'+caption+'}',
                 r'\label{tab:main}',r'\setlength{\tabcolsep}{5pt}',r'\begin{tabular}{cccccccc}',r'\toprule',
                 r'Detector & Raw & Raw$_s$ & $U_D$ (Spl) & CDU (Full) & CDU (Lin) & CDU (Spl) & CDU (HGB) \\',r'\midrule']
        for d in STYLE:
            vals = [f'{raw.loc[d,"Raw_VUS"]:.4f}',f'{raw.loc[d,"Source_macro_Raw_VUS"]:.4f}',
                    f'{util.loc[("spline",d),"detector_utility"]:.5f}',f'{raw.loc[d,"CDU"]:.5f}']
            for p in PROBES:
                row = det.loc[(p,d)]
                v = f'{row.CDU:.5f}'
                vals.append(r'\textbf{'+v+'}' if row.CI_low>0 else v)
            table.append(d.replace('_','-')+' & '+' & '.join(vals)+r' \\')
        table += [r'\bottomrule',r'\end{tabular}',r'\end{table*}']
        suffix = '_zh' if zh else ''
        (ROOT/f'icassp/tables/unified_results{suffix}.tex').write_text('\n'.join(table)+'\n',encoding='utf-8')
        plt.rcParams.update({'font.family':'Microsoft YaHei' if zh else 'DejaVu Serif','font.size':8,
                             'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        fig,(a,b) = plt.subplots(1,2,figsize=(7.05,2.85),gridspec_kw={'width_ratios':[1,1.05]})
        fig.subplots_adjust(left=.08,right=.985,bottom=.29,top=.91,wspace=.75)
        for d,(c,m) in STYLE.items():
            r = util.loc[('spline',d)]
            a.scatter(r.detector_utility,r.CDU,s=40,marker=m,color=c,edgecolors='#555555',linewidths=.45,zorder=3)
        a.set(xlim=(-.003,.045),ylim=(-.0015,.0175),xlabel='$U_D$ (bits)',ylabel='CDU (bits)')
        a.set_title('(a) 相同损失，不同评价问题' if zh else '(a) Same loss, different questions',fontsize=8.5,loc='left')
        a.text(.03,.94,r'Spline: $\rho=0.667$',transform=a.transAxes,va='top',fontsize=7.5,color='#555555')
        a.set_xticks([0,.01,.02,.03,.04])
        a.set_yticks([0,.005,.01,.015])
        ranks = det['CDU'].unstack('probe')[PROBES].rank(ascending=False)
        b.axhspan(.5,4.5,color='#78B6C8',alpha=.10,zorder=0)
        for d,(c,m) in STYLE.items():
            b.plot(range(3),ranks.loc[d],marker=m,color=c,markersize=5,
                   linewidth=1.1,markeredgecolor='#555555',markeredgewidth=.35)
        b.set_xticks(range(3),['Linear','Spline','HGB'])
        b.set_yticks(range(1,10))
        b.set(ylim=(9.6,.4),xlim=(-.2,2.2),ylabel='CDU 排名' if zh else 'CDU rank')
        b.set_title('(b) 跨探针排名稳定性' if zh else '(b) Rank stability across probes',fontsize=8.5,loc='left')
        handles = [Line2D([],[],linestyle='none',marker=m,color=c,label=d.replace('_','-'),markersize=5)
                   for d,(c,m) in STYLE.items()]
        fig.legend(handles=handles,loc='lower center',ncol=5,frameon=False,fontsize=7,
                   columnspacing=1,handletextpad=.4,bbox_to_anchor=(.5,.005))
        target = ROOT/f'icassp/figures/conditional_comparison{suffix}'
        fig.savefig(target.with_suffix('.pdf'),bbox_inches='tight',pad_inches=.04)
        fig.savefig(target.with_suffix('.png'),dpi=180,bbox_inches='tight',pad_inches=.04)
        plt.close(fig)

if __name__=='__main__':
    main()
