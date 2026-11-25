"""Dummy-coded conditional logit for complete choice tasks; pooled or segment fits."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp

META=['respondent_id','task_id','alternative_id','chosen','segment']
def demo_choices():
    rng=np.random.default_rng(51); rows=[]
    for r in range(120):
        seg='Efficacy focused' if r<60 else 'Safety focused'
        for t in range(12):
            x=rng.integers(0,3,(3,3)); beta=np.array([[0,.6,1.3],[0,-.4,-1.0],[0,.2,.5]]) if r<60 else np.array([[0,.3,.7],[0,-.8,-1.6],[0,.2,.5]])
            v=beta[np.arange(3),x].sum(axis=1); p=np.exp(v-logsumexp(v)); ch=rng.choice(3,p=p)
            for j,a in enumerate(x): rows.append([f'HCP{r+1:03}',str(t+1),str(j+1),int(j==ch),seg,*a])
    d=pd.DataFrame(rows,columns=META+['Efficacy','Adverse events','Administration'])
    for c,ls in zip(d.columns[5:],[['30%','45%','60%'],['10%','20%','30%'],['IV Q2W','IV Q4W','Oral daily']]): d[c]=d[c].map(dict(enumerate(ls)))
    return d

def fit_cbc(data,by_segment=False,holdout=.2,seed=42,ridge=.01):
    d=data.copy(); required=META[:4]
    if not set(required)<=set(d): raise ValueError('Required columns: '+', '.join(required))
    if 'segment' not in d: d['segment']='Overall'
    attrs=[c for c in d if c not in META]
    if not attrs or d.empty or d.isna().any().any(): raise ValueError('Supply complete choice rows and at least one attribute.')
    for c in ['respondent_id','task_id','alternative_id','segment']+attrs:
        d[c]=d[c].astype(str).str.strip()
        if (d[c]=='').any(): raise ValueError('Blank labels.')
    d['chosen']=pd.to_numeric(d.chosen,errors='raise')
    if not d.chosen.isin([0,1]).all() or d.duplicated(required[:3]).any(): raise ValueError('Chosen must be 0/1; alternatives must be unique within tasks.')
    if d.groupby('respondent_id').segment.nunique().max()!=1: raise ValueError('One segment per respondent required.')
    levels={a:sorted(d[a].unique()) for a in attrs}; cols=[(a,l) for a in attrs for l in levels[a][1:]]
    if not cols: raise ValueError('No varying attribute levels.')
    if not by_segment: d['segment']='Overall'
    rng=np.random.default_rng(seed); utilities=[]; metrics=[]; predictions=[]
    for seg,g in d.groupby('segment',sort=True):
        tasks=[]
        for (r,t),q in g.groupby(['respondent_id','task_id'],sort=True):
            if len(q)<2 or q.chosen.sum()!=1: raise ValueError(f'Task {r}/{t} must have >=2 alternatives and exactly one chosen.')
            x=np.column_stack([(q[a]==l).to_numpy(float) for a,l in cols]); y=q.chosen.to_numpy(float)
            tasks.append((r,t,q.alternative_id.to_numpy(),x,y))
        # Hold out complete tasks, stratified by respondent when possible.
        train=[]; test=[]
        for r in sorted(set(t[0] for t in tasks)):
            ts=[t for t in tasks if t[0]==r]; order=rng.permutation(len(ts)); n=min(len(ts)-1,max(1,round(len(ts)*holdout))) if holdout>0 and len(ts)>1 else 0
            test.extend(ts[i] for i in order[:n]); train.extend(ts[i] for i in order[n:])
        rank=np.linalg.matrix_rank(np.vstack([t[3]-t[3].mean(axis=0) for t in train]))
        if rank<len(cols): raise ValueError(f'{seg}: training design rank {rank}/{len(cols)}; levels are confounded or absent.')
        def objective(b):
            loss=ridge*np.dot(b,b)/2; grad=ridge*b.copy()
            for _,_,_,x,y in train:
                v=x@b; z=logsumexp(v); loss+=z-y@v; grad+=x.T@(np.exp(v-z)-y)
            return loss,grad
        res=minimize(objective,np.zeros(len(cols)),jac=True,method='L-BFGS-B',options={'maxiter':1000,'gtol':1e-7,'ftol':1e-12})
        if not res.success or not np.isfinite(res.x).all(): raise ValueError(f'Fit failed for {seg}: {res.message}')
        coef=dict(zip(cols,res.x)); nresp=g.respondent_id.nunique()
        utilities.extend(dict(segment=seg,weight=nresp,attribute=a,level=l,utility=coef.get((a,l),0.)) for a in attrs for l in levels[a])
        for split,ts in [('Train',train),('Holdout',test)]:
            if not ts: continue
            ll=0.; null=0.; hit=0.
            for r,t,ids,x,y in ts:
                v=x@res.x; lp=v-logsumexp(v); p=np.exp(lp); ll+=y@lp; null-=np.log(len(y)); winners=np.isclose(p,p.max(),rtol=0,atol=1e-12); hit+=y[winners].sum()/winners.sum()
                predictions.extend(dict(segment=seg,split=split,respondent_id=r,task_id=t,alternative_id=a,chosen=int(c),probability=pr) for a,c,pr in zip(ids,y,p))
            metrics.append(dict(segment=seg,split=split,tasks=len(ts),respondents=nresp,log_loss=-ll/len(ts),null_log_loss=-null/len(ts),hit_rate=hit/len(ts),mcfadden_r2=1-ll/null))
    return pd.DataFrame(utilities),pd.DataFrame(metrics),pd.DataFrame(predictions)
