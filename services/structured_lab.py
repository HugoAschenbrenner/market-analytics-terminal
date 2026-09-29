"""Independent structured-note state; opening it never replaces the shared book."""
from datetime import date
from dataclasses import replace
import streamlit as st
from core.models import TerminalState
from core.state import demo_book

DEMO_DATE = date(2026, 9, 9)


def demo_structured_lab():
    book = demo_book('structured')
    book.positions = book.positions.query("asset_class == 'Structured'").copy()
    book.repo_cash = 0.
    book.collateral_id = ''
    key = book.positions.iloc[0]['id']
    book.structured_terms[key] = dict(
        product='Phoenix', memory=True, underlyings=('SPY', 'QQQ', 'SX5E'),
        fixings=(550., 475., 5000.), volatilities=(.20, .25, .23),
        correlation=.30, simulations=3000, frequency=4,
    )
    return TerminalState(book, valuation_date=DEMO_DATE)


def get_structured_lab(ui=None):
    if 'structured_lab' not in st.session_state:
        st.session_state.structured_lab = demo_structured_lab()
    lab = st.session_state.structured_lab
    if ui is not None:
        lab.ui = replace(ui)
    return lab
