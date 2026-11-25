from ci_enrich import arm_roles, enrich_frame, asset_rows, phase_matrix, canonical_asset
from oncology import demo, flatten

def test_roles():
    a={'armGroups':[{'label':'a','type':'EXPERIMENTAL'},{'label':'b','type':'ACTIVE_COMPARATOR'}],'interventions':[{'name':'pembrolizumab','type':'DRUG','armGroupLabels':['a','b']},{'name':'X','type':'DRUG','armGroupLabels':['b']},{'name':'Y','type':'BIOLOGICAL','armGroupLabels':[]}]}
    r=arm_roles(a); assert [x['Arm role'] for x in r]==['Both','Comparator arm','Unclear']; assert r[0]['Asset']=='Keytruda'
def test_alias(): assert canonical_asset('pembrolizumab/vibostolimab')=='pembrolizumab/vibostolimab'
def test_activity():
    d,_=demo(); f=enrich_frame(d); assert (f['Development status']=='Active / planned').sum()==4

def test_matrix():
    d,_=demo(); a=asset_rows(d); assert len(a)==5 and phase_matrix(a).sum().sum()==5

def test_unique():
    import pandas as pd
    d,_=demo(); a=asset_rows(d); assert phase_matrix(pd.concat([a,a])).sum().sum()==5

def test_benchmark():
    import pandas as pd
    from ci_enrich import benchmark_assets
    a=pd.DataFrame({'Asset':['A','A','A','B'],'Phase':['PHASE2 / PHASE3','PHASE2 / PHASE3','PHASE3','PHASE1'],'NCT ID':['1','1','2','3']})
    m=benchmark_assets(a,['B','A']); assert list(m.index)==['B','A']; assert m.loc['A','Unique studies']==2; assert m.loc['A','PHASE3']==2; assert m.loc['A','PHASE2']==1
