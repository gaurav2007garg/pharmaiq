import pandas as pd
import numpy as np
import pytest
from simulator import sample_utilities, shares, validate, importance, ATTRIBUTES

def profile(i): return {a:ls[i] for a,ls in ATTRIBUTES.items()}
def test_equal_profiles():
    s,d=shares(sample_utilities(),{'A':profile(0),'B':profile(0)})
    assert np.allclose(s,.5); assert np.allclose(d.groupby('segment').share.sum(),1)
def test_monotonic_efficacy():
    a=profile(0); b=a.copy(); b['Efficacy (response rate)']='60%'
    s,_=shares(sample_utilities(),{'A':a,'B':b}); assert s.B>s.A

def test_manual_logit():
    df=pd.DataFrame([['s',1,'a','x',0],['s',1,'a','y',np.log(3)]],columns=['segment','weight','attribute','level','utility'])
    s,_=shares(df,{'A':{'a':'x'},'B':{'a':'y'}}); assert np.isclose(s.B,.75)
def test_weighting():
    df=pd.DataFrame([['s1',3,'a','x',0],['s1',3,'a','y',np.log(3)],['s2',1,'a','x',np.log(3)],['s2',1,'a','y',0]],columns=['segment','weight','attribute','level','utility'])
    s,_=shares(df,{'A':{'a':'x'},'B':{'a':'y'}}); assert np.isclose(s.B,.625)
def test_invalid_duplicate():
    df=sample_utilities();
    with pytest.raises(ValueError): validate(pd.concat([df,df.iloc[:1]]))
def test_missing_level():
    with pytest.raises(ValueError): validate(sample_utilities().iloc[1:])
def test_importance():
    assert np.allclose(importance(sample_utilities()).groupby('segment').importance.sum(),1)
def test_large_utilities():
    df=sample_utilities(); df.utility*=10000; s,_=shares(df,{'A':profile(0),'B':profile(2)}); assert np.isfinite(s).all() and np.isclose(s.sum(),1)

def test_respondent_nonlinearity_and_weights():
    from simulator import individual_shares
    df=pd.DataFrame([['r1','s',3,'a','x',0],['r1','s',3,'a','y',0],['r2','s',1,'a','x',0],['r2','s',1,'a','y',np.log(9)]],columns=['respondent_id','segment','weight','attribute','level','utility'])
    p={'A':{'a':'x'},'B':{'a':'y'}}
    s,d=shares(df,p)
    assert np.isclose(s.B,.6) and np.isclose(d.loc[d['product']=='B','share'].iloc[0],.6)
    assert not np.isclose(s.B, 1/(1+np.exp(-np.log(9)/4)))
    assert np.allclose(individual_shares(df,p).groupby('respondent_id').share.sum(),1)
def test_respondent_sample():
    from simulator import sample_respondents
    df=sample_respondents(); assert df.respondent_id.nunique()==200
    s,d=shares(df,{'A':profile(0),'B':profile(0)}); assert np.allclose(s,.5)
    assert np.allclose(importance(df).groupby('segment').importance.sum(),1)
def test_respondent_validation():
    from simulator import sample_respondents
    df=sample_respondents(); df.loc[0,'weight']=2
    with pytest.raises(ValueError): validate(df)
def test_filter_population():
    from simulator import sample_respondents
    df=sample_respondents(); p={'A':profile(0),'B':profile(2)}
    s,d=shares(df[df.segment=='Safety focused'],p)
    assert len(d)==2 and np.isclose(s.sum(),1) and np.allclose(d.share,s.values)
