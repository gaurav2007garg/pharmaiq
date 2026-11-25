import streamlit as st
import pandas as pd
import hashlib
from audit_export import build_audit
from calibration import fit_constants
from tornado import tornado
from cbc_ui import render as render_cbc
from oncology_ui import render as render_oncology
import plotly.graph_objects as go
import numpy as np
import plotly.express as px
from simulator import sample_utilities, sample_respondents, validate, shares, importance, individual_shares

st.set_page_config(page_title='PharmaIQ | Market Simulator',layout='wide')
st.title('PharmaIQ')
st.caption('Commercial Intelligence & Analytics • v0.6.1')
st.sidebar.header('Modules')
module=st.sidebar.radio('Navigate',['Market Simulator','CBC Utility Estimation','Oncology Intelligence','AI Analytics (planned)'])
if module=='CBC Utility Estimation':
    render_cbc(); st.stop()
if module=='Oncology Intelligence':
    render_oncology(); st.stop()
if module!='Market Simulator':
    st.info('This module is planned for the next development phase.'); st.stop()
demo=st.sidebar.radio('Demo data',['Respondent-level (200 HCPs)','Segment-level']+(['Estimated CBC utilities'] if 'estimated_utilities' in st.session_state else []))
st.sidebar.download_button('Download respondent utility CSV',sample_respondents().to_csv(index=False),'sample_respondent_utilities.csv')
st.sidebar.download_button('Download segment utility CSV',sample_utilities().to_csv(index=False),'sample_utilities.csv')
file=st.sidebar.file_uploader('Upload part-worth utilities',type=['csv','xlsx'])
try:
    df=validate((pd.read_csv(file,dtype={'respondent_id':str}) if file.name.endswith('.csv') else pd.read_excel(file,dtype={'respondent_id':str})) if file else (sample_respondents() if demo.startswith('Respondent') else (st.session_state['estimated_utilities'] if demo=='Estimated CBC utilities' else sample_utilities())))
except Exception as e:
    st.error(f'Invalid utility file: {e}'); st.stop()
respondent='respondent_id' in df
st.sidebar.caption('Respondent-level logit' if respondent else 'Segment-average logit')
st.sidebar.caption('Weights are normalized across the selected population. Utilities must be on a comparable scale.')
selected=st.sidebar.multiselect('Filter physician segments',list(df.segment.unique()),default=list(df.segment.unique()),key='segments-'+hashlib.sha256(df.to_csv(index=False).encode()).hexdigest())
full_context=hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
full_df=df.copy()
df=df[df.segment.isin(selected)]
try: df=validate(df)
except ValueError as e: st.info(f'Select a population with positive total weight: {e}'); st.stop()
unit='respondent_id' if respondent else 'segment'
meta=df.groupby(unit).weight.first()
st.caption(f'Analysis population: {len(meta):,} '+('respondents' if respondent else 'segments')+f' | {df.segment.nunique()} segments | Sum of weights: {meta.sum():.2f}')
levels={a:list(g.level.unique()) for a,g in df.groupby('attribute',sort=False)}
st.subheader('Configure competing profiles')
count=st.slider('Number of alternatives',2,5,3)
profiles={}; baseline={}
cols=st.columns(count)
for i,col in enumerate(cols):
    name=['Competitor A','Competitor B','New Product','Competitor C','Competitor D'][i]
    with col:
        st.markdown('**'+name+'**'); profiles[name]={}; baseline[name]={}
        for a,ls in levels.items():
            default=min(i,len(ls)-1)
            baseline[name][a]=ls[default]
            profiles[name][a]=st.selectbox(a,ls,index=default,key=f'{i}-{a}-{ls}')
# Baselines are kept separately for each utility dataset and alternative set.
context=full_context+f':{count}'
store=st.session_state.setdefault('baselines',{})
if context not in store:
    store[context]={k:v.copy() for k,v in baseline.items()}
left,right=st.columns(2)
if left.button('Save current profiles as baseline'):
    store[context]={k:v.copy() for k,v in profiles.items()}
