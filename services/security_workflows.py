"""Explicit context transfer. Never relabel the synthetic option chain as market data."""
from dataclasses import replace
import streamlit as st
from core.securities import SECURITIES
from core.i18n import t
from services.lab import get_lab


def open_options(id,quote,assumed_vol):
    from components.global_header import navigate
    lab=get_lab();lab.position=replace(lab.position,spot=quote.price,strike=quote.price,volatility=assumed_vol)
    lab.currency=quote.currency if quote.currency in ('USD','EUR','GBP','JPY') else 'USD'
    lab.position_source=f'{id} · spot {quote.source} {quote.observed_at:%Y-%m-%d %H:%M UTC}; ATM strike; user-assumed volatility; other contract/model inputs retained'
    lab.view='position';st.session_state.eqd_view='position'
    for key in list(st.session_state):
        if key.startswith('eqd_pos_'):del st.session_state[key]
    st.session_state.security_context=id
    navigate('equity-derivatives')


def open_fx(id,quote):
    from components.global_header import navigate
    state=st.session_state.terminal
    foreign,domestic=id[:3],id[3:]
    st.session_state.fx_foreign=foreign;st.session_state.fx_domestic=domestic
    if quote:st.session_state[f'fx_spot_{foreign}_{domestic}']=float(quote.price)
    st.session_state.markets_tabs=t('fx',state.ui.language)
    st.session_state.security_context=id
    navigate('analytics')
