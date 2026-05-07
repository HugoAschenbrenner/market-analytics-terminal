import streamlit as st


def render() -> None:
    st.title("Repo & Securities Lending")
    st.caption("Funding, collateral, haircut, margin call, and borrow fee analytics.")

    st.info("This module will be implemented after the Fixed Income Risk module.")

    st.subheader("Planned Desk Outputs")
    st.markdown(
        """
        - Repo cash amount
        - Repo interest
        - Repurchase amount
        - Haircut impact
        - Collateral shock
        - Margin call / margin surplus
        - Securities lending borrow fee
        - Rebate and collateralization
        - Specialness indicator
        - Financing and margin report
        """
    )
