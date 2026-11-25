import streamlit as st
import pandas as pd
import plotly.express as px
from cbc import demo_choices,fit_cbc

def render():
    st.header('CBC utility estimation')
    st.caption('Conditional multinomial logit • pooled or separate segment models • categorical dummy coding')
    demo=demo_choices(); st.download_button('Download synthetic choice tasks',demo.to_csv(index=False),'sample_cbc_choices.csv')
    upload=st.file_uploader('Upload long-format choice tasks',type=['csv','xlsx'])
    try:
        d=(pd.read_csv(upload,dtype=str) if upload.name.endswith('.csv') else pd.read_excel(upload,dtype=str)) if upload else demo
        st.dataframe(d.head(12),hide_index=True)
        st.caption('One row per alternative per task; exactly one chosen=1. Required: respondent_id, task_id, alternative_id, chosen. Optional segment; all other columns are categorical attributes. No opt-out or alternative constants in this model.')
        by=st.checkbox('Estimate separate models by segment')
        h=st.slider('Holdout tasks (%)',0,40,20,5)/100
        ridge=st.number_input('L2 penalty (0 = unpenalized)',min_value=0.,value=.01,step=.01,format='%.4f')
        if st.button('Estimate utilities'):
            with st.spinner('Fitting conditional logit models'):
                st.session_state['cbc_result']=fit_cbc(d,by,h,ridge=ridge)
                st.session_state['cbc_signature']=(d.to_csv(index=False),by,h,ridge)
        if st.session_state.get('cbc_signature')==(d.to_csv(index=False),by,h,ridge):
            u,m,p=st.session_state['cbc_result']; st.subheader('Model diagnostics'); st.dataframe(m,hide_index=True)
            st.caption('Holdout uses entire tasks from the same respondents; not an independent respondent validation. Hit rate splits ties. McFadden R² uses equal-choice null. Models fitted to training tasks only.')
            st.subheader('Part-worth utilities'); st.plotly_chart(px.bar(u,x='level',y='utility',color='segment',facet_col='attribute',facet_col_wrap=2,barmode='group').update_xaxes(matches=None),use_container_width=True)
            st.dataframe(u,hide_index=True)
            st.download_button('Download simulator-ready utilities',u.to_csv(index=False),'estimated_utilities.csv')
            st.download_button('Download task probabilities',p.to_csv(index=False),'cbc_predictions.csv')
            st.download_button('Download diagnostics',m.to_csv(index=False),'cbc_diagnostics.csv')
            if st.button('Use estimated utilities in simulator'):
                st.session_state['estimated_utilities']=u.copy(); st.success('Utilities ready. Select Market Simulator in sidebar and Estimated CBC utilities as data source.')
            st.warning('These are pooled or segment-level estimates, not individual utilities. Segment weights are respondent counts; separately estimated models can differ in utility scale. No standard errors or hierarchical Bayes yet.')
    except Exception as e: st.error(str(e))
