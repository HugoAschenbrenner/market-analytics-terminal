"""Dedicated V2 structured notes route, reusing the existing contract workspace."""
from components.structured_workspace import render_structured
import streamlit as st
from core.i18n import t
from core.state import demo_book
from components.lab_common import tr


def _load_demo(state):
    state.book = demo_book('structured')
    state.risk.results.clear()
    st.session_state['demo_selector'] = 'structured'


def render(state):
    st.title(t('nav.structured-products'))
    if state.book.positions.query("asset_class=='Structured'").empty:
        st.info(t('structured.none'))
        st.button(tr('Load structured demo (replaces current book)', 'Charger la démo structurée (remplace le portefeuille)'),
                  key='load_structured_demo',on_click=_load_demo,args=(state,))
        return
    render_structured(state)
