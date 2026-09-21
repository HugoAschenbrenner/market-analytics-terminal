import streamlit as st
from core.state import get_state
from core.i18n import t, error_message
from components.global_header import global_header, footer, page_from_query
from components.book_editor import book_selector
from app_pages import overview, markets, risk_lab, derivatives_lab, financing, welcome, equity_derivatives, structured_lab, market_monitor, security

def render():
    from services.market_data import ensure_market
    state=get_state()
    book_pages=('overview','analytics','risk','derivatives','financing','structured-products')
    if page_from_query() in book_pages:
        ensure_market(state)
    global_header(state)
    from components.version_switch import render_version_switch
    render_version_switch("v2", state.ui.language, state.ui.theme)
    if state.ui.page in book_pages:
        book_selector(state)
        from components.education import render_workspace_guide
        render_workspace_guide(state)
    PAGES={'welcome':welcome,'overview':overview,'markets':market_monitor,'analytics':markets,'security':security,'risk':risk_lab,'derivatives':derivatives_lab,'financing':financing,'equity-derivatives':equity_derivatives,'structured-products':structured_lab}
    try:
        PAGES[state.ui.page].render(state)
    except (ValueError,KeyError,TypeError) as exc:
        st.error(error_message(exc))
    if state.ui.page in book_pages:
        from components.report_download import render_reports
        render_reports(state)
    footer()
