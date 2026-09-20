import streamlit as st
from core.state import get_state
from core.i18n import t, error_message
from components.global_header import global_header, footer, page_from_query
from components.book_editor import book_selector
from app_pages import overview, markets, risk_lab, derivatives_lab, financing, welcome

def render():
    from services.market_data import ensure_market
    state=get_state()
    if page_from_query() != 'welcome':
        ensure_market(state)
    global_header(state)
    from components.version_switch import render_version_switch
    render_version_switch("v2", state.ui.language, state.ui.theme)
    if state.ui.page != 'welcome':
        book_selector(state)
        from components.education import render_workspace_guide
        render_workspace_guide(state)
    PAGES={'welcome':welcome,'overview':overview,'markets':markets,'risk':risk_lab,'derivatives':derivatives_lab,'financing':financing}
    try:
        PAGES[state.ui.page].render(state)
    except (ValueError,KeyError,TypeError) as exc:
        st.error(error_message(exc))
    if state.ui.page != 'welcome':
        from components.report_download import render_reports
        render_reports(state)
    footer()
