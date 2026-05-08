import streamlit as st


PAGE_SLUGS = {
    "Fixed Income Risk": "fixed-income-risk",
    "Repo & Securities Lending": "repo-sec-lending",
    "Structured Products": "structured-products",
    "Portfolio Risk": "portfolio-risk",
    "Cross-Asset Dashboard": "cross-asset-dashboard",
}


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


EXECUTIVE_INSIGHTS = [
    {
        "risk": "Rates concentration",
        "why": "Fixed income exposure is summarized through DV01, curve buckets, and shock P&L.",
        "next_check": "Review the Fixed Income Risk module to identify long-end duration concentration.",
        "page": "Fixed Income Risk",
    },
    {
        "risk": "Collateral and funding stress",
        "why": "Repo margin calls are driven by collateral depreciation and haircut widening.",
        "next_check": "Open Repo & Securities Lending to stress collateral value and haircut assumptions.",
        "page": "Repo & Securities Lending",
    },
    {
        "risk": "Worst-of barrier risk",
        "why": "Structured product downside can be dominated by the weakest underlying in the basket.",
        "next_check": "Open Structured Products to review worst-of scenarios and Monte Carlo barrier risk.",
        "page": "Structured Products",
    },
]


QUESTIONS = [
    "Where is duration risk concentrated in a bond portfolio?",
    "How much margin call is created by collateral depreciation and haircut widening?",
    "What is the payoff profile of a Phoenix or Athena autocallable?",
    "How does worst-of basket dispersion affect barrier risk?",
    "Which asset contributes most to portfolio volatility?",
    "Which cross-asset stress scenario creates the largest proxy loss?",
]


def _go_to_page(page_name: str) -> None:
    slug = PAGE_SLUGS.get(page_name, "home")
    st.query_params["page"] = slug
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
            st.success("Implemented")
            if st.button(
                "Open module",
                key=f"open_{module['page']}",
                width="stretch",
            ):
                _go_to_page(module["page"])


def _render_executive_insight_card(insight: dict[str, str], index: int) -> None:
    with st.container(border=True):
        st.markdown(f"#### {index}. {insight['risk']}")
        st.write(insight["why"])
        st.caption(f"Recommended next check: {insight['next_check']}")

        if st.button(
            f"Open {insight['page']}",
            key=f"executive_insight_{index}_{insight['page']}",
            width="stretch",
        ):
            _go_to_page(insight["page"])


def render() -> None:
    st.title("Multi-Asset Desk Utility Platform")
    st.caption("Personal multi-asset analytics project built by Hugo Aschenbrenner.")

    st.write(
        "This platform converts market, portfolio, trade, and product inputs into practical desk outputs: "
        "stress tests, P&L explainers, DV01 decomposition, repo margin analytics, structured product scenarios, "
        "portfolio risk reports, R performance analytics, and cross-asset market snapshots."
    )

    st.warning(
        "Educational/proxy analytics only. Not investment advice, not a trading bot, and not bank-grade pricing.",
        icon="⚠️",
    )

    st.info(
        "Built by Hugo Aschenbrenner, MSc Financial Markets & Investments student at SKEMA Business School. "
        "This project was built to turn market concepts from fixed income, repo/securities lending, "
        "structured products, and portfolio risk into a practical desk-style analytics workflow.",
        icon="👤",
    )

    st.subheader("Executive Snapshot")

    snapshot_cols = st.columns(5)

    snapshot_items = [
        ("Modules", "5", "Fixed income, repo, structured products, portfolio risk, cross-asset."),
        ("Tests", "150+", "Automated checks across engines, reports, UI integration, and documentation."),
        ("Reports", "4", "Excel exports for fixed income, financing, structured products, and portfolio risk."),
        ("Languages", "Python/R", "Streamlit terminal with R portfolio analytics companion."),
        ("Data policy", "Synthetic", "Synthetic sample data and user-provided inputs only."),
    ]

    for col, (label, value, help_text) in zip(snapshot_cols, snapshot_items):
        with col:
            st.metric(label, value)
            st.caption(help_text)

    st.subheader("What This Terminal Can Answer")

    question_cols = st.columns(2)

    for idx, question in enumerate(QUESTIONS):
        with question_cols[idx % 2]:
            with st.container(border=True):
                st.write(f"• {question}")

    st.subheader("Top 3 Risk Insights")

    insight_cols = st.columns(3)

    for idx, insight in enumerate(EXECUTIVE_INSIGHTS, start=1):
        with insight_cols[idx - 1]:
            _render_executive_insight_card(insight, idx)

    st.subheader("About This Project")

    about_col_1, about_col_2, about_col_3 = st.columns(3)

    with about_col_1:
        with st.container(border=True):
            st.markdown("#### Project intent")
            st.write(
                "Build a transparent multi-asset analytics terminal that connects market theory, "
                "risk decomposition, scenario analysis, and practical reporting."
            )

    with about_col_2:
        with st.container(border=True):
            st.markdown("#### Data policy")
            st.write(
                "The app uses synthetic sample data and user-provided inputs only. "
                "No proprietary client, employer, or confidential market data is included."
            )

    with about_col_3:
        with st.container(border=True):
            st.markdown("#### Build facts")
            st.write(
                "Python, Streamlit, R companion analytics, Excel exports, modular engines, "
                "GitHub documentation, screenshots, and 150+ automated tests."
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
