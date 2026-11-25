import numpy as np
import pytest
from cbc import demo_choices,fit_cbc
from simulator import sample_utilities,ATTRIBUTES,validate,shares
from tornado import tornado

def test_cbc_pooled():
    u,m,p=fit_cbc(demo_choices()); validate(u)
    assert set(m.split)=={'Train','Holdout'}
    assert np.allclose(p.groupby(['respondent_id','task_id']).probability.sum(),1)
    assert (p.groupby(['respondent_id','task_id']).split.nunique()==1).all()
    assert m.loc[m.split=='Holdout','log_loss'].iloc[0]<m.loc[m.split=='Holdout','null_log_loss'].iloc[0]
    assert u.query("attribute=='Efficacy' and level=='60%'").utility.iloc[0]>0

def test_cbc_segments():
    u,m,p=fit_cbc(demo_choices(),True); validate(u)
    assert u.segment.nunique()==2
    assert set(u.weight)=={60}

def test_bad_task():
    d=demo_choices(); d.loc[:2,'chosen']=0
    with pytest.raises(ValueError,match='exactly one'): fit_cbc(d)

def test_tornado():
    d=sample_utilities(); p={k:{a:ls[i] for a,ls in ATTRIBUTES.items()} for i,k in enumerate(['A','B','C'])}
    ref,s,detail=tornado(d,p,'A'); assert np.isclose(ref,shares(d,p)[0]['A'])
    assert len(detail)==12 and len(s)==4
    assert np.allclose(detail[detail.level==detail.reference_level].delta_pp,0)
    assert (s.low<=0).all() and (s.high>=0).all()
    assert s.span.is_monotonic_increasing
