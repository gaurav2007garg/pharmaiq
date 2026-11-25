from simulator import shares
import pandas as pd

def tornado(df,profiles,product,constants=None):
    base=shares(df,profiles,constants)[0][product]; rows=[]
    for a,g in df.groupby('attribute',sort=False):
        for l in g.level.unique():
            p={k:v.copy() for k,v in profiles.items()}; p[product][a]=l
            s=shares(df,p,constants)[0][product]
            rows.append(dict(attribute=a,level=l,reference_level=profiles[product][a],share=s,delta_pp=100*(s-base)))
    detail=pd.DataFrame(rows); summary=[]
    for a,g in detail.groupby('attribute',sort=False):
        lo=g.loc[g.delta_pp.idxmin()]; hi=g.loc[g.delta_pp.idxmax()]
        summary.append(dict(attribute=a,low=lo.delta_pp,high=hi.delta_pp,low_level=lo.level,high_level=hi.level,span=hi.delta_pp-lo.delta_pp))
    return base,pd.DataFrame(summary).sort_values('span'),detail
