import numpy as np
import pandas as pd
import pytest
from simulator import sample_respondents, ATTRIBUTES, shares, individual_shares
from calibration import fit_constants
from audit_export import build_audit
from openpyxl import load_workbook
from io import BytesIO

@pytest.fixture
def setup():
    df=sample_respondents(); profiles={p:{a:l[i] for a,l in ATTRIBUTES.items()} for i,p in enumerate(['A','B','C'])}; return df,profiles

@pytest.mark.parametrize('mode',['Overall','Segment','Respondent'])
def test_fit(setup,mode):
    df,p=setup; groups=['Overall'] if mode=='Overall' else df.segment.unique() if mode=='Segment' else df.respondent_id.unique()
    t=pd.DataFrame([(g,k,v) for g in groups for k,v in zip(p,[.5,.3,.2])],columns=['group','product','target']); a,d=fit_constants(df,p,t,mode)
    assert d.residual.abs().max()<1e-9
    assert np.allclose(shares(df,p,a)[0],[.5,.3,.2],atol=1e-9)
    assert np.allclose(a.iloc[:,0],0)
    assert np.allclose(shares(df[df.segment==df.segment.iloc[0]],p,a)[0].sum(),1)

def test_zero_and_scenario_audit(setup):
    df,p=setup; t=pd.DataFrame({'group':'Overall','product':list(p),'target':[.6,.4,0]}); a,d=fit_constants(df,p,t)
    assert d.effective_target.min()>0
    q={k:v.copy() for k,v in p.items()}; q['C'][list(ATTRIBUTES)[0]]='30%'
    assert not np.allclose(shares(df,p,a)[0],shares(df,q,a)[0])
    wb=load_workbook(BytesIO(build_audit(df,p,q,a,d)))
    assert 'Calibration constants' in wb.sheetnames
    assert 'Calibration fit' in wb.sheetnames
    assert any('Calibration constants' in str(c.value) for c in wb['Baseline calc'][2])

def test_invalid(setup):
    df,p=setup; t=pd.DataFrame({'group':'Overall','product':list(p),'target':[.6,.4,.1]})
    with pytest.raises(ValueError): fit_constants(df,p,t)
