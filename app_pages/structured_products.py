import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from engines.structured_products_engine import (
    AutocallableTerms,
    build_standard_scenario_paths,
    calculate_autocallable_payoff,
    calculate_scenario_table,
    generate_structured_product_commentary,
    payoff_result_to_dict,
)


def _format_currency(value: float) -> str:
    return f"{value:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def render() -> None:
    render_module_header(
        title="Structured Products",
        caption="Autocallable note analytics: payoff logic, scenarios, barrier risk, and desk explanations.",
        objective=(
            "Objective: convert Athena and Phoenix terms into transparent payoff outcomes, "
            "scenario analysis, and client/desk-ready explanations."
        ),
    )

    st.subheader("Product Terms")

    c1, c2, c3 = st.columns(3)

    with c1:
        product_type = st.selectbox("Product type", ["Athena", "Phoenix"])
        nominal = st.number_input(
            "Nominal",
            min_value=1_000.0,
            value=1_000_000.0,
            step=50_000.0,
        )
        number_of_observations = st.number_input(
            "Number of observations",
            min_value=1,
            max_value=12,
            value=4,
            step=1,
        )

    with c2:
        coupon_rate_pct = st.number_input(
            "Coupon per observation (%)",
            min_value=0.0,
            max_value=20.0,
            value=2.0,
            step=0.25,
        )
        autocall_barrier_pct = st.number_input(
            "Autocall barrier (% of initial)",
            min_value=50.0,
            max_value=150.0,
            value=100.0,
            step=1.0,
        )
        coupon_barrier_pct = st.number_input(
            "Coupon barrier (% of initial)",
            min_value=30.0,
            max_value=150.0,
            value=70.0,
            step=1.0,
        )

    with c3:
        protection_barrier_pct = st.number_input(
            "Protection barrier (% of initial)",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
        )
        memory_coupon = st.checkbox(
            "Memory coupon",
            value=True,
            disabled=product_type == "Athena",
            help="Memory coupon applies to Phoenix in this simplified model.",
        )

    terms = AutocallableTerms(
        product_type=product_type,
        nominal=float(nominal),
        coupon_rate_per_period=coupon_rate_pct / 100.0,
        autocall_barrier=autocall_barrier_pct / 100.0 - 1.0,
        coupon_barrier=coupon_barrier_pct / 100.0 - 1.0,
        protection_barrier=protection_barrier_pct / 100.0 - 1.0,
        memory_coupon=bool(memory_coupon if product_type == "Phoenix" else False),
    )

    st.subheader("Custom Performance Path")

    st.caption(
        "Enter performance versus initial level for each observation. Example: -20 means underlying is down 20%."
    )

    path_cols = st.columns(int(number_of_observations))
    performance_path = []

    for idx, col in enumerate(path_cols, start=1):
        with col:
            perf_pct = st.number_input(
                f"Obs {idx} perf (%)",
                min_value=-99.0,
                max_value=200.0,
                value=-10.0 if idx < int(number_of_observations) else -20.0,
                step=5.0,
            )
            performance_path.append(perf_pct / 100.0)

    result = calculate_autocallable_payoff(terms, performance_path)
    result_dict = payoff_result_to_dict(result)
    commentary = generate_structured_product_commentary(terms, result)

    st.subheader("Payoff Summary")

    s1, s2, s3, s4, s5 = st.columns(5)

    s1.metric("Autocalled?", "Yes" if result.autocalled else "No")
    s2.metric("Autocall Obs", result.autocall_observation if result.autocall_observation else "N/A")
    s3.metric("Coupons Paid", _format_currency(result.total_coupons_paid))
    s4.metric("Total Payoff", _format_currency(result.total_payoff))
    s5.metric("Payoff Return", _format_percent(result.payoff_return))

    with st.container(border=True):
        for comment in commentary:
            st.markdown(f"- {comment}")

    st.subheader("Custom Path Result Details")

    result_table = pd.DataFrame(
        [{"Metric": key, "Value": str(value)} for key, value in result_dict.items()]
    )

    st.dataframe(result_table, use_container_width=True)

    st.subheader("Standard Scenario Table")

    scenario_paths = build_standard_scenario_paths(int(number_of_observations))
    scenario_df = calculate_scenario_table(terms, scenario_paths)

    st.dataframe(
        scenario_df.style.format(
            {
                "final_performance": "{:.2%}",
                "total_coupons_paid": "{:,.0f}",
                "redemption_amount": "{:,.0f}",
                "capital_pnl": "{:,.0f}",
                "total_payoff": "{:,.0f}",
                "total_pnl": "{:,.0f}",
                "payoff_return": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

    fig = px.bar(
        scenario_df,
        x="scenario",
        y="total_pnl",
        color="protection_barrier_breached",
        title="Total P&L by Scenario",
        labels={"scenario": "Scenario", "total_pnl": "Total P&L"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Methodology Notes")

    st.markdown(
        """
        - Performance values are measured versus initial level.
        - Autocall barrier at 100% of initial means performance must be at least 0%.
        - Protection barrier at 60% of initial means final performance below -40% creates capital loss.
        - Athena coupon is simplified as accumulated coupon paid only if autocall occurs.
        - Phoenix coupon can be paid periodically if the coupon barrier is met.
        - Phoenix memory coupon allows missed coupons to be recovered later if the coupon condition is met.
        - Worst-of basket and Monte Carlo layers will be added later.
        - This module is deterministic payoff logic, not bank-grade pricing.
        """
    )
