"""Exploratory source-level inference on saved OOF losses; no refitting."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp
from evaluate_cdu_protocol_v1 import DETECTORS, load_source_map

ROOT=Path(__file__).resolve().parents[1]


def holm(p):
    p=np.asarray(p); order=np.argsort(p); out=np.empty(len(p))
    out[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return out


def main():
    output=ROOT/'paper/evidence/source_inference'
    output.mkdir(parents=True,exist_ok=True)
    sources=sorted(set(load_source_map().values()))
    columns,arrays=[],[]
    for probe in ['linear','spline','hgb']:
        for d in DETECTORS:
            f=pd.read_csv(ROOT/'protocol_rank_probe_results/cap2048'/probe/d/'PER_SERIES.csv')
            np.testing.assert_allclose(f.CDU,f.L_basis-f.L_basis_detector,atol=1e-14,rtol=0)
            v=f.groupby('source_dataset').CDU.mean().reindex(sources).to_numpy()
            assert len(v)==23 and np.isfinite(v).all()
            columns.append((probe,d)); arrays.append(v)
    x=np.column_stack(arrays); mean=x.mean(axis=0); se=x.std(axis=0,ddof=1)/np.sqrt(23)
    assert (se>0).all()
    rng=np.random.default_rng(2024)
    draws=rng.integers(0,23,(20000,23))
    boot=x[draws].mean(axis=1)
    z=np.abs((boot-mean)/se)
    q27=np.quantile(z.max(axis=1),.95)
    rawp=ttest_1samp(x,0,axis=0,alternative='greater').pvalue
    adjusted27=holm(rawp)
    records,influence=[],[]
    for j,(probe,d) in enumerate(columns):
        group=np.array([i for i,c in enumerate(columns) if c[0]==probe])
        q9=np.quantile(z[:,group].max(axis=1),.95)
        h9=holm(rawp[group])[np.flatnonzero(group==j)[0]]
        loo=(x[:,j].sum()-x[:,j])/22
        records.append(dict(probe=probe,detector=d,CDU=mean[j],
            simultaneous9_low=mean[j]-q9*se[j],simultaneous9_high=mean[j]+q9*se[j],
            simultaneous27_low=mean[j]-q27*se[j],simultaneous27_high=mean[j]+q27*se[j],
            exploratory_t_p_greater=rawp[j],holm9_p=h9,holm27_p=adjusted27[j],
            delete_source_min=loo.min(),delete_source_max=loo.max(),
            delete_source_positive_count=int((loo>0).sum()),
            most_influential_source=sources[int(np.argmax(np.abs(loo-mean[j])))]))
        for source,value in zip(sources,loo):
            influence.append(dict(probe=probe,detector=d,omitted_source=source,mean_without_source=value,
                                  change_from_full=value-mean[j]))
    result=pd.DataFrame(records)
    result.to_csv(output/'MULTIPLICITY.csv',index=False)
    pd.DataFrame(influence).to_csv(output/'SOURCE_INFLUENCE.csv',index=False)
    pd.DataFrame(x,index=sources,columns=[f'{p}/{d}' for p,d in columns]).to_csv(output/'SOURCE_CDU_MATRIX.csv')
    report=['# Source-level multiplicity and influence sensitivity','',
      'This is exploratory inference conditional on the saved OOF losses. It does not refit probes.',
      'All detectors/probes share each bootstrap source draw. Simultaneous intervals use the 95th percentile of the maximum absolute centered bootstrap mean deviation divided by its original source standard error. Both nine-detector families within probe and the joint 27-comparison family are reported.',
      'One-sided source t-tests and Holm adjustment are sensitivity analyses: they assume independent source observations and an adequate t approximation. Shared LOSO training sets violate strict independence; neither Holm nor resampling fixes that dependence. These are not unconditional type-I-error guarantees.',
      'The source-deletion analysis removes one source from aggregation, without retraining. It measures evaluation influence, not the effect of removing that source from model training.',
      'Method reference: [SciPy one-sample t-test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_1samp.html).','',
      result.to_markdown(index=False,floatfmt='.6g'),'']
    (output/'METHODS_AND_RESULTS.md').write_text('\n'.join(report),encoding='utf-8')
    print(result[['probe','detector','CDU','simultaneous27_low','holm27_p','delete_source_positive_count']].to_string(index=False))


if __name__=='__main__': main()
