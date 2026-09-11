import streamlit as st
from core.i18n import t
from services.analytics import marked_positions
from components.vanilla_workspace import render_vanilla,render_greeks,render_volatility
from components.structured_workspace import render_structured


def render(state):
    options=marked_positions(state).query("asset_class=='Option'")
    row=None
    if not options.empty and st.session_state.get('derivative_tabs') != t('structured'):
        selected=st.selectbox(t('option.select'),options.id.tolist(),key='book_option')
        row=options.set_index('id').loc[selected]
    tabs=st.tabs([t(k) for k in ['vanilla','greeks','volatility','structured']],key='derivative_tabs',on_change='rerun')
    for tab,renderer in zip(tabs[:3],[render_vanilla,render_greeks,render_volatility]):
        if tab.open:
            with tab:
                if row is None:st.info(t('option.none'))
                else:renderer(row,state)
    if tabs[3].open:
        with tabs[3]:render_structured(state)
