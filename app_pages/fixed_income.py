import streamlit as st


def render() -> None:
    st.title("Fixed Income Risk")
    st.caption("Bond portfolio risk analytics: duration, convexity, DV01, curve shocks, and risk reports.")

    st.info("This module will be implemented after the shared scenario engine.")

    st.subheader("Planned Desk Outputs")
    st.markdown(
        """
        - Clean price / dirty price
        - Accrued interest
        - YTM
        - Modified duration
        - Convexity
        - DV01
        - DV01 by maturity bucket
        - Curve shock P&L
        - Spread shock P&L
        - Hedge approximation
        - Excel risk report
        """
    )
