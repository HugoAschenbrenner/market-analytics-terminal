from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from reports.excel_exporter import generate_portfolio_risk_report
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



    st.subheader("Portfolio Risk Excel Report")

    weights_df = pd.DataFrame(
        [{"asset": asset, "weight": weight} for asset, weight in weights.items()]
    )

    portfolio_returns_df = portfolio_returns.reset_index()
    portfolio_returns_df.columns = ["date", "portfolio_return"]

    drawdown_df = drawdown_series.reset_index()
    drawdown_df.columns = ["date", "drawdown"]

    portfolio_report_bytes = generate_portfolio_risk_report(
        summary=summary_dict,
        weights_df=weights_df,
        risk_contribution_df=risk_contribution_df,
        correlation_matrix=correlation_matrix,
        stress_df=stress_df,
        portfolio_returns_df=portfolio_returns_df,
        drawdown_df=drawdown_df,
    )

    st.download_button(
        label="Download Portfolio Risk Report",
        data=portfolio_report_bytes,
        file_name="portfolio_risk_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


    st.subheader("R Portfolio Analytics Companion")

    r_output_dir = Path("r_analytics/outputs")

    required_r_outputs = {
        "performance_summary": r_output_dir / "performance_summary.csv",
        "rolling_risk_metrics": r_output_dir / "rolling_risk_metrics.csv",
        "drawdown_series": r_output_dir / "drawdown_series.csv",
        "monthly_returns": r_output_dir / "monthly_returns.csv",
        "correlation_matrix": r_output_dir / "correlation_matrix.csv",
        "cumulative_performance_chart": r_output_dir / "cumulative_performance.png",
        "drawdown_chart": r_output_dir / "drawdown_chart.png",
        "rolling_volatility_chart": r_output_dir / "rolling_volatility.png",
    }

    missing_r_outputs = [
        str(path) for path in required_r_outputs.values() if not path.exists()
    ]

    if missing_r_outputs:
        st.warning(
            "R analytics outputs are missing. Run: "
            "`Rscript r_analytics/portfolio_performance_report.R`"
        )
        with st.expander("Missing R output files", expanded=False):
            for missing_file in missing_r_outputs:
                st.code(missing_file)
    else:
        st.caption(
            "These outputs were generated by the R companion script and loaded into the Python Streamlit terminal."
        )

        r_summary_df = pd.read_csv(required_r_outputs["performance_summary"])
        rolling_risk_df = pd.read_csv(required_r_outputs["rolling_risk_metrics"])
        monthly_returns_df = pd.read_csv(required_r_outputs["monthly_returns"])
        r_correlation_df = pd.read_csv(required_r_outputs["correlation_matrix"], index_col=0)

        st.markdown("#### R Performance Summary")

        r_summary_display = r_summary_df.copy()
        r_summary_display["value"] = r_summary_display["value"].astype(str)

        st.dataframe(r_summary_display, use_container_width=True)

        st.markdown("#### R-Generated Charts")

        chart_col_1, chart_col_2, chart_col_3 = st.columns(3)

        with chart_col_1:
            st.image(
                str(required_r_outputs["cumulative_performance_chart"]),
                caption="R cumulative performance",
            )

        with chart_col_2:
            st.image(
                str(required_r_outputs["drawdown_chart"]),
                caption="R drawdown chart",
            )

        with chart_col_3:
            st.image(
                str(required_r_outputs["rolling_volatility_chart"]),
                caption="R rolling volatility",
            )

        st.markdown("#### Rolling Risk Metrics from R")

        st.dataframe(
            rolling_risk_df.tail(20),
            use_container_width=True,
        )

        rolling_risk_clean = rolling_risk_df.dropna(subset=["rolling_volatility"])

        if not rolling_risk_clean.empty:
            fig_r_rolling_vol = px.line(
                rolling_risk_clean,
                x="date",
                y="rolling_volatility",
                title="R Companion - Rolling Volatility",
                labels={"rolling_volatility": "Rolling Volatility"},
            )
            st.plotly_chart(fig_r_rolling_vol, use_container_width=True)

        st.markdown("#### Monthly Returns from R")

        st.dataframe(
            monthly_returns_df.tail(24),
            use_container_width=True,
        )

        fig_r_monthly = px.bar(
            monthly_returns_df.tail(24),
            x="month",
            y="portfolio_monthly_return",
            title="R Companion - Monthly Portfolio Returns",
            labels={"portfolio_monthly_return": "Monthly Return"},
        )
        st.plotly_chart(fig_r_monthly, use_container_width=True)

        st.markdown("#### R Correlation Matrix")

        fig_r_corr = px.imshow(
            r_correlation_df,
            text_auto=".2f",
            title="R Companion - Correlation Matrix",
            aspect="auto",
        )
        st.plotly_chart(fig_r_corr, use_container_width=True)

        with st.expander("R correlation table", expanded=False):
            st.dataframe(
                r_correlation_df.style.format("{:.2f}"),
                use_container_width=True,
            )


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
