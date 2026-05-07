import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from engines.fixed_income_engine import (
    calculate_bond_risk_metrics,
    estimate_pnl_from_yield_move,
    load_bond_data,
    portfolio_summary_to_dict,
    summarize_portfolio,
)


def _format_currency(value: float) -> str:
    return f"{value:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def render() -> None:
    render_module_header(
        title="Fixed Income Risk",
        caption="Bond portfolio risk analytics: duration, convexity, DV01, curve shocks, and risk reports.",
        objective=(
            "Objective: help a sales, trader, PM, or risk analyst understand where bond portfolio risk "
            "is concentrated and how the portfolio reacts to yield moves."
        ),
    )

    st.subheader("Input Data")

    uploaded_file = st.file_uploader(
        "Upload a bond portfolio CSV",
        type=["csv"],
        help="If no file is uploaded, the app uses the synthetic sample bond dataset.",
    )

    if uploaded_file is not None:
        bonds = pd.read_csv(uploaded_file)
        st.info("Using uploaded portfolio.")
    else:
        bonds = load_bond_data("data/sample_bonds.csv")
        st.info("Using default synthetic sample bond dataset.")

    with st.expander("Raw bond data", expanded=False):
        st.dataframe(bonds, use_container_width=True)

    risk_df = calculate_bond_risk_metrics(bonds)
    summary = summarize_portfolio(risk_df)
    summary_dict = portfolio_summary_to_dict(summary)

    st.subheader("Portfolio Summary")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Market Value", _format_currency(summary_dict["total_market_value"]))
    c2.metric("WA Yield", _format_percent(summary_dict["weighted_average_yield"]))
    c3.metric(
        "WA Mod Duration",
        f"{summary_dict['weighted_average_modified_duration']:.2f}",
    )
    c4.metric("Total DV01", _format_currency(summary_dict["total_dv01"]))
    c5.metric("Bonds", f"{summary_dict['number_of_bonds']}")

    st.subheader("Bond-Level Risk Metrics")

    display_columns = [
        "bond_id",
        "issuer",
        "currency",
        "clean_price",
        "accrued_interest_per_100",
        "dirty_price",
        "yield_to_maturity",
        "years_to_maturity",
        "modified_duration",
        "convexity",
        "market_value",
        "dv01",
        "curve_bucket",
        "rating",
        "sector",
    ]

    st.dataframe(
        risk_df[display_columns].style.format(
            {
                "clean_price": "{:.2f}",
                "accrued_interest_per_100": "{:.4f}",
                "dirty_price": "{:.4f}",
                "yield_to_maturity": "{:.2%}",
                "years_to_maturity": "{:.2f}",
                "modified_duration": "{:.2f}",
                "convexity": "{:.2f}",
                "market_value": "{:,.0f}",
                "dv01": "{:,.0f}",
            }
        ),
        use_container_width=True,
    )

    st.subheader("DV01 by Bond")

    fig = px.bar(
        risk_df.sort_values("dv01", ascending=False),
        x="bond_id",
        y="dv01",
        color="curve_bucket",
        title="DV01 by Bond",
        labels={"dv01": "DV01", "bond_id": "Bond"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Simple Yield Move P&L")

    yield_move_bps = st.slider(
        "Yield move in bps",
        min_value=-100,
        max_value=100,
        value=25,
        step=5,
    )

    pnl = estimate_pnl_from_yield_move(
        dv01=summary.total_dv01,
        yield_move_bps=yield_move_bps,
    )

    st.metric(
        f"Estimated P&L for {yield_move_bps:+} bps move",
        _format_currency(pnl),
    )

    st.caption(
        "Convention: DV01 is positive and represents the approximate gain for a 1 bp fall in yield. "
        "Therefore, a positive yield move produces negative estimated P&L."
    )

    st.subheader("Methodology Notes")

    st.markdown(
        """
        - Clean price is quoted per 100 notional.
        - Dirty price = clean price + accrued interest per 100.
        - Market value = clean price / 100 × notional.
        - Duration and convexity are approximate and based on yield-implied cashflows.
        - DV01 = modified duration × market value × 0.0001.
        - This MVP does not yet build a full discount curve or use bond-specific day-count conventions.
        """
    )
