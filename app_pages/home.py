import streamlit as st


MODULES = [
    {
        "title": "Fixed Income Risk",
        "caption": "Risk review for bond portfolios.",
        "description": "Duration, convexity, DV01, curve shocks, bucket risk decomposition, Excel risk report.",
        "page": "Fixed Income Risk",
    },
    {
        "title": "Repo & Securities Lending",
        "caption": "Funding, collateral, and margin analysis.",
        "description": "Repo cashflows, haircuts, collateral shocks, margin calls, borrow fee, specialness.",
        "page": "Repo & Securities Lending",
    },
    {
        "title": "Structured Products",
        "caption": "Autocallable note scenario analytics.",
        "description": "Athena/Phoenix payoff, worst-of basket, Monte Carlo proxy, barrier risk, Excel report.",
        "page": "Structured Products",
    },
    {
        "title": "Portfolio Risk",
        "caption": "AM/risk portfolio review.",
        "description": "VaR, CVaR, drawdown, risk contribution, stress scenarios, R analytics, Excel report.",
        "page": "Portfolio Risk",
    },
    {
        "title": "Cross-Asset Dashboard",
        "caption": "Manager view and risk synthesis.",
        "description": "Rates, financing, structured products, portfolio risk, stress scenarios, risk heatmap.",
        "page": "Cross-Asset Dashboard",
    },
]


def _go_to_page(page_name: str) -> None:
    st.session_state["selected_page"] = page_name
    st.rerun()


def _render_workflow_card(number: int, title: str, description: str) -> None:
    with st.container(border=True):
        st.caption(str(number))
        st.markdown(f"### {title}")
        st.write(description)


def _render_module_card(module: dict[str, str]) -> None:
    with st.container(border=True):
        left, middle, right = st.columns([2.2, 3.2, 1.3])

        with left:
            st.markdown(f"### {module['title']}")
            st.caption(module["caption"])

        with middle:
            st.write(module["description"])

        with right:
            st.markdown("**Status**")
            st.success("Live")
            if st.button(
                "Open module",
                key=f"open_{module['page']}",
                width="stretch",
            ):
                _go_to_page(module["page"])


def render() -> None:
    st.title("Multi-Asset Desk Utility Platform")
    st.caption("Desk-ready analytics for pricing proxies, risk, scenarios, interpretation, and exports.")

    st.write(
        "This platform is designed to convert market, portfolio, trade, and product inputs into "
        "practical desk outputs: stress tests, P&L explainers, DV01 decomposition, repo margin analytics, "
        "structured product scenarios, portfolio risk reports, and cross-asset market snapshots."
    )

    st.warning(
        "Educational/proxy analytics only. Not investment advice, not a trading bot, and not bank-grade pricing.",
        icon="⚠️",
    )

    st.subheader("Desk Workflow")

    workflow_cols = st.columns(5)

    workflow_steps = [
        ("Input", "Upload or enter product, trade, market, or portfolio data."),
        ("Calculation", "Run transparent pricing, risk, or performance calculations."),
        ("Scenario", "Stress key variables such as rates, spot, volatility, spreads, or haircuts."),
        ("Interpretation", "Explain the main drivers and risk concentration."),
        ("Export", "Generate reusable Excel reports or factsheets."),
    ]

    for idx, (title, description) in enumerate(workflow_steps, start=1):
        with workflow_cols[idx - 1]:
            _render_workflow_card(idx, title, description)

    st.subheader("Modules")

    for module in MODULES:
        _render_module_card(module)
