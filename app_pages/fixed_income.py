import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from engines.fixed_income_engine import (
    calculate_bond_risk_metrics,
    calculate_dv01_by_bucket,
    calculate_hedge_units,
    calculate_scenario_pnl,
    estimate_pnl_from_yield_move,
    generate_fixed_income_commentary,
    identify_worst_scenario,
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
            "is concentrated and how the portfolio reacts to yield curve and spread shocks."
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

    bucket_df = calculate_dv01_by_bucket(risk_df)
    scenario_df = calculate_scenario_pnl(risk_df)
    worst_scenario = identify_worst_scenario(scenario_df)
    commentary = generate_fixed_income_commentary(risk_df, bucket_df, scenario_df)

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

    st.subheader("Desk Commentary")

    with st.container(border=True):
        for comment in commentary:
            st.markdown(f"- {comment}")

    st.subheader("DV01 Bucket Decomposition")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.dataframe(
            bucket_df.style.format(
                {
                    "market_value": "{:,.0f}",
                    "dv01": "{:,.0f}",
                    "pct_total_dv01": "{:.1%}",
                }
            ),
            use_container_width=True,
        )

    with c2:
        fig_bucket = px.bar(
            bucket_df,
            x="curve_bucket",
            y="dv01",
            title="DV01 by Curve Bucket",
            labels={"curve_bucket": "Curve Bucket", "dv01": "DV01"},
        )
        st.plotly_chart(fig_bucket, use_container_width=True)

    st.subheader("Scenario P&L")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.dataframe(
            scenario_df.style.format(
                {
                    "duration_pnl": "{:,.0f}",
                    "convexity_pnl": "{:,.0f}",
                    "estimated_pnl": "{:,.0f}",
                }
            ),
            use_container_width=True,
        )

    with c2:
        st.metric(
            "Worst Scenario",
            worst_scenario["scenario_name"],
            delta=_format_currency(worst_scenario["estimated_pnl"]),
            delta_color="inverse",
        )
        st.caption(worst_scenario["shock_description"])

    fig_scenarios = px.bar(
        scenario_df,
        x="scenario_name",
        y="estimated_pnl",
        color="risk_factor",
        title="Estimated P&L by Scenario",
        labels={"scenario_name": "Scenario", "estimated_pnl": "Estimated P&L"},
    )
    st.plotly_chart(fig_scenarios, use_container_width=True)

    st.subheader("Simple Hedge Approximation")

    st.caption(
        "This approximates hedge size using DV01 only. It is a risk sizing proxy, not an execution recommendation."
    )

    hedge_dv01 = st.number_input(
        "Hedge instrument DV01 per unit",
        min_value=1.0,
        value=75.0,
        step=5.0,
        help="Example: approximate DV01 of one futures contract or hedge instrument unit.",
    )

    hedge_units = calculate_hedge_units(
        portfolio_dv01=summary.total_dv01,
        hedge_instrument_dv01=hedge_dv01,
    )

    st.metric("Approximate hedge units", f"{hedge_units:,.1f}")

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

    st.subheader("Custom Parallel Yield Move P&L")

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
        - Scenario P&L uses duration/convexity approximation.
        - Credit spread shock uses modified duration as a spread-duration proxy.
        - Hedge approximation uses portfolio DV01 / hedge instrument DV01.
        - This MVP does not yet build a full discount curve or use bond-specific day-count conventions.
        """
    )
