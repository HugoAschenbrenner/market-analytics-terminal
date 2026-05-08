import html

import streamlit as st

from app_pages.theme import apply_global_styles
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

apply_global_styles()

PAGES = {
    "Home": home.render,
    "Fixed Income Risk": fixed_income.render,
    "Repo & Securities Lending": repo_sec_lending.render,
    "Structured Products": structured_products.render,
    "Portfolio Risk": portfolio_risk.render,
    "Cross-Asset Dashboard": cross_asset_dashboard.render,
}

PAGE_SLUGS = {
    "Home": "home",
    "Fixed Income Risk": "fixed-income-risk",
    "Repo & Securities Lending": "repo-sec-lending",
    "Structured Products": "structured-products",
    "Portfolio Risk": "portfolio-risk",
    "Cross-Asset Dashboard": "cross-asset-dashboard",
}

SLUG_TO_PAGE = {slug: page for page, slug in PAGE_SLUGS.items()}

PAGE_ICONS = {
    "Home": "⌂",
    "Fixed Income Risk": "◔",
    "Repo & Securities Lending": "⇄",
    "Structured Products": "◇",
    "Portfolio Risk": "▣",
    "Cross-Asset Dashboard": "◎",
}


def _get_query_page_slug() -> str:
    page_slug = st.query_params.get("page", "home")

    if isinstance(page_slug, list):
        page_slug = page_slug[0] if page_slug else "home"

    if page_slug not in SLUG_TO_PAGE:
        return "home"

    return page_slug


def render_sidebar_nav_link(page_name: str, selected_page: str) -> None:
    icon = PAGE_ICONS.get(page_name, "•")
    slug = PAGE_SLUGS[page_name]
    active_class = " mat-sidebar-active" if page_name == selected_page else ""

    safe_page_name = html.escape(page_name)
    safe_icon = html.escape(icon)

    st.markdown(
        f"""
        <a class="mat-sidebar-link{active_class}" href="?page={slug}" target="_self">
            <span class="mat-sidebar-icon">{safe_icon}</span>
            <span class="mat-sidebar-label">{safe_page_name}</span>
        </a>
        """,
        unsafe_allow_html=True,
    )


selected_slug = _get_query_page_slug()
selected_page = SLUG_TO_PAGE[selected_slug]

with st.sidebar:
    st.title("Market Analytics Terminal")
    st.caption("Personal multi-asset analytics project")

    st.caption("Built by Hugo Aschenbrenner")
    st.caption("SKEMA MSc Financial Markets & Investments")

    st.link_button(
        "GitHub",
        "https://github.com/HugoAschenbrenner/market-analytics-terminal",
        width="stretch",
    )
    st.link_button(
        "LinkedIn",
        "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
        width="stretch",
    )

    st.divider()

    st.markdown("##### Command Menu")
    st.caption("Open an analytics module")

    for page_name in PAGES:
        render_sidebar_nav_link(page_name, selected_page)

    st.divider()

    st.markdown("### Build standard")
    st.caption("Input → Calculation → Scenario → Interpretation → Export")

    st.divider()

    st.caption(
        "Educational/proxy analytics only. Not investment advice, "
        "not a trading bot, and not bank-grade pricing."
    )

PAGES[selected_page]()
