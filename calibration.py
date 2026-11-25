"""Fixed alternative-specific constants for weighted MNL calibration."""
import numpy as np
import pandas as pd
from simulator import individual_shares, validate

def fit_constants(df, baseline, targets, granularity='Overall', smoothing=0.001):
    """Targets use fractions, with one complete row per group and product.
    Smoothing is a uniform mixture, applied only to rows containing zeros.
    """
    df=validate(df); unit='respondent_id' if 'respondent_id' in df else 'segment'
    if granularity not in ('Overall','Segment','Respondent'): raise ValueError('Unknown granularity')
    if granularity=='Respondent' and unit!='respondent_id': raise ValueError('Respondent data required')
    if not 0<smoothing<1: raise ValueError('Smoothing must be between zero and one')
    rows=individual_shares(df,baseline); products=list(baseline)
    raw=rows.pivot(index=unit,columns='product',values='share')[products]
    meta=df.groupby(unit)[['segment','weight']].first().reindex(raw.index)
    groups=pd.Series('Overall',index=raw.index) if granularity=='Overall' else (meta.segment if granularity=='Segment' else pd.Series(raw.index,index=raw.index))
    t=targets.copy(); required=['group','product','target']
    if not set(required)<=set(t): raise ValueError('Required columns: group, product, target')
    t=t[required]; t['group']=t.group.astype(str).str.strip(); t['product']=t['product'].astype(str).str.strip(); t['target']=pd.to_numeric(t.target,errors='raise')
    if t.duplicated(['group','product']).any() or not np.isfinite(t.target).all() or (t.target<0).any(): raise ValueError('Invalid or duplicate targets')
    if set(zip(t.group,t['product']))!={(g,p) for g in groups.unique() for p in products}: raise ValueError('Targets must cover exactly every group and product')
    target=t.pivot(index='group',columns='product',values='target')[products]
    if not np.allclose(target.sum(axis=1),1,atol=1e-8,rtol=0): raise ValueError('Each group must sum to 1 (fractions, not percentages)')
    target=target.div(target.sum(axis=1),axis=0); effective=target.copy(); mask=(target==0).any(axis=1); effective.loc[mask]=(1-smoothing)*target.loc[mask]+smoothing/len(products)
    constants=pd.DataFrame(0.,index=raw.index,columns=products); diagnostics=[]
    for g in groups.unique():
        ix=groups.index[groups==g]; w=meta.loc[ix,'weight'].to_numpy(); p=raw.loc[ix].to_numpy(); q=effective.loc[g].to_numpy()
        if (p<=0).any(): raise ValueError('Baseline probability underflow; rescale extreme utilities')
        logp=np.log(p)
        if granularity=='Respondent' or len(ix)==1: a=np.log(q)-logp[0]
        else:
            if w.sum()<=0: raise ValueError(f'Group {g} has zero total weight')
            a=np.zeros(len(products))
            for _ in range(10000):
                z=logp+a; e=np.exp(z-z.max(axis=1,keepdims=True)); pred=np.average(e/e.sum(axis=1,keepdims=True),axis=0,weights=w)
                if np.max(np.abs(pred-q))<1e-10: break
                a+=np.log(q)-np.log(pred); a-=a[0]
            else: raise ValueError(f'Calibration did not converge for {g}')
        a-=a[0]; constants.loc[ix]=a
        z=logp+a; e=np.exp(z-z.max(axis=1,keepdims=True)); prob=e/e.sum(axis=1,keepdims=True); fitted=np.average(prob,axis=0,weights=w) if w.sum()>0 else prob[0]
        for j,pname in enumerate(products): diagnostics.append(dict(group=g,product=pname,target=target.loc[g,pname],effective_target=q[j],fitted=fitted[j],residual=fitted[j]-q[j]))
    return constants,pd.DataFrame(diagnostics)