if right.button('Reset baseline to defaults'):
    store[context]={k:v.copy() for k,v in baseline.items()}
old=store[context]
base,_=shares(df,old)
st.caption('Baseline is fixed until saved or reset. Each dataset and alternative count has its own baseline for this session. Filters recalculate both cases on the same population.')
with st.expander('View locked baseline product profiles'):
    st.dataframe(pd.DataFrame(old),use_container_width=True)
raw_base=base.copy()
raw_current,_=shares(df,profiles)
constants=None; diagnostics=None
with st.expander('Market share calibration', expanded=False):
    enabled=st.checkbox('Enable calibration')
    if enabled:
        source=st.radio('Target source',['Stated prescribing shares','Observed market shares'],horizontal=True)
        granularity=st.selectbox('Calibration level',['Overall','Segment']+(['Respondent'] if respondent and source.startswith('Stated') else []))
        st.caption('Targets must refer to the locked baseline profiles and full dataset. Constants are fitted on the full dataset, not the selected segment filter, and held fixed when scenario profiles change.')
        groups=['Overall'] if granularity=='Overall' else sorted(full_df.segment.unique() if granularity=='Segment' else full_df.respondent_id.unique())
        template=pd.DataFrame([{'group':g,'product':p,'target':1/count} for g in groups for p in old])
        st.download_button('Download target template (fractions)',template.to_csv(index=False),'calibration_targets.csv')
        uploaded=st.file_uploader('Upload target shares (CSV or Excel)',type=['csv','xlsx'],key='calibration_upload')
        smoothing=st.number_input('Zero-share smoothing mixture (%)',min_value=0.0001,max_value=10.0,value=0.1,format='%.4f')/100
        st.caption('Only groups containing zero shares are mixed with a uniform distribution. A 0.1% mixture makes every alternative possible; it does not imply observed uptake.')
        try:
            if uploaded:
                targets=pd.read_csv(uploaded,dtype={'group':str}) if uploaded.name.endswith('.csv') else pd.read_excel(uploaded,dtype={'group':str})
            elif granularity!='Respondent':
                targets=st.data_editor(template,key='target-'+context+granularity+source,disabled=['group','product'],hide_index=True,column_config={'target':st.column_config.NumberColumn('Target fraction',min_value=0.,max_value=1.,format='%.6f')})
            else:
                st.info('Upload a target file with one row per respondent and product. The template contains equal shares as placeholders, not survey results.')
                targets=None
            if targets is not None:
                if not uploaded: st.caption("Equal-share starting values are placeholders; replace with your research targets.")
                constants,diagnostics=fit_constants(full_df,old,targets,granularity,smoothing)
                st.success(f'Calibration fitted. Maximum absolute residual: {diagnostics.residual.abs().max():.2e}')
                st.dataframe(diagnostics,hide_index=True)
                st.download_button('Export calibration constants',constants.reset_index().to_csv(index=False),'calibration_constants.csv')
            else: st.stop()
        except Exception as e:
            st.error(f'Calibration not applied: {e}'); st.stop()
base,_=shares(df,old,constants)
current,detail=shares(df,profiles,constants)
st.subheader('Simulated preference share')
for col,(name,value) in zip(st.columns(count),current.items()):
    col.metric(name,f'{value:.1%}',f'{(value-base[name])*100:+.1f} pp')
    col.caption(f'Baseline: {base[name]:.1%}')
comparison=pd.DataFrame({'Baseline':base,'Scenario':current}).reset_index().melt(id_vars='product',var_name='Case',value_name='Share')
st.plotly_chart(px.bar(comparison,x='product',y='Share',color='Case',barmode='group',text='Share',color_discrete_map={'Baseline':'#94a3b8','Scenario':'#2563eb'}).update_traces(texttemplate='%{y:.1%}',textposition='outside',cliponaxis=False).update_yaxes(tickformat='.0%',rangemode='tozero').update_layout(yaxis_range=[0,max(base.max(),current.max())*1.2],xaxis_title=None),use_container_width=True)
if constants is not None:
    st.dataframe(pd.DataFrame({'Raw baseline':raw_base,'Calibrated baseline':base,'Raw scenario':raw_current,'Calibrated scenario':current}).style.format('{:.2%}'),use_container_width=True)
    st.caption('Calibrated shares are anchored to the selected source, not independently validated forecasts. Changing or resetting the locked baseline refits constants.')
