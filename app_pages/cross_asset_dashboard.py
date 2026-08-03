from dataclasses import asdict

import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from engines.cross_asset_dashboard_engine import (
    CrossAssetRiskInputs,
    build_default_cross_asset_inputs,
    build_risk_heatmap_table,
    build_sleeve_reconciliation_table,
    calculate_cross_asset_stress_table,
    calculate_cross_asset_summary,
    cross_asset_inputs_to_dict,
    cross_asset_summary_to_dict,
    generate_cross_asset_commentary,
)
from engines.market_data_engine import (
    build_market_snapshot,
    default_watchlist,
    normalize_symbols,
)


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def _format_score(value: float) -> str:
    return f"{value:.1f}/100"


def _format_amount(value: float, currency: str | None = None) -> str:
    formatted = f"{value:,.0f}"
    return f"{formatted} {currency}" if currency else formatted


def _parse_watchlist_text(watchlist_text: str) -> list[str]:
    """Parse comma-separated Streamlit watchlist input into normalized tickers."""

    return normalize_symbols(watchlist_text.split(","))


def _market_snapshot_to_dataframe(payload: dict) -> pd.DataFrame:
    """Convert market data payload into a Streamlit-friendly table."""

    rows = []
    for symbol, quote in payload.get("quotes", {}).items():
        rows.append(
            {
                "symbol": quote.get("symbol", symbol),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct"),
                "currency": quote.get("currency") or "",
                "status": quote.get("status"),
                "source": quote.get("source", payload.get("source")),
                "data_mode": quote.get(
                    "data_mode",
                    payload.get("data_mode"),
                ),
                "timestamp_utc": quote.get(
                    "timestamp_utc",
                    payload.get("timestamp_utc"),
                ),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "symbol",
            "price",
            "change_pct",
            "currency",
            "status",
            "source",
            "data_mode",
            "timestamp_utc",
        ],
    )


def _format_optional_number(
    value: float | None,
    decimals: int = 2,
    suffix: str = "",
) -> str:
    """Format optional numeric values without breaking on missing data."""

    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}{suffix}"


def _render_market_data_snapshot() -> None:
    """Render optional public market data without automatic network calls."""

    st.subheader("Free Market Data Snapshot")

    with st.container(border=True):
        st.caption(
            "Optional public-market data adapter. Quotes may be near-live or "
            "delayed depending on provider availability and are used only as "
            "separate demo context; they do not feed the stress aggregation."
        )

        watchlist_text = st.text_input(
            "Watchlist",
            value=", ".join(default_watchlist()),
            help=(
                "Use Yahoo/yfinance ticker format, for example: "
                "SPY, QQQ, TLT, GLD, AAPL."
            ),
        )

        refresh = st.button(
            "Refresh market data",
            key="refresh_market_data_snapshot",
        )

        if refresh:
            symbols = _parse_watchlist_text(watchlist_text)
            if not symbols:
                st.warning("Enter at least one valid ticker.")
                return

            with st.spinner("Fetching public market data..."):
                st.session_state[
                    "market_data_snapshot_payload"
                ] = build_market_snapshot(symbols)

        payload = st.session_state.get(
            "market_data_snapshot_payload"
        )

        if payload is None:
            st.info(
                "Click Refresh market data to load the optional public quote snapshot."
            )
            return

        snapshot_df = _market_snapshot_to_dataframe(payload)
        if snapshot_df.empty:
            st.warning("No market data returned for the selected watchlist.")
            return

        st.dataframe(
            snapshot_df.style.format(
                {
                    "price": lambda value: _format_optional_number(
                        value,
                        decimals=4,
                    ),
                    "change_pct": lambda value: _format_optional_number(
                        value,
                        decimals=2,
                        suffix="%",
                    ),
                }
            ),
            use_container_width=True,
        )
        st.caption(
            f"Source: {payload.get('source')} | "
            f"Mode: {payload.get('data_mode')} | "
            f"Updated: {payload.get('timestamp_utc')}"
        )
        st.caption(payload.get("disclaimer", ""))


