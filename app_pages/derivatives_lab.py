import streamlit as st
from core.i18n import t
from services.analytics import marked_positions
from components.vanilla_workspace import render_vanilla,render_greeks,render_volatility
from components.structured_workspace import render_structured
from components.product_workshop import render_workshop


def render(state):
    tab_keys=['vanilla','greeks','volatility','structured','workshop']
    active=st.session_state.get('derivative_tabs',st.session_state.get('_derivative_active'))
    for key in tab_keys:
        if active in (t(key,'en'),t(key,'fr')):
            if st.session_state.get('derivative_tabs') != t(key):
                st.session_state['derivative_tabs']=t(key)
            break
    options=marked_positions(state).query("asset_class=='Option'")
    row=None
    if not options.empty and st.session_state.get('derivative_tabs') not in (t('structured'),t('workshop')):
        selected=st.selectbox(t('option.select'),options.id.tolist(),key='book_option')
        row=options.set_index('id').loc[selected]
    tabs=st.tabs([t(k) for k in tab_keys],key='derivative_tabs',on_change='rerun')
    st.session_state['_derivative_active']=st.session_state['derivative_tabs']
    for tab,renderer in zip(tabs[:3],[render_vanilla,render_greeks,render_volatility]):
        if tab.open:
            with tab:
                if row is None:st.info(t('option.none'))
                else:renderer(row,state)
    if tabs[3].open:
        with tabs[3]:render_structured(state)
    if tabs[4].open:
        with tabs[4]:render_workshop(state)
