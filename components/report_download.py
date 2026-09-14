import streamlit as st
from core.i18n import t, error_message
from reports.desk_report import generate_desk_report


def render_reports(state):
    with st.expander(t('export')):
        section=st.selectbox(t('report.scope'),['all','rates','risk','structured','financing'],format_func=lambda x,lang=state.ui.language:t('report.'+x,lang))
        if st.button(t('report.prepare')):
            try:
                data=generate_desk_report(state,section)
            except (ValueError,KeyError,TypeError) as exc:
                st.error(error_message(exc))
            else:
                st.download_button(t('report.download'),data,f'market_terminal_{section}.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.caption(t('report.note'))
