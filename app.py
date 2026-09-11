import streamlit as st
from core.state import get_state
from core.i18n import t, error_message
from components.global_header import global_header, footer
from components.book_editor import book_selector
from app_pages import overview, markets, risk_lab, derivatives_lab, financing

st.set_page_config(page_title='Market Analytics Terminal',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
from services.market_data import ensure_market
state=get_state()
ensure_market(state)
global_header(state)
book_selector(state)
PAGES={'overview':overview,'markets':markets,'risk':risk_lab,'derivatives':derivatives_lab,'financing':financing}
try:
    PAGES[state.ui.page].render(state)
except (ValueError,KeyError,TypeError) as exc:
    st.error(error_message(exc))
footer()
