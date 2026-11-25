"""On-demand public metadata discovery; not a comprehensive media database."""
import json, re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from ci_enrich import DRUGS

DOMAINS={'FDA':'fda.gov','Fierce Pharma':'fiercepharma.com','Fierce Biotech':'fiercebiotech.com','BioPharma Dive':'biopharmadive.com','OncLive':'onclive.com','Reuters':'reuters.com','ASCO':'asco.org','ESMO':'esmo.org','AACR':'aacr.org','AstraZeneca':'astrazeneca.com','Merck':'merck.com','Bristol Myers Squibb':'bms.com','Roche':'roche.com','Regeneron':'regeneron.com'}
NCBI='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
def retrieve(url):
    with urlopen(Request(url,headers={'User-Agent':'PharmaIQ research prototype/0.6.3'}),timeout=20) as r: return r.read(5_000_000)
def quoted(s): return '"'+str(s).replace('"',' ').strip()+'"'
def asset_terms(asset):
    return list(dict.fromkeys([asset]+[k for k,v in DRUGS.items() if v.casefold()==asset.casefold() and k!=asset.casefold()]))
def query_terms(terms,condition='',pubmed=False):
    clean=[quoted(t) for t in terms if str(t).strip()]
    if not clean: raise ValueError('Enter at least one asset or trial identifier.')
    q='('+' OR '.join(clean)+')'
    if condition.strip(): q+=(' AND ' if pubmed else ' ')+quoted(condition)
    return q

def pubmed(terms,condition,days,fetch=retrieve):
    q=query_terms(terms,condition,True)
    p={'db':'pubmed','term':q,'reldate':days,'datetype':'pdat','retmax':50,'sort':'pub date','retmode':'json','tool':'pharmaiq'}
    ids=json.loads(fetch(NCBI+'esearch.fcgi?'+urlencode(p)))['esearchresult']['idlist']
    if not ids:return []
    result=json.loads(fetch(NCBI+'esummary.fcgi?'+urlencode({'db':'pubmed','id':','.join(ids),'retmode':'json','tool':'pharmaiq'})))['result']
    return [{'Title':result[i].get('title',''),'Source':result[i].get('fulljournalname','PubMed'),'Date':result[i].get('pubdate',''),'Type':'Scientific publication (verify article type)','URL':'https://pubmed.ncbi.nlm.nih.gov/'+i+'/'} for i in ids if i in result]

def rss(terms,condition,days,sources,fetch=retrieve):
    if not sources:return []
    q=query_terms(terms,condition)+' ('+' OR '.join('site:'+DOMAINS[s] for s in sources)+') when:'+str(days)+'d'
    url='https://news.google.com/rss/search?'+urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
    root=ET.fromstring(fetch(url)); rows=[]
    for item in root.findall('./channel/item'):
        source=item.find('source'); domain=urlparse(source.get('url','') if source is not None else '').hostname or ''
        matches=[s for s in sources if domain==DOMAINS[s] or domain.endswith('.'+DOMAINS[s])]
        if not matches:continue
        link=item.findtext('link',''); title=item.findtext('title',''); raw=item.findtext('pubDate','')
        try: dt=parsedate_to_datetime(raw).astimezone(timezone.utc)
        except (ValueError,TypeError,OverflowError):continue
        if dt < datetime.now(timezone.utc)-timedelta(days=days) or dt>datetime.now(timezone.utc)+timedelta(days=1):continue
        if urlparse(link).scheme!='https':continue
        label=matches[0]; typ='Regulatory announcement' if label=='FDA' else 'Company announcement' if label in {'AstraZeneca','Merck','Bristol Myers Squibb','Roche','Regeneron'} else 'Conference / society news' if label in {'ASCO','ESMO','AACR'} else 'Industry news'
        rows.append({'Title':title,'Source':label,'Date':dt.date().isoformat(),'Type':typ,'URL':link})
    return rows

def combine(rows):
    seen=set(); out=[]
    for r in rows:
        key=(re.sub(r'\W+',' ',r['Title'].casefold()).strip(),r['Source'])
        if key in seen:continue
        seen.add(key); out.append(r)
    return out
