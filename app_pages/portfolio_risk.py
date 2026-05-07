import streamlit as st


def render() -> None:
    st.title("Portfolio Risk")
    st.caption("Portfolio risk, benchmark-relative analytics, VaR, Expected Shortfall, and R integration.")

    st.info("This module will be implemented after the structured product module.")

    st.subheader("Planned Desk Outputs")
    st.markdown(
        """
        - Annualized return
        - Annualized volatility
        - Sharpe ratio
        - Max drawdown
        - Historical VaR
        - Expected Shortfall
        - Tracking error
        - Information ratio
        - Benchmark comparison
        - R-based portfolio analytics
        - Portfolio review report
        """
    )
