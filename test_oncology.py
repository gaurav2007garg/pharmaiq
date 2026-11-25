from oncology import search, flatten, demo, milestones
import pandas as pd
import pytest

def record(n): return {'protocolSection':{'identificationModule':{'nctId':n},'statusModule':{'primaryCompletionDateStruct':{'date':'2027-01','type':'ESTIMATED'}}}}
def test_parse():
    r=flatten(record('NCT123')); assert r['Primary completion']=='2027-01' and r['Date type']=='ESTIMATED' and r['Source'].endswith('NCT123')
def test_pages():
    def fetch(p):
        return {'studies':[record('NCT2')],'totalCount':2} if 'pageToken' in p else {'studies':[record('NCT1')],'nextPageToken':'abc','totalCount':2}
    d,m=search(condition='cancer',fetch=fetch); assert len(d)==2 and not m['Potentially truncated']
def test_cap():
    d,m=search(condition='cancer',limit=1,fetch=lambda p:{'studies':[record('NCT1')],'totalCount':5,'nextPageToken':'abc'}); assert len(d)==1 and m['Potentially truncated']
def test_empty():
    with pytest.raises(ValueError): search()
def test_milestones():
    d,_=demo(); m=milestones(d,24); assert len(m)==3 and 'COMPLETED' not in set(m.Status)
def test_missing():
    d,m=search(term='x',fetch=lambda p:{'studies':[],'totalCount':0}); assert d.empty and m['Retrieved']==0
