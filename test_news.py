import json
from datetime import datetime, timezone
from email.utils import format_datetime
from news_monitor import asset_terms, query_terms, pubmed, rss, combine

def test_alias():
    assert 'durvalumab' in asset_terms('Imfinzi')
    assert 'NSCLC' in query_terms(['Imfinzi'],'NSCLC')
def test_pubmed():
    def fetch(url):
        return json.dumps({'esearchresult':{'idlist':['123']}} if 'esearch' in url else {'result':{'123':{'title':'Study','pubdate':'2026 Nov','fulljournalname':'Journal'}}}).encode()
    assert pubmed(['NCT123'],'',90,fetch)[0]['URL']=='https://pubmed.ncbi.nlm.nih.gov/123/'
def test_rss():
    dt=format_datetime(datetime.now(timezone.utc))
    xml=f'<rss><channel><item><title>Example</title><source url="https://www.fda.gov">FDA</source><pubDate>{dt}</pubDate><link>https://news.google.com/a</link></item><item><title>Untrusted</title><source url="https://fda.gov.example.com">Fake</source><pubDate>{dt}</pubDate><link>https://news.google.com/b</link></item></channel></rss>'
    rows=rss(['Imfinzi'],'',90,['FDA'],lambda _:xml.encode());assert len(rows)==1 and rows[0]['Type']=='Regulatory announcement'
    assert len(combine(rows+rows))==1
