import numpy as np
import pandas as pd
import streamlit as st
from core.models import ASSET_CLASSES, CURRENCIES, PositionBook, TerminalState

DEMO_BOOKS = ("balanced", "macro", "options", "structured")
FIELDS = dict(id="", ticker="", asset_class="Equity", currency="USD", quantity=1., price=100.,
              multiplier=1., sleeve="Core", underlying="SPY", strike=550., maturity=1.,
              volatility=.20, coupon=.04, yield_rate=.04, option_type="Call", mark_mode="Book", weight=np.nan)

def position(identifier, ticker, asset_class, quantity, price, **kwargs):
    return {**FIELDS, "id": identifier, "ticker": ticker, "asset_class": asset_class,
            "quantity": quantity, "price": price, **kwargs}

def demo_book(name="balanced"):
    cash = position("cash", "USD", "Cash", 400000, 1)
    bonds = [position("ust10", "UST10", "Bond", 250000, 99.5, multiplier=.01, maturity=10, sleeve="Rates"),
             position("credit5", "CREDIT5", "Bond", 150000, 98, multiplier=.01, maturity=5, coupon=.05, yield_rate=.055, sleeve="Credit")]
    equity = position("spy", "SPY", "Equity", 500, 550, sleeve="Equity", mark_mode="Market")
    option = position("spy-put", "SPY-P550", "Option", 10, 1, multiplier=100, option_type="Put", sleeve="Hedge")
    eur = position("eur", "EUR", "FX", 100000, 1, currency="EUR", sleeve="FX")
    note = position("note", "WORST-OF", "Structured", 500, 100, underlying="SPY", maturity=3, sleeve="Structured")
    rows = {"balanced": [cash, *bonds, equity, option, eur],
            "macro": [cash, *bonds, eur, position("bund", "BUND10", "Bond", 250000, 99, multiplier=.01, maturity=10, currency="EUR", coupon=.025, sleeve="Rates")],
            "options": [cash, equity, option, position("spy-call", "SPY-C575", "Option", -15, 1, multiplier=100, strike=575, sleeve="Overwrite")],
            "structured": [cash, bonds[0], note, option, eur]}[name]
    book=PositionBook(validate_book(pd.DataFrame(rows)), name=name)
    if name != "options":
        book.repo_cash=150000.;book.collateral_id="ust10"
        book.positions.loc[book.positions.id=="cash","quantity"]+=book.repo_cash
    return book

def validate_book(frame):
    frame = frame.copy()
    required = {"id", "ticker", "asset_class", "currency", "quantity", "price"}
    if not required.issubset(frame):
        raise ValueError("book.missing_columns")
    if not 1 <= len(frame) <= 1000:
        raise ValueError("book.row_count")
    for key, default in FIELDS.items():
        if key not in frame:
            frame[key] = np.where(frame.asset_class=="Bond", .01, 1.) if key=="multiplier" else default
    for col in ("id", "ticker", "asset_class", "currency"):
        if frame[col].isna().any() or frame[col].astype(str).str.strip().eq("").any():
            raise ValueError("book.missing_values")
        frame[col] = frame[col].astype(str).str.strip()
    if frame.id.duplicated().any():
        raise ValueError("book.duplicates")
    if not frame.asset_class.isin(ASSET_CLASSES).all():
        raise ValueError("book.asset_class")
    if not frame.currency.isin(CURRENCIES).all():
        raise ValueError("book.currency")
    for col in ("quantity", "price", "multiplier", "strike", "maturity", "volatility", "coupon", "yield_rate"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").astype(float)
        if not np.isfinite(frame[col]).all():
            raise ValueError("book.numeric")
    if (frame[["price", "multiplier", "maturity", "strike", "volatility"]] <= 0).any().any():
        raise ValueError("book.positive")
    if not frame.mark_mode.isin(['Book','Market']).all():raise ValueError('book.mark_mode')
    if ((frame.asset_class=='Bond') & ~np.isclose(frame.multiplier,.01)).any():raise ValueError('book.bond_multiplier')
    cash=frame.asset_class.isin(['Cash','FX'])
    if (cash & (~np.isclose(frame.price,1.) | ~np.isclose(frame.multiplier,1.))).any():raise ValueError('book.cash_unit')
    fx_underlying=frame.underlying.astype(str).map(lambda x:len(x)==6 and x[:3] in CURRENCIES and x[3:] in CURRENCIES)
    if ((frame.asset_class=='Option')&fx_underlying).any():raise ValueError('book.fx_option')
    if not frame.option_type.isin(["Call", "Put"]).all():
        raise ValueError("book.option_type")
    if frame.weight.notna().any():
        w = pd.to_numeric(frame.weight, errors="coerce")
        if not np.isfinite(w).all() or not np.isclose(w.sum(), 1., atol=1e-6):
            raise ValueError("book.weights")
    return frame[list(FIELDS)]

def replace_book(state, frame, source="USER INPUT"):
    validated = validate_book(frame)
    state.book.positions = validated
    state.book.source = source
    state.book.revision += 1
    state.risk.results.clear()

def get_state():
    if "terminal" not in st.session_state:
        state = TerminalState(demo_book())
        state.ui.language = st.query_params.get("lang", "en") if st.query_params.get("lang", "en") in ("en", "fr") else "en"
        state.ui.theme = st.query_params.get("theme", "dark") if st.query_params.get("theme", "dark") in ("dark", "light") else "dark"
        st.session_state.terminal = state
    state = st.session_state.terminal
    # Preserve books in already-open sessions across compatible app upgrades.
    for name in ("structured_terms", "financing_terms", "lending_terms"):
        if not hasattr(state.book, name):setattr(state.book, name, {})
    return state
