"""Registry search and transparent descriptive intelligence."""
import json
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
import pandas as pd
from ci_enrich import arm_roles
API='https://clinicaltrials.gov/api/v2/studies'
COLS=['NCT ID','Title','Sponsor','Conditions','Interventions','Phase','Status','Study type','Enrollment','Enrollment type','Primary completion','Date type','Study completion','Last update','Primary outcomes','Results posted','Source','Arm mapping','Brief summary','Eligibility criteria']
def flatten(study):
    p=study.get('protocolSection',{}); i=p.get('identificationModule',{}); s=p.get('statusModule',{}); d=p.get('designModule',{}); a=p.get('armsInterventionsModule',{}); o=p.get('outcomesModule',{}); n=i.get('nctId',''); pc=s.get('primaryCompletionDateStruct',{})
    return dict(zip(COLS,[n,i.get('briefTitle',''),p.get('sponsorCollaboratorsModule',{}).get('leadSponsor',{}).get('name',''),'; '.join(p.get('conditionsModule',{}).get('conditions',[])),'; '.join(x.get('name','') for x in a.get('interventions',[])), ' / '.join(d.get('phases',[])) or 'Not specified',s.get('overallStatus','Unknown'),d.get('studyType',''),d.get('enrollmentInfo',{}).get('count'),d.get('enrollmentInfo',{}).get('type',''),pc.get('date',''),pc.get('type',''),s.get('completionDateStruct',{}).get('date',''),s.get('lastUpdatePostDateStruct',{}).get('date',''),'; '.join(x.get('measure','') for x in o.get('primaryOutcomes',[])),bool(study.get('hasResults',False)),f'https://clinicaltrials.gov/study/{n}' if n else '',json.dumps(arm_roles(a)),p.get('descriptionModule',{}).get('briefSummary',''),p.get('eligibilityModule',{}).get('eligibilityCriteria','')]))
def get_json(params):
    with urlopen(API+'?'+urlencode(params),timeout=30) as response: return json.load(response)
def search(condition='',intervention='',sponsor='',term='',limit=500,fetch=get_json):
    if not any(x.strip() for x in (condition,intervention,sponsor,term)): raise ValueError('Enter at least one search criterion.')
    if not 1<=limit<=2000: raise ValueError('Limit must be 1–2000.')
    params={'format':'json','countTotal':'true','pageSize':min(100,limit)}
    params.update({k:v.strip() for k,v in zip(['query.cond','query.intr','query.spons','query.term'],[condition,intervention,sponsor,term]) if v.strip()})
    rows={}; total=None; seen=set()
    while len(rows)<limit:
        data=fetch(params.copy()); total=data.get('totalCount',total)
        for study in data.get('studies',[]):
            row=flatten(study)
            if row['NCT ID']: rows[row['NCT ID']]=row
            if len(rows)>=limit: break
        token=data.get('nextPageToken')
        if not token: break
        if token in seen: raise RuntimeError('Repeated pagination token; search incomplete.')
        seen.add(token); params['pageToken']=token; params['pageSize']=min(100,limit-len(rows))
    return pd.DataFrame(rows.values(),columns=COLS), {'Registry total':total,'Retrieved':len(rows),'Limit':limit,'Retrieved UTC':datetime.now(timezone.utc).isoformat(),'Query':str({k:v for k,v in params.items() if k.startswith('query.')}),'Potentially truncated': bool(token) or (total is not None and total>len(rows))}
def milestones(df, months=24, today=None):
    today=pd.Timestamp(today or date.today()).normalize(); end=today+pd.DateOffset(months=months)
    out=df.copy(); out['Milestone month']=pd.to_datetime(out['Primary completion'].str.slice(0,7),format='%Y-%m',errors='coerce')
    active=out.Status.isin(['RECRUITING','ACTIVE_NOT_RECRUITING','NOT_YET_RECRUITING','ENROLLING_BY_INVITATION'])
    return out[active & out['Milestone month'].between(today.replace(day=1),end.replace(day=1))].sort_values('Milestone month')
def demo():
    rows=[]
    for k,(asset,phase,status,month) in enumerate([('Asset Alpha','PHASE3','RECRUITING',4),('Asset Beta','PHASE2','ACTIVE_NOT_RECRUITING',9),('Asset Gamma','PHASE3','NOT_YET_RECRUITING',16),('Asset Alpha','PHASE2','COMPLETED',-3),('Asset Delta','PHASE1','RECRUITING',25)]):
        row=dict.fromkeys(COLS,''); row.update({'NCT ID':f'DEMO-{k+1}','Title':f'Fictional oncology study {k+1}','Sponsor':f'Synthetic Sponsor {k%3+1}','Conditions':'Synthetic lung cancer','Interventions':asset,'Phase':phase,'Status':status,'Study type':'INTERVENTIONAL','Enrollment':100*(k+1),'Primary completion':(pd.Timestamp.today()+pd.DateOffset(months=month)).strftime('%Y-%m'),'Date type':'ESTIMATED','Results posted':False,'Arm mapping':json.dumps([{'Asset':asset,'Registry intervention':asset,'Arm role':'Experimental arm','Arm evidence':'Fictional experimental arm','Role caveat':'Synthetic'}])}); rows.append(row)
    return pd.DataFrame(rows,columns=COLS),{'Mode':'SYNTHETIC — not real clinical evidence','Retrieved':len(rows)}
