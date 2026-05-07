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

CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.metric-card {
    padding: 1.1rem;
    border: 1px solid rgba(49, 51, 63, 0.15);
    border-radius: 0.75rem;
    background-color: rgba(250, 250, 250, 0.65);
}

.module-caption {
    color: #6c757d;
    font-size: 0.92rem;
}

.small-muted {
    color: #6c757d;
    font-size: 0.85rem;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
st.sidebar.markdown("### Build standard")
st.sidebar.caption("Input → Calculation → Scenario → Interpretation → Export")

st.sidebar.divider()
st.sidebar.caption(
    "Educational/proxy analytics only. Not investment advice, not a trading bot, "
    "and not bank-grade pricing."
)

PAGES[selected_page]()
