import streamlit as st

from app_pages import (
    home,
    fixed_income,
    repo_sec_lending,
    structured_products,
    portfolio_risk,
    cross_asset_dashboard,
)

st.set_page_config(
    page_title="Multi-Asset Desk Utility Platform",
    page_icon="📊",
    layout="wide",
)

PAGES = {
    "Home": home.render,
    "Fixed Income Risk": fixed_income.render,
    "Repo & Securities Lending": repo_sec_lending.render,
    "Structured Products": structured_products.render,
    "Portfolio Risk": portfolio_risk.render,
    "Cross-Asset Dashboard": cross_asset_dashboard.render,
}

st.sidebar.title("Market Analytics Terminal")
st.sidebar.caption("Desk-ready analytics toolkit")

selected_page = st.sidebar.radio(
    "Select module",
    list(PAGES.keys()),
)

st.sidebar.divider()
st.sidebar.caption(
    "Educational/proxy analytics only. "
    "Not investment advice or bank-grade pricing."
)

PAGES[selected_page]()
