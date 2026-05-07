import streamlit as st


def render() -> None:
    st.title("Multi-Asset Desk Utility Platform")
    st.caption("Desk-ready analytics for pricing proxies, risk, scenarios, interpretation, and exports.")

    st.markdown(
        """
        This platform is designed to convert market and portfolio inputs into practical desk outputs:
        stress tests, P&L explainers, DV01 decomposition, repo margin analytics, structured product scenarios,
        portfolio risk reports, and cross-asset market snapshots.
        """
    )

    st.warning(
        "Educational/proxy analytics only. Not investment advice, not a trading bot, and not bank-grade pricing."
    )

    st.subheader("Desk Workflow")

    cols = st.columns(5)
    steps = [
        ("1", "Input"),
        ("2", "Calculation"),
        ("3", "Scenario analysis"),
        ("4", "Interpretation"),
        ("5", "Export"),
    ]

    for col, (number, label) in zip(cols, steps):
        with col:
            st.metric(number, label)

    st.subheader("Modules")

    modules = [
        (
            "Fixed Income Risk",
            "Duration, convexity, DV01, curve shocks, bucket risk decomposition, and Excel risk reports.",
        ),
        (
            "Repo & Securities Lending",
            "Haircuts, repo cashflows, collateral shocks, margin calls, borrow fee, and specialness analytics.",
        ),
        (
            "Structured Products",
            "Athena/Phoenix payoff logic, autocall probability, barrier breach risk, worst-of scenarios, factsheets.",
        ),
        (
            "Portfolio Risk",
            "VaR, Expected Shortfall, drawdown, tracking error, benchmark comparison, and R analytics layer.",
        ),
        (
            "Cross-Asset Dashboard",
            "Equities, rates, FX, commodities, volatility, credit proxies, and market regime snapshots.",
        ),
    ]

    for title, description in modules:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.write(description)
