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
    equity_derivatives,
)

PAGES = {
    "Home": home.render,
    "Equity Derivatives": equity_derivatives.render,
    "Fixed Income Risk": fixed_income.render,
    "Repo & Securities Lending": repo_sec_lending.render,
    "Structured Products": structured_products.render,
    "Portfolio Risk": portfolio_risk.render,
    "Cross-Asset Dashboard": cross_asset_dashboard.render,
}

PAGE_SLUGS = {
    "Home": "home",
    "Equity Derivatives": "equity-derivatives",
    "Fixed Income Risk": "fixed-income-risk",
    "Repo & Securities Lending": "repo-sec-lending",
    "Structured Products": "structured-products",
    "Portfolio Risk": "portfolio-risk",
    "Cross-Asset Dashboard": "cross-asset-dashboard",
}

SLUG_TO_PAGE = {slug: page for page, slug in PAGE_SLUGS.items()}

PAGE_ICONS = {
    "Home": "⌂",
    "Equity Derivatives": "Δ",
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


def _navigate_v1(slug: str) -> None:
    st.query_params['page'] = slug


def render_sidebar_nav_link(page_name: str, selected_page: str) -> None:
    # Native callbacks preserve analytical inputs between module visits.
    st.button(f"{PAGE_ICONS.get(page_name, '')} {page_name}",
              key='v1-nav-'+PAGE_SLUGS[page_name], width='stretch',
              type='primary' if page_name==selected_page else 'secondary',
              on_click=_navigate_v1,args=(PAGE_SLUGS[page_name],))


def render():
    apply_global_styles()
    from components.version_switch import render_version_switch
    render_version_switch("v1")
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
            use_container_width=True,
        )
        st.link_button(
            "LinkedIn",
            "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
            use_container_width=True,
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
