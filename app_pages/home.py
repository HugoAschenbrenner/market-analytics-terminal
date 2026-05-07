import streamlit as st

from app_pages.common import render_workflow


def render() -> None:
    st.title("Multi-Asset Desk Utility Platform")
    st.caption("Desk-ready analytics for pricing proxies, risk, scenarios, interpretation, and exports.")

    st.markdown(
        """
        This platform is designed to convert market, portfolio, trade, and product inputs into practical
        desk outputs: stress tests, P&L explainers, DV01 decomposition, repo margin analytics,
        structured product scenarios, portfolio risk reports, and cross-asset market snapshots.
        """
    )

    st.warning(
        "Educational/proxy analytics only. Not investment advice, not a trading bot, and not bank-grade pricing."
    )

    render_workflow()

    st.subheader("Modules")

    modules = [
        {
            "title": "Fixed Income Risk",
            "desk_use": "Risk review for bond portfolios.",
            "outputs": "Duration, convexity, DV01, curve shocks, bucket risk decomposition, Excel risk report.",
            "status": "Next build priority",
        },
        {
            "title": "Repo & Securities Lending",
            "desk_use": "Funding, collateral, and margin analysis.",
            "outputs": "Repo cashflows, haircuts, collateral shocks, margin calls, borrow fee, specialness.",
            "status": "Planned",
        },
        {
            "title": "Structured Products",
            "desk_use": "Autocallable note scenario analytics.",
            "outputs": "Athena/Phoenix payoff, autocall probability, barrier risk, worst-of stress, factsheet.",
            "status": "Planned",
        },
        {
            "title": "Portfolio Risk",
            "desk_use": "AM/risk portfolio review.",
            "outputs": "VaR, Expected Shortfall, tracking error, drawdown, benchmark comparison, R analytics.",
            "status": "Planned",
        },
        {
            "title": "Cross-Asset Dashboard",
            "desk_use": "Morning market monitoring.",
            "outputs": "Equities, rates, FX, commodities, volatility, credit proxies, market regime narrative.",
            "status": "Planned",
        },
    ]

    for module in modules:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 3, 1])
            with c1:
                st.markdown(f"### {module['title']}")
                st.caption(module["desk_use"])
            with c2:
                st.write(module["outputs"])
            with c3:
                st.info(module["status"])

    st.subheader("Design Principle")
    st.markdown(
        """
        Every module must go beyond calculation. The target standard is:
        **calculation → visualization → scenario analysis → interpretation → export**.
        """
    )
