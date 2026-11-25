"""Conservative registry-arm classification and commercial views."""
import re
import json
import pandas as pd
ACTIVE={'RECRUITING','ACTIVE_NOT_RECRUITING','NOT_YET_RECRUITING','ENROLLING_BY_INVITATION'}
ALIASES={'Merck Sharp & Dohme LLC':'Merck','Merck Sharp & Dohme Corp.':'Merck','Hoffmann-La Roche':'Roche','Bristol-Myers Squibb':'Bristol Myers Squibb'}
DRUGS={'pembrolizumab':'Keytruda','keytruda':'Keytruda','nivolumab':'Opdivo','opdivo':'Opdivo','durvalumab':'Imfinzi','imfinzi':'Imfinzi','atezolizumab':'Tecentriq','tecentriq':'Tecentriq','cemiplimab':'Libtayo','libtayo':'Libtayo','ipilimumab':'Yervoy','yervoy':'Yervoy','tremelimumab':'Imjudo','imjudo':'Imjudo'}
def canonical_asset(name):
    # Exact aliases only: do not collapse combinations, biosimilars or similar names.
    return DRUGS.get(name.strip().casefold(),name.strip())
def arm_roles(module):
    arms={a.get('label',''):a.get('type','UNKNOWN') for a in module.get('armGroups',[]) if a.get('label')}
    rows=[]
    for i in module.get('interventions',[]):
        if i.get('type') not in ('DRUG','BIOLOGICAL'): continue
        name=i.get('name','').strip()
        if not name: continue
        labels=i.get('armGroupLabels',[])
        types={arms.get(x,'UNKNOWN') for x in labels}
        exp='EXPERIMENTAL' in types; comp=bool(types & {'ACTIVE_COMPARATOR','PLACEBO_COMPARATOR','SHAM_COMPARATOR'})
        unknown=not types or bool(types-{'EXPERIMENTAL','ACTIVE_COMPARATOR','PLACEBO_COMPARATOR','SHAM_COMPARATOR'})
        role='Both' if exp and comp else 'Experimental arm' if exp else 'Comparator arm' if comp else 'Unclear'
        rows.append({'Asset':canonical_asset(name),'Registry intervention':name,'Arm role':role,'Arm evidence':'; '.join(f'{x}: {arms.get(x,"UNKNOWN")}' for x in labels),'Role caveat':'Incomplete or other arm labels' if unknown else 'Registry arm mapping; not ownership or development intent'})
    return rows
def enrich_frame(df):
    f=df.copy(); f['Sponsor display']=f.Sponsor.map(lambda x:ALIASES.get(x,x)); f['Development status']=f.Status.map(lambda x:'Active / planned' if x in ACTIVE else 'Historical / closed' if x in {'COMPLETED','TERMINATED','WITHDRAWN'} else 'Other / uncertain'); return f
def asset_rows(df):
    rows=[]
    for _,r in df.iterrows():
        try: roles=json.loads(r.get('Arm mapping','[]') or '[]')
        except (ValueError,TypeError): roles=[]
        for role in roles:
            rows.append({**role,**{k:r.get(k,'') for k in ['NCT ID','Phase','Status','Sponsor','Source']}})
    return pd.DataFrame(rows,columns=['Asset','Registry intervention','Arm role','Arm evidence','Role caveat','NCT ID','Phase','Status','Sponsor','Source'])
def phase_matrix(rows):
    if rows.empty: return pd.DataFrame()
    r=rows.assign(Phase=rows.Phase.str.split(' / ')).explode('Phase')
    return r.groupby(['Asset','Phase'])['NCT ID'].nunique().unstack(fill_value=0)

def benchmark_assets(rows, selected):
    """Unique study totals, separately from potentially overlapping phase counts."""
    r=rows[rows.Asset.isin(selected)]
    matrix=phase_matrix(r).reindex(selected,fill_value=0)
    phases=[p for p in ['PHASE1','PHASE2','PHASE3','PHASE4'] if p in matrix.columns]
    phases+=sorted(set(matrix.columns)-set(phases))
    matrix=matrix.reindex(columns=phases)
    matrix['Unique studies']=r.groupby('Asset')['NCT ID'].nunique().reindex(selected,fill_value=0)
    return matrix