t1,t2,t3=st.tabs(['Physician segments','Attribute importance','Sensitivity analysis'])
with t1:
    st.plotly_chart(px.bar(detail,x='segment',y='share',color='product',barmode='group').update_yaxes(tickformat='.0%'),use_container_width=True)
with t2:
    imp=importance(df)
    st.plotly_chart(px.bar(imp,x='attribute',y='importance',color='segment',barmode='group').update_yaxes(tickformat='.0%'),use_container_width=True)
    st.caption('Relative utility range within each segment; depends on the levels tested.')
with t3:
    product=st.selectbox('Product to vary',list(profiles),index=min(2,count-1)); attribute=st.selectbox('Attribute to vary',list(levels))
    results=[]
    for level in levels[attribute]:
        scenario={k:v.copy() for k,v in profiles.items()}; scenario[product][attribute]=level
        s,_=shares(df,scenario,constants)
        results.append({'Level':level,'Preference share':s[product],'Change (pp)':100*(s[product]-current[product])})
    st.dataframe(pd.DataFrame(results),hide_index=True)
    st.download_button('Export sensitivity results',pd.DataFrame(results).to_csv(index=False),'sensitivity.csv')
with t3:
    st.subheader('Tornado chart — one attribute at a time')
    st.caption('Reference is the current scenario, not the locked market baseline. Calibration constants and all other attributes remain fixed.')
    if st.checkbox('Show tornado analysis'):
        ref,summary,detail_t=tornado(df,profiles,product,constants)
        fig=go.Figure()
        for col,label,color in [('low','Minimum','#b45309'),('high','Maximum','#2563eb')]:
            fig.add_bar(y=summary.attribute,x=summary[col],orientation='h',name=label,marker_color=color,customdata=summary[col+'_level'],hovertemplate='%{y}: %{customdata}<br>%{x:+.2f} pp<extra></extra>')
        fig.update_layout(barmode='relative',xaxis_title='Change vs current scenario (percentage points)',title=f'{product} | Reference share {ref:.1%}')
        fig.add_vline(x=0,line_color='gray'); st.plotly_chart(fig,use_container_width=True)
        st.dataframe(summary,hide_index=True)
        st.download_button('Export all tornado levels',detail_t.to_csv(index=False),'tornado_levels.csv')
st.subheader('Net competitive share redistribution')
changes=(current-base)*100
st.plotly_chart(px.bar(changes.rename('Change (pp)').reset_index(),x='product',y='Change (pp)').add_hline(y=0),use_container_width=True)
st.caption('Net changes versus locked baseline, not observed switching flows.')
if respondent:
    individual=individual_shares(df,profiles,constants)
    st.download_button('Export respondent probabilities',individual.to_csv(index=False),'respondent_probabilities.csv')
    st.caption('Each respondent is simulated separately; probabilities are then weighted and aggregated. No utilities are averaged before simulation.')
with st.expander('Excel calculation audit', expanded=False):
    st.caption('Formula-driven workbook for the selected population, including both baseline and scenario calculations.')
    if st.button('Prepare Excel audit workbook'):
        audit=build_audit(df,old,profiles,constants,diagnostics)
        st.download_button('Download Excel audit workbook',audit,'pharmaiq_share_audit.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if constants is not None:
            st.download_button('Download uncalibrated audit for comparison',build_audit(df,old,profiles),'pharmaiq_raw_audit.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
st.download_button('Export segment results',detail.to_csv(index=False),'segment_shares.csv')
st.warning('Preference shares are conditional on the profiles shown, not forecasts of actual sales or prescribing. No explicit opt-out, access or awareness model is included. Demo data are fictional.')
