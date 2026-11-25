"""Preference-share simulation using additive part-worth utilities and MNL."""
import numpy as np
import pandas as pd

ATTRIBUTES = {
    'Efficacy (response rate)': ['30%', '45%', '60%'],
    'Grade 3+ adverse events': ['10%', '20%', '30%'],
    'Administration': ['IV every 2 weeks', 'IV every 4 weeks', 'Oral daily'],
    'Monthly patient out-of-pocket cost': ['$0', '$100', '$300'],
}
SEGMENTS = {'Efficacy focused': (0.40, [[0, .7, 1.5],[.7,.35,0],[0,.2,.45],[.3,.15,0]]),
            'Safety focused': (0.35, [[0,.4,.85],[1.5,.7,0],[0,.2,.4],[.4,.2,0]]),
            'Convenience focused': (0.25, [[0,.4,.9],[.7,.35,0],[0,.55,1.25],[.5,.25,0]])}

def sample_utilities():
    return pd.DataFrame([dict(segment=s, weight=w, attribute=a, level=l, utility=u)
        for s,(w,values) in SEGMENTS.items() for (a,levels),us in zip(ATTRIBUTES.items(),values)
        for l,u in zip(levels,us)])

def sample_respondents():
    rng=np.random.default_rng(42)
    rows=[]
    for segment,(weight,values) in SEGMENTS.items():
        n=round(weight*200)
        for i in range(n):
            for (attribute,levels),utilities in zip(ATTRIBUTES.items(),values):
                for level,u in zip(levels,utilities):
                    rows.append(dict(respondent_id=f'{segment}-{i+1:03}',segment=segment,weight=1,attribute=attribute,level=level,utility=u+rng.normal(0,.45)))
    return pd.DataFrame(rows)

def validate(df):
    cols=['segment','weight','attribute','level','utility']
    if 'respondent_id' in df.columns: cols=['respondent_id']+cols
    if not set(cols).issubset(df.columns): raise ValueError('Required columns: '+', '.join(cols))
    df=df[cols].copy()
    if df.empty or df.isna().any().any(): raise ValueError('Missing values or empty data.')
    unit='respondent_id' if 'respondent_id' in df else 'segment'
    for c in set([unit,'segment','attribute','level']):
        df[c]=df[c].astype(str).str.strip()
        if (df[c]=='').any(): raise ValueError('Blank labels are not allowed.')
    for c in ['weight','utility']:
        df[c]=pd.to_numeric(df[c],errors='raise')
        if not np.isfinite(df[c]).all(): raise ValueError('Utilities and weights must be finite.')
    if df.duplicated([unit,'attribute','level']).any(): raise ValueError('Duplicate unit / attribute / level rows.')
    grouped=df.groupby(unit)
    if (df.weight<0).any() or grouped.weight.nunique().max()!=1 or grouped.segment.nunique().max()!=1: raise ValueError('Each unit needs one nonnegative weight and one segment.')
    if grouped.weight.first().sum()<=0: raise ValueError('Total weight must be positive.')
    keys=set(zip(df.attribute,df.level))
    for _,g in grouped:
        if set(zip(g.attribute,g.level))!=keys: raise ValueError('Every unit must contain the same attribute levels.')
    return df

def individual_shares(df,profiles,constants=None):
    df=validate(df)
    unit='respondent_id' if 'respondent_id' in df else 'segment'
    if len(profiles)<2: raise ValueError('Provide at least two alternatives.')
    attrs=set(df.attribute)
    matrix=df.pivot(index=unit,columns=['attribute','level'],values='utility')
    meta=df.groupby(unit)[['segment','weight']].first().reindex(matrix.index)
    vals=[]
    for name,p in profiles.items():
        if set(p)!=attrs: raise ValueError('Every product needs exactly one level per attribute.')
        try: vals.append(matrix[list(p.items())].sum(axis=1).to_numpy())
        except KeyError as e: raise ValueError('Unknown attribute/level') from e
    v=np.column_stack(vals)
    if constants is not None:
        adjustment=constants.reindex(index=matrix.index,columns=list(profiles)).to_numpy(dtype=float)
        if not np.isfinite(adjustment).all(): raise ValueError('Missing or invalid calibration constants')
        v=v+adjustment
    e=np.exp(v-v.max(axis=1,keepdims=True)); probs=e/e.sum(axis=1,keepdims=True)
    result=pd.DataFrame(probs,index=matrix.index,columns=list(profiles))
    result=result.join(meta.rename(columns={'segment':'_segment','weight':'_weight'})).reset_index()
    if unit=='segment': result=result.drop(columns='segment').rename(columns={'_segment':'segment'})
    else: result=result.rename(columns={'_segment':'segment'})
    result=result.rename(columns={'_weight':'weight'})
    return result.melt(id_vars=[unit,'weight']+(['segment'] if unit!='segment' else []),value_vars=list(profiles),var_name='product',value_name='share')

def shares(df,profiles,constants=None):
    rows=individual_shares(df,profiles,constants)
    rows['weighted']=rows.share*rows.weight
    totals=rows.groupby('product',sort=False).agg(weighted=('weighted','sum'),weight=('weight','sum'))
    overall=(totals.weighted/totals.weight).rename('share')
    detail=rows.groupby(['segment','product'],sort=False).agg(weighted=('weighted','sum'),weight=('weight','sum')).reset_index()
    detail=detail[detail.weight>0].copy()
    detail['share']=detail.weighted/detail.weight
    detail['weight']/=totals.weight.iloc[0]
    return overall,detail[['segment','product','share','weight']]

def importance(df):
    df=validate(df)
    unit='respondent_id' if 'respondent_id' in df else 'segment'
    ranges=df.groupby([unit,'attribute']).utility.agg(lambda x:x.max()-x.min())
    totals=ranges.groupby(level=0).transform('sum')
    imp=(ranges/totals.replace(0,np.nan)).rename('importance').reset_index()
    if unit=='segment': return imp
    imp=imp.merge(df.groupby(unit)[['segment','weight']].first(),on=unit)
    imp=imp.dropna(subset=['importance']); imp['weighted']=imp.importance*imp.weight
    out=imp.groupby(['segment','attribute']).agg(weighted=('weighted','sum'),weight=('weight','sum')).reset_index()
    out=out[out.weight>0]; out['importance']=out.weighted/out.weight
    return out[['segment','attribute','importance']]
