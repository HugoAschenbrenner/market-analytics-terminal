import streamlit as st
from core.i18n import t
from reports.desk_report import generate_desk_report


def render_reports(state):
    with st.expander(t('export')):
        section=st.selectbox(t('report.scope'),['all','rates','risk','structured','financing'],format_func=lambda x,lang=state.ui.language:t('report.'+x,lang))
        if st.button(t('report.prepare')):
            data=generate_desk_report(state,section)
            st.download_button(t('report.download'),data,f'market_terminal_{section}.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.caption(t('report.note'))
