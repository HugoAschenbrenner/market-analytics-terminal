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

if st.session_state["selected_page"] not in PAGES:
    st.session_state["selected_page"] = "Home"

with st.sidebar:
    st.title("Market Analytics Terminal")
    st.caption("Personal multi-asset analytics project")

    current_page = st.session_state["selected_page"]
    current_index = list(PAGES.keys()).index(current_page)

    sidebar_selection = st.radio(
        "Select module",
        list(PAGES.keys()),
        index=current_index,
    )

    st.session_state["selected_page"] = sidebar_selection

    st.divider()

    st.markdown("### Build standard")
    st.caption("Input → Calculation → Scenario → Interpretation → Export")

    st.divider()

    st.caption(
        "Educational/proxy analytics only. Not investment advice, "
        "not a trading bot, and not bank-grade pricing."
    )

    st.divider()

    st.markdown("### Project")
    st.caption("Built by Hugo Aschenbrenner")
    st.caption("SKEMA MSc Financial Markets & Investments")
    st.link_button(
        "GitHub repository",
        "https://github.com/HugoAschenbrenner/market-analytics-terminal",
        width="stretch",
    )
    st.link_button(
        "LinkedIn profile",
        "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
        width="stretch",
    )

selected_page = st.session_state["selected_page"]
PAGES[selected_page]()
