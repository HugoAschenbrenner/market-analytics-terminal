import streamlit as st
from core.i18n import t
from services.analytics import marked_positions
from components.vanilla_workspace import render_vanilla,render_greeks,render_volatility


def render(state):
    options=marked_positions(state).query("asset_class=='Option'")
    if options.empty:
        st.info(t('option.none'));return
    selected=st.selectbox(t('option.select'),options.id.tolist(),key='book_option')
    row=options.set_index('id').loc[selected]
    tabs=st.tabs([t(k) for k in ['vanilla','greeks','volatility']],key='derivative_tabs',on_change='rerun')
    for tab,renderer in zip(tabs,[render_vanilla,render_greeks,render_volatility]):
        if tab.open:
            with tab:renderer(row,state)
