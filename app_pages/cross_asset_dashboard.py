import streamlit as st


def render() -> None:
    st.title("Cross-Asset Dashboard")
    st.caption("Market monitoring dashboard for equities, rates, FX, commodities, volatility, and credit proxies.")

    st.info("This module will be implemented after the core risk modules.")

    st.subheader("Planned Desk Outputs")
    st.markdown(
        """
        - Equity index moves
        - Rates moves
        - FX moves
        - Commodity moves
        - Volatility regime
        - Credit proxy moves
        - Risk-on / risk-off score
        - Market narrative
        - Morning market snapshot export
        """
    )