def render() -> None:
    render_module_header(
        title="Cross-Asset Dashboard",
        caption=(
            "Manual cross-asset stress synthesis with a common NAV, explicit "
            "base currency, and separate financing-liquidity reporting."
        ),
        objective=(
            "Objective: convert non-overlapping sleeve shocks into economic "
            "P&L amounts, reconcile them to one NAV, and keep collateral or "
            "margin requirements outside economic P&L."
        ),
    )

    _render_market_data_snapshot()
    st.divider()

    default_inputs = build_default_cross_asset_inputs()

    st.warning(
        "Manual/sample input mode. These values are not automatically linked "
        "to current module runs. The stress table is valid only when all "
        "amounts refer to the same as-of, base currency and non-overlapping sleeves."
    )

    st.subheader("Common NAV & Sleeve Contract")

    n1, n2, n3, n4, n5 = st.columns(5)
    with n1:
        base_currency = st.selectbox(
            "Base currency",
            ["EUR", "USD", "GBP", "CHF"],
            index=["EUR", "USD", "GBP", "CHF"].index(
                default_inputs.base_currency
            ),
        )
    with n2:
        portfolio_nav = st.number_input(
            f"Common portfolio NAV ({base_currency})",
            min_value=1.0,
            value=float(default_inputs.portfolio_nav),
            step=5_000_000.0,
        )
    with n3:
        rates_sleeve_notional = st.number_input(
            f"Dedicated rates sleeve ({base_currency})",
            min_value=0.0,
            value=float(default_inputs.rates_sleeve_notional),
            step=1_000_000.0,
        )
    with n4:
        structured_products_notional = st.number_input(
            f"Structured-products sleeve ({base_currency})",
            min_value=0.0,
            value=float(default_inputs.structured_products_notional),
            step=1_000_000.0,
        )
    with n5:
        residual_portfolio_notional = st.number_input(
            f"Residual multi-asset sleeve ({base_currency})",
            min_value=0.0,
            value=float(default_inputs.residual_portfolio_notional),
            step=1_000_000.0,
            help=(
                "This sleeve must exclude the dedicated rates and structured-products sleeves."
            ),
        )

    allocated_notional = (
        rates_sleeve_notional
        + structured_products_notional
        + residual_portfolio_notional
    )

    if allocated_notional > portfolio_nav:
        st.error(
            "Non-overlapping sleeve notionals exceed common portfolio NAV. "
            "Reduce the sleeves or increase NAV before running the aggregation."
        )
        return

    st.caption(
        f"Allocated sleeves: {_format_amount(allocated_notional, base_currency)} | "
        f"Unallocated NAV: {_format_amount(portfolio_nav - allocated_notional, base_currency)}"
    )

    st.subheader("Manual Risk Inputs")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        total_dv01 = st.number_input(
            f"Rates DV01 ({base_currency}/bp)",
            value=float(default_inputs.total_dv01),
            step=1_000.0,
            help=(
                "Signed dedicated-rates-sleeve DV01 already translated into the base currency."
            ),
        )
        long_end_dv01_share = st.slider(
            "Long-end DV01 share",
            0.0,
            1.0,
            float(default_inputs.long_end_dv01_share),
            0.01,
        )

    with c2:
        repo_margin_deficit = st.number_input(
            f"Current financing liquidity requirement ({base_currency})",
            min_value=0.0,
            value=float(default_inputs.repo_margin_deficit),
            step=25_000.0,
            help=(
                "Collateral or margin requirement. It is reported separately and is not economic P&L."
            ),
        )
        collateral_market_value = st.number_input(
            f"Financing collateral market value ({base_currency})",
            min_value=1.0,
            value=float(default_inputs.collateral_market_value),
            step=500_000.0,
        )

    with c3:
        structured_autocall_probability = st.slider(
            "Autocall probability",
            0.0,
            1.0,
            float(default_inputs.structured_autocall_probability),
            0.01,
        )
        structured_barrier_breach_probability = st.slider(
            "Final protection loss probability",
            0.0,
            1.0,
            float(default_inputs.structured_barrier_breach_probability),
            0.01,
        )

    with c4:
        portfolio_var_95 = st.slider(
            "Residual sleeve VaR 95%",
            0.0,
            0.10,
            float(default_inputs.portfolio_var_95),
            0.001,
        )
        portfolio_cvar_95 = st.slider(
            "Residual sleeve CVaR 95%",
            0.0,
            0.15,
            float(default_inputs.portfolio_cvar_95),
            0.001,
        )
        max_drawdown = st.slider(
            "Residual sleeve max drawdown",
            -0.80,
            0.0,
            float(default_inputs.max_drawdown),
            0.01,
        )

    st.subheader("Residual Multi-Asset Exposure Mix")
    e1, e2, e3, e4 = st.columns(4)

    with e1:
        equity_weight = st.slider(
            "Equity weight",
            0.0,
            1.0,
            float(default_inputs.equity_weight),
            0.01,
        )
    with e2:
        credit_weight = st.slider(
            "Credit weight",
            0.0,
            1.0,
            float(default_inputs.credit_weight),
            0.01,
        )
    with e3:
        rates_weight = st.slider(
            "Rates weight",
            0.0,
            1.0,
            float(default_inputs.rates_weight),
            0.01,
        )
    with e4:
        alternatives_weight = st.slider(
            "Alternatives weight",
            0.0,
            1.0,
            float(default_inputs.alternatives_weight),
            0.01,
        )

    exposure_sum = (
        equity_weight
        + credit_weight
        + rates_weight
        + alternatives_weight
    )

    if exposure_sum <= 0:
        st.error("Residual-sleeve exposure weights must sum to a positive number.")
        return

    inputs = CrossAssetRiskInputs(
        total_dv01=float(total_dv01),
        long_end_dv01_share=float(long_end_dv01_share),
        repo_margin_deficit=float(repo_margin_deficit),
        collateral_market_value=float(collateral_market_value),
        structured_autocall_probability=float(
            structured_autocall_probability
        ),
        structured_barrier_breach_probability=float(
            structured_barrier_breach_probability
        ),
        portfolio_var_95=float(portfolio_var_95),
        portfolio_cvar_95=float(portfolio_cvar_95),
        max_drawdown=float(max_drawdown),
        equity_weight=float(equity_weight / exposure_sum),
        credit_weight=float(credit_weight / exposure_sum),
        rates_weight=float(rates_weight / exposure_sum),
        alternatives_weight=float(alternatives_weight / exposure_sum),
        base_currency=str(base_currency),
        portfolio_nav=float(portfolio_nav),
        rates_sleeve_notional=float(rates_sleeve_notional),
        structured_products_notional=float(
            structured_products_notional
        ),
        residual_portfolio_notional=float(
            residual_portfolio_notional
        ),
    )

    summary = calculate_cross_asset_summary(inputs)
    stress_df = calculate_cross_asset_stress_table(inputs)
    heatmap_df = build_risk_heatmap_table(summary)
    sleeve_df = build_sleeve_reconciliation_table(inputs)
    commentary = generate_cross_asset_commentary(
        inputs,
        summary,
        stress_df,
    )

    st.subheader("Sleeve NAV Reconciliation")
    st.dataframe(
        sleeve_df.style.format(
            {
                "notional_base": "{:,.0f}",
                "share_of_nav": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

    worst_row = stress_df.loc[
        stress_df["economic_pnl_pct_nav"].idxmin()
    ]
    peak_liquidity_row = stress_df.loc[
        stress_df[
            "stressed_financing_liquidity_requirement_amount"
        ].idxmax()
    ]

    st.subheader("Cross-Asset Stress Summary")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Worst Economic Stress", worst_row["scenario"])
    k2.metric(
        f"Economic P&L ({base_currency})",
        _format_amount(worst_row["economic_pnl_amount"]),
    )
    k3.metric(
        "Economic P&L / Common NAV",
        _format_percent(worst_row["economic_pnl_pct_nav"]),
    )
    k4.metric(
        "Peak Financing Liquidity",
        _format_amount(
            peak_liquidity_row[
                "stressed_financing_liquidity_requirement_amount"
            ],
            base_currency,
        ),
    )
    k5.metric(
        "Heuristic Demo Score",
        _format_score(summary.composite_score),
    )

    st.info(
        "The score and bucket labels below are uncalibrated demo heuristics. "
        "They are not VaR, stress loss, limit utilization, or a validated composite risk measure."
    )

    st.subheader("Desk Commentary")
    with st.container(border=True):
        for comment in commentary:
            st.markdown(f"- {comment}")

    st.subheader("Cross-Asset Economic P&L Scenarios")
    st.dataframe(
        stress_df.style.format(
            {
                "rates_pnl_amount": "{:,.0f}",
                "structured_products_shock_pct": "{:.2%}",
                "structured_products_pnl_amount": "{:,.0f}",
                "residual_portfolio_shock_pct": "{:.2%}",
                "residual_portfolio_pnl_amount": "{:,.0f}",
                "economic_pnl_amount": "{:,.0f}",
                "economic_pnl_pct_nav": "{:.2%}",
                "incremental_financing_liquidity_change_amount": "{:,.0f}",
                "stressed_financing_liquidity_requirement_amount": "{:,.0f}",
            }
        ),
        use_container_width=True,
    )

    fig_stress = px.bar(
        stress_df,
        x="scenario",
        y="economic_pnl_pct_nav",
        title="Economic P&L as a Percentage of Common NAV",
        labels={
            "scenario": "Scenario",
            "economic_pnl_pct_nav": "Economic P&L / NAV",
        },
    )
    st.plotly_chart(fig_stress, use_container_width=True)

    fig_liquidity = px.bar(
        stress_df,
        x="scenario",
        y="stressed_financing_liquidity_requirement_amount",
        title=f"Separate Financing Liquidity Requirement ({base_currency})",
        labels={
            "scenario": "Scenario",
            "stressed_financing_liquidity_requirement_amount": (
                f"Liquidity Requirement ({base_currency})"
            ),
        },
    )
    st.plotly_chart(fig_liquidity, use_container_width=True)

    st.subheader("Illustrative Heuristic Risk Scores")
    heatmap_matrix = heatmap_df.set_index("risk_bucket")[["heuristic_score"]]
    fig_heatmap = px.imshow(
        heatmap_matrix,
        text_auto=".1f",
        title="Uncalibrated Heuristic Score Heatmap",
        aspect="auto",
        labels={"color": "Heuristic score"},
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.dataframe(
        heatmap_df.style.format({"heuristic_score": "{:.1f}"}),
        use_container_width=True,
    )

    st.subheader("Input Snapshot")
    input_snapshot_df = pd.DataFrame(
        [
            {"input": key, "value": value}
            for key, value in cross_asset_inputs_to_dict(inputs).items()
        ]
    )
    input_snapshot_df["value"] = input_snapshot_df["value"].astype(str)
    st.dataframe(input_snapshot_df, use_container_width=True)

    st.subheader("Output Summary")
    output_summary_df = pd.DataFrame(
        [
            {"output": key, "value": value}
            for key, value in cross_asset_summary_to_dict(summary).items()
        ]
    )
    output_summary_df["value"] = output_summary_df["value"].astype(str)
    st.dataframe(output_summary_df, use_container_width=True)

    st.subheader("Methodology Notes")
    st.markdown(
        f"""
        - **Common denominator:** economic P&L is divided only by the common portfolio NAV of **{portfolio_nav:,.0f} {base_currency}**.
        - **Amount-first aggregation:** rates, structured-products and residual-portfolio impacts are calculated as **{base_currency} amounts** before aggregation.
        - **No double counting:** dedicated rates, structured-products and residual multi-asset sleeve notionals must not overlap and cannot exceed NAV.
        - **Liquidity is separate:** repo margin and collateral requirements are liquidity transfers/requirements, not economic P&L, and are excluded from `economic_pnl_amount`.
        - **Rates convention:** DV01 is assumed to be signed and already translated into **{base_currency} per bp**.
        - **Scenario labels:** the rates stress is explicitly a parallel +100 bp shock; it is not presented as a 2s10s curve twist.
        - **Heuristic scores:** score formulas are illustrative, uncalibrated and unsuitable for limits, governance or production aggregation.
        - **Data lineage:** inputs are manual/sample values and are not synchronized with the latest runs of the source modules.
        """
    )
