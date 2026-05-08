import streamlit as st

from app_pages import (
    cross_asset_dashboard,
    fixed_income,
    home,
    portfolio_risk,
    repo_sec_lending,
    structured_products,
)

st.set_page_config(
    page_title="Market Analytics Terminal",
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

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Home"

with st.sidebar:
    st.title("Market Analytics Terminal")
    st.caption("Desk-ready analytics toolkit")

    st.radio(
        "Select module",
        list(PAGES.keys()),
        key="selected_page",
    )

    st.divider()

    st.markdown("### Build standard")
    st.caption("Input → Calculation → Scenario → Interpretation → Export")

    st.divider()

    st.caption(
        "Educational/proxy analytics only. Not investment advice, "
        "not a trading bot, and not bank-grade pricing."
    )

selected_page = st.session_state["selected_page"]
PAGES[selected_page]()
