import pandas as pd
import streamlit as st
from news_monitor import DOMAINS, asset_terms, pubmed, rss, combine

@st.cache_data(ttl=1800,show_spinner=False)
def load(terms,condition,days,sources,scientific):
    rows=[]; errors=[]
    for label,fn in [('Curated news',lambda:rss(terms,condition,days,sources)),('PubMed',lambda:pubmed(terms,condition,days))]:
        if label=='PubMed' and not scientific:continue
        if label=='Curated news' and not sources:continue
        try:rows.extend(fn())
        except Exception as e:errors.append(label+': '+type(e).__name__)
    return combine(rows),errors

def render_news(f,assets,selected_assets,condition,synthetic):
    st.subheader('News & Evidence Monitor')
    st.caption('On-demand headline and publication discovery. Metadata only; open original sources before interpreting findings. Search coverage is incomplete; news uses an unofficial Google News RSS interface, which may change.')
    if synthetic:
        st.info('Switch to live registry data to discover articles. Fictional trial IDs are not searched.');return
    mode=st.radio('News search scope',['Asset news','Trial-specific evidence'],horizontal=True)
    if mode=='Asset news':
        options=sorted(set(assets.Asset))
        chosen=st.multiselect('Products to monitor',options,default=[x for x in selected_assets if x in options],key='news_assets_'+str(hash(tuple(options))))
        terms=list(dict.fromkeys(t for a in chosen for t in asset_terms(a)))
        cond=st.text_input('Indication filter (optional)',condition,key='news_cond')
        scope='Asset / indication search; not trial-specific'
    else:
        nct=st.selectbox('Clinical study',f['NCT ID'].tolist(),format_func=lambda n:n+' — '+str(f.loc[f['NCT ID']==n,'Title'].iloc[0]))
        acronym=st.text_input('Study acronym (optional; verify spelling)',key='news_acronym')
        terms=[nct]+([acronym.strip()] if acronym.strip() else [])
        cond='';scope='Trial identifier/acronym search; verify exact study match'
    days=st.selectbox('Publication lookback (days)',[30,90,180,365],index=1)
    sources=st.multiselect('News publishers',list(DOMAINS),default=list(DOMAINS))
    scientific=st.checkbox('Include PubMed publications',True)
    signature=(tuple(terms),cond,days,tuple(sources),scientific,scope)
    if st.button('Search latest evidence',key='news_search'):
        if not terms:st.warning('Select an asset or trial first.')
        elif not sources and not scientific:st.warning('Select at least one source.')
        else:
            with st.spinner('Searching public evidence sources...'):
                st.session_state['news_results']=(signature,load(tuple(terms),cond,days,tuple(sources),scientific))
    result=st.session_state.get('news_results')
    if result and result[0]==signature:
        rows,errors=result[1]
        for e in errors:st.warning('Retrieval incomplete: '+e)
        st.caption(scope+' | Search terms: '+', '.join(terms))
        if not rows:st.info('No results returned. Try a longer lookback or broader indication; this does not establish absence of news.')
        else:
            df=pd.DataFrame(rows); df['Sort date']=pd.to_datetime(df.Date,errors='coerce',format='mixed');df=df.sort_values('Sort date',ascending=False,na_position='last').drop(columns='Sort date')
            st.metric('Discovered records',len(df));st.dataframe(df,hide_index=True,use_container_width=True,column_config={'URL':st.column_config.LinkColumn('Open source')})
            safe=df.apply(lambda c:c.map(lambda x:"'"+x if isinstance(x,str) and x.startswith(('=','+','-','@')) else x))
            st.download_button('Download article evidence CSV',safe.to_csv(index=False),'pharmaiq_news.csv','text/csv')
    elif result:st.info('Search criteria changed. Run a new search.')
