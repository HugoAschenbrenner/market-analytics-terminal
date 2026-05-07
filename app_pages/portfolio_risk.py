import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from engines.portfolio_risk_engine import (
    build_sample_price_data,
    calculate_asset_returns,
    calculate_correlation_matrix,
    calculate_cumulative_return_series,
    calculate_drawdown_series,
    calculate_portfolio_returns,
    calculate_risk_contribution,
    calculate_stress_scenario_table,
    generate_portfolio_risk_commentary,
    portfolio_risk_summary_to_dict,
    summarize_portfolio_risk,
)


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def _format_number(value: float) -> str:
    return f"{value:,.2f}"


def render() -> None:
    render_module_header(
        title="Portfolio Risk",
        caption="Portfolio analytics: returns, volatility, Sharpe, drawdown, VaR, CVaR, correlations, and stress tests.",
        objective=(
            "Objective: convert asset price data and weights into practical portfolio risk diagnostics, "
            "risk concentration, and stress scenario outputs."
        ),
    )

    st.subheader("Input Data")

    uploaded_file = st.file_uploader(
        "Upload price CSV with a date column and asset price columns",
        type=["csv"],
        help="If no file is uploaded, the app uses a synthetic multi-asset price dataset.",
    )

    if uploaded_file is not None:
        price_df = pd.read_csv(uploaded_file)
        st.info("Using uploaded price dataset.")
    else:
        price_df = build_sample_price_data()
        st.info("Using default synthetic multi-asset dataset.")

    with st.expander("Raw price data", expanded=False):
        st.dataframe(price_df.tail(20), use_container_width=True)

    returns_df = calculate_asset_returns(price_df)
    assets = list(returns_df.columns)

    st.subheader("Portfolio Weights")

    st.caption("Weights are normalized automatically if they do not sum exactly to 100%.")

    default_weight = 100.0 / len(assets)
    weight_inputs = {}

    weight_columns = st.columns(min(len(assets), 5))

    for idx, asset in enumerate(assets):
        with weight_columns[idx % len(weight_columns)]:
            weight_pct = st.number_input(
                f"{asset} weight (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(default_weight),
                step=1.0,
            )
            weight_inputs[asset] = weight_pct / 100.0

    weight_sum = sum(weight_inputs.values())

    if weight_sum <= 0:
        st.error("Total portfolio weight must be positive.")
        return

    weights = {asset: weight / weight_sum for asset, weight in weight_inputs.items()}

    risk_free_rate_pct = st.number_input(
        "Risk-free rate for Sharpe (%)",
        min_value=-5.0,
        max_value=20.0,
        value=2.0,
        step=0.25,
    )

    portfolio_returns = calculate_portfolio_returns(returns_df, weights)
    cumulative_returns = calculate_cumulative_return_series(portfolio_returns)
    drawdown_series = calculate_drawdown_series(portfolio_returns)

    summary = summarize_portfolio_risk(
        returns_df=returns_df,
        weights=weights,
        risk_free_rate=risk_free_rate_pct / 100.0,
    )

    summary_dict = portfolio_risk_summary_to_dict(summary)
    risk_contribution_df = calculate_risk_contribution(returns_df, weights)
    stress_df = calculate_stress_scenario_table(weights)
    correlation_matrix = calculate_correlation_matrix(returns_df)
    commentary = generate_portfolio_risk_commentary(
        summary=summary,
        risk_contribution_df=risk_contribution_df,
        stress_df=stress_df,
    )

    st.subheader("Portfolio Risk Summary")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Ann. Return", _format_percent(summary.annualized_return))
    c2.metric("Ann. Volatility", _format_percent(summary.annualized_volatility))
    c3.metric("Sharpe", _format_number(summary.sharpe_ratio))
    c4.metric("Max Drawdown", _format_percent(summary.max_drawdown))
    c5.metric("Hist. VaR 95%", _format_percent(summary.historical_var_95))

    c6, c7, c8, c9, c10 = st.columns(5)

    c6.metric("Hist. CVaR 95%", _format_percent(summary.historical_cvar_95))
    c7.metric("Best Period", _format_percent(summary.best_period_return))
    c8.metric("Worst Period", _format_percent(summary.worst_period_return))
    c9.metric("Assets", str(summary.number_of_assets))
    c10.metric("Observations", str(summary.number_of_observations))

    st.subheader("Desk Commentary")

    with st.container(border=True):
        for comment in commentary:
            st.markdown(f"- {comment}")

    st.subheader("Performance and Drawdown")

    cumulative_df = cumulative_returns.reset_index()
    cumulative_df.columns = ["date", "cumulative_return_index"]

    fig_cumulative = px.line(
        cumulative_df,
        x="date",
        y="cumulative_return_index",
        title="Portfolio Cumulative Return Index",
        labels={"cumulative_return_index": "Cumulative Return Index"},
    )
    st.plotly_chart(fig_cumulative, use_container_width=True)

    drawdown_df = drawdown_series.reset_index()
    drawdown_df.columns = ["date", "drawdown"]

    fig_drawdown = px.area(
        drawdown_df,
        x="date",
        y="drawdown",
        title="Portfolio Drawdown",
        labels={"drawdown": "Drawdown"},
    )
    st.plotly_chart(fig_drawdown, use_container_width=True)

    st.subheader("Risk Contribution")

    st.dataframe(
        risk_contribution_df.style.format(
            {
                "weight": "{:.2%}",
                "marginal_contribution_to_risk": "{:.2%}",
                "contribution_to_volatility": "{:.2%}",
                "pct_contribution_to_volatility": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

    fig_contribution = px.bar(
        risk_contribution_df,
        x="asset",
        y="pct_contribution_to_volatility",
        title="Contribution to Portfolio Volatility",
        labels={
            "asset": "Asset",
            "pct_contribution_to_volatility": "% Contribution to Volatility",
        },
    )
    st.plotly_chart(fig_contribution, use_container_width=True)

    st.subheader("Correlation Matrix")

    corr_long = correlation_matrix.reset_index().melt(
        id_vars="index",
        var_name="asset_2",
        value_name="correlation",
    )
    corr_long = corr_long.rename(columns={"index": "asset_1"})

    fig_corr = px.imshow(
        correlation_matrix,
        text_auto=".2f",
        title="Asset Return Correlation Matrix",
        aspect="auto",
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    with st.expander("Correlation table", expanded=False):
        st.dataframe(
            correlation_matrix.style.format("{:.2f}"),
            use_container_width=True,
        )

    st.subheader("Stress Scenarios")

    st.dataframe(
        stress_df.style.format(
            {
                "estimated_portfolio_return": "{:.2%}",
                "estimated_loss": "{:.2%}",
                "estimated_gain": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

    fig_stress = px.bar(
        stress_df,
        x="scenario",
        y="estimated_portfolio_return",
        title="Estimated Portfolio Return by Stress Scenario",
        labels={
            "scenario": "Scenario",
            "estimated_portfolio_return": "Estimated Portfolio Return",
        },
    )
    st.plotly_chart(fig_stress, use_container_width=True)

    st.subheader("Methodology Notes")

    st.markdown(
        """
        - Portfolio return is calculated as the weighted sum of asset returns.
        - Weights are normalized if they do not sum exactly to 100%.
        - Annualized return uses arithmetic average return multiplied by 252.
        - Annualized volatility uses standard deviation multiplied by sqrt(252).
        - Sharpe ratio uses the user-defined risk-free rate.
        - Historical VaR and CVaR are reported as positive loss numbers.
        - Risk contribution uses covariance-based contribution to portfolio volatility.
        - Stress scenarios are predefined simplified shocks based on generic asset labels.
        - This module does not model liquidity, transaction costs, factor exposure, or live risk.
        """
    )
