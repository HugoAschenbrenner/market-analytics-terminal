import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from reports.excel_exporter import generate_structured_products_report
from engines.structured_products_engine import (
    AutocallableTerms,
    build_standard_basket_scenario_paths,
    build_standard_scenario_paths,
    calculate_autocallable_payoff,
    calculate_basket_scenario_table,
    calculate_monte_carlo_results_table,
    calculate_scenario_table,
    generate_monte_carlo_commentary,
    generate_structured_product_commentary,
    generate_worst_of_basket_commentary,
    payoff_result_to_dict,
    simulate_single_underlying_paths,
    simulate_worst_of_basket_paths,
    summarize_monte_carlo_results,
)


def _format_currency(value: float) -> str:
    return f"{value:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def render() -> None:
    render_module_header(
        title="Structured Products",
        caption="Autocallable note analytics: payoff logic, worst-of scenarios, Monte Carlo proxies, barrier risk, and desk explanations.",
        objective=(
            "Objective: convert Athena and Phoenix terms into transparent payoff outcomes, "
            "scenario analysis, worst-of basket behavior, Monte Carlo proxies, and client/desk-ready explanations."
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

    st.subheader("Custom Single-Underlying Performance Path")

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

    st.dataframe(result_table, width="stretch")

    st.subheader("Single-Underlying Standard Scenario Table")

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
        width="stretch",
    )

    fig = px.bar(
        scenario_df,
        x="scenario",
        y="total_pnl",
        color="protection_barrier_breached",
        title="Single-Underlying Total P&L by Scenario",
        labels={"scenario": "Scenario", "total_pnl": "Total P&L"},
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Worst-of Basket Scenario Table")

    basket_scenario_paths = build_standard_basket_scenario_paths(int(number_of_observations))
    basket_df = calculate_basket_scenario_table(terms, basket_scenario_paths)

    st.dataframe(
        basket_df.style.format(
            {
                "worst_performance_at_maturity": "{:.2%}",
                "total_coupons_paid": "{:,.0f}",
                "redemption_amount": "{:,.0f}",
                "capital_pnl": "{:,.0f}",
                "total_payoff": "{:,.0f}",
                "total_pnl": "{:,.0f}",
                "payoff_return": "{:.2%}",
            }
        ),
        width="stretch",
    )

    fig_basket = px.bar(
        basket_df,
        x="scenario",
        y="total_pnl",
        color="worst_performer_at_maturity",
        title="Worst-of Basket Total P&L by Scenario",
        labels={"scenario": "Scenario", "total_pnl": "Total P&L"},
    )
    st.plotly_chart(fig_basket, width="stretch")

    st.subheader("Worst-of Basket Commentary")

    selected_basket_scenario = st.selectbox(
        "Select basket scenario for commentary",
        list(basket_scenario_paths.keys()),
    )

    basket_commentary = generate_worst_of_basket_commentary(
        terms=terms,
        underlying_paths=basket_scenario_paths[selected_basket_scenario],
    )

    with st.container(border=True):
        for comment in basket_commentary:
            st.markdown(f"- {comment}")

    st.subheader("Monte Carlo Proxy")

    st.caption(
        "Simplified GBM simulation. This is a risk/payoff proxy, not calibrated issuer pricing."
    )

    mc1, mc2, mc3 = st.columns(3)

    with mc1:
        simulation_mode = st.selectbox(
            "Simulation mode",
            ["Single underlying", "Worst-of basket"],
        )
        n_simulations = st.number_input(
            "Number of simulations",
            min_value=500,
            max_value=20_000,
            value=5_000,
            step=500,
        )

    with mc2:
        volatility_pct = st.number_input(
            "Volatility (%)",
            min_value=0.0,
            max_value=100.0,
            value=25.0,
            step=1.0,
        )
        drift_pct = st.number_input(
            "Drift / proxy rate (%)",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
        )

    with mc3:
        maturity_years = st.number_input(
            "Maturity in years",
            min_value=0.25,
            max_value=10.0,
            value=1.0,
            step=0.25,
        )
        correlation = st.number_input(
            "Basket correlation",
            min_value=-0.40,
            max_value=0.99,
            value=0.50,
            step=0.05,
            disabled=simulation_mode == "Single underlying",
        )
        seed = st.number_input(
            "Random seed",
            min_value=1,
            max_value=999_999,
            value=42,
            step=1,
        )

    if simulation_mode == "Single underlying":
        simulated_paths = simulate_single_underlying_paths(
            number_of_observations=int(number_of_observations),
            n_simulations=int(n_simulations),
            drift=drift_pct / 100.0,
            volatility=volatility_pct / 100.0,
            maturity_years=float(maturity_years),
            seed=int(seed),
        )
        is_worst_of = False
    else:
        basket_simulation = simulate_worst_of_basket_paths(
            number_of_observations=int(number_of_observations),
            n_underlyings=3,
            n_simulations=int(n_simulations),
            drift=drift_pct / 100.0,
            volatility=volatility_pct / 100.0,
            correlation=float(correlation),
            maturity_years=float(maturity_years),
            seed=int(seed),
        )
        simulated_paths = basket_simulation["worst_of_performance_paths"]
        is_worst_of = True

    mc_results_df = calculate_monte_carlo_results_table(
        terms=terms,
        performance_paths=simulated_paths,
    )

    mc_summary = summarize_monte_carlo_results(mc_results_df)
    mc_commentary = generate_monte_carlo_commentary(mc_summary, is_worst_of=is_worst_of)

    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Autocall Prob.", _format_percent(mc_summary["autocall_probability"]))
    m2.metric("Barrier Breach Prob.", _format_percent(mc_summary["barrier_breach_probability"]))
    m3.metric("Expected Payoff", _format_currency(mc_summary["expected_payoff"]))
    m4.metric("Expected P&L", _format_currency(mc_summary["expected_pnl"]))
    m5.metric("Expected Return", _format_percent(mc_summary["expected_return"]))

    with st.container(border=True):
        for comment in mc_commentary:
            st.markdown(f"- {comment}")

    summary_table = pd.DataFrame(
        [{"Metric": key, "Value": value} for key, value in mc_summary.items()]
    )

    st.dataframe(summary_table, width="stretch")

    fig_mc = px.histogram(
        mc_results_df,
        x="total_pnl",
        nbins=50,
        title="Monte Carlo Total P&L Distribution",
        labels={"total_pnl": "Total P&L"},
    )
    st.plotly_chart(fig_mc, width="stretch")


    st.subheader("Structured Products Excel Report")

    structured_report_bytes = generate_structured_products_report(
        terms_summary={
            "product_type": terms.product_type,
            "nominal": terms.nominal,
            "coupon_rate_per_period": terms.coupon_rate_per_period,
            "autocall_barrier": terms.autocall_barrier,
            "coupon_barrier": terms.coupon_barrier,
            "protection_barrier": terms.protection_barrier,
            "memory_coupon": terms.memory_coupon,
            "performance_path": performance_path,
            "simulation_mode": simulation_mode,
            "number_of_simulations": int(n_simulations),
            "volatility": volatility_pct / 100.0,
            "drift": drift_pct / 100.0,
            "maturity_years": float(maturity_years),
            "correlation": float(correlation) if simulation_mode == "Worst-of basket" else None,
            "seed": int(seed),
        },
        custom_path_result=result_dict,
        single_scenario_df=scenario_df,
        basket_scenario_df=basket_df,
        monte_carlo_summary=mc_summary,
        monte_carlo_results_df=mc_results_df,
    )

    st.download_button(
        label="Download Structured Products Report",
        data=structured_report_bytes,
        file_name="structured_products_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Methodology Notes")

    st.markdown(
        """
        - Performance values are measured versus initial level.
        - Autocall barrier at 100% of initial means performance must be at least 0%.
        - Protection barrier at 60% of initial means final performance below -40% creates capital loss.
        - Athena coupon is simplified as accumulated coupon paid only if autocall occurs.
        - Phoenix coupon can be paid periodically if the coupon barrier is met.
        - Phoenix memory coupon allows missed coupons to be recovered later if the coupon condition is met.
        - Worst-of basket payoff is driven by the weakest underlying at each observation.
        - Worst-of structures are exposed to dispersion risk: one weak name can dominate the payoff.
        - Monte Carlo uses simplified GBM paths and should be treated as a proxy layer only.
        - This module is not bank-grade pricing, not fair value, and not investment advice.
        """
    )
