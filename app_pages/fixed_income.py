import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from reports.excel_exporter import generate_fixed_income_risk_report
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

from engines.market_data_engine import normalize_symbols
from engines.rates_market_data_engine import (
    BOND_ETF_PROXY_WATCHLIST,
    bond_proxy_quotes_to_dataframe,
    build_rates_and_bond_market_snapshot,
    curve_payload_to_dataframe,
    spreads_payload_to_dataframe,
)


def _format_currency(value: float) -> str:
    return f"{value:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def _format_optional_number(value: float | None, decimals: int = 2, suffix: str = "") -> str:
    """Format optional numbers safely for public market data tables."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):,.{decimals}f}{suffix}"


def _parse_bond_proxy_watchlist_text(watchlist_text: str) -> list[str]:
    """Parse comma-separated bond ETF proxy tickers into normalized symbols."""
    return normalize_symbols(watchlist_text.split(","))


def _render_rates_bond_market_snapshot() -> None:
    """Render optional official rates and bond ETF proxy snapshot."""
    st.subheader("Free Rates & Bond Market Snapshot")

    with st.container(border=True):
        st.caption(
            "Optional public-market rates layer. Treasury curve data is official daily public data. "
            "ETF proxies are used for market context only and are not individual bond prices."
        )

        default_symbols = ", ".join(BOND_ETF_PROXY_WATCHLIST)

        watchlist_text = st.text_input(
            "Bond ETF proxies",
            value=default_symbols,
            help="ETF proxy examples: SHY short Treasury, IEF intermediate Treasury, TLT long Treasury, LQD investment grade credit, HYG high yield credit.",
        )

        refresh = st.button(
            "Refresh rates and bond proxies",
            key="refresh_rates_bond_market_snapshot",
        )

        if refresh:
            symbols = _parse_bond_proxy_watchlist_text(watchlist_text)

            if not symbols:
                st.warning("Enter at least one valid bond ETF proxy ticker.")
                return

            with st.spinner("Fetching public rates and bond proxy data..."):
                st.session_state["rates_bond_market_snapshot_payload"] = (
                    build_rates_and_bond_market_snapshot(bond_etf_symbols=symbols)
                )

        payload = st.session_state.get("rates_bond_market_snapshot_payload")

        if payload is None:
            st.info("Click Refresh rates and bond proxies to load the optional rates snapshot.")
            return

        treasury_payload = payload.get("treasury_curve", {})
        curve = treasury_payload.get("curve", {})
        spreads = treasury_payload.get("spreads_bps", {})

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Curve Regime", str(treasury_payload.get("curve_regime", "N/A")).title())
        c2.metric(
            "2s10s",
            _format_optional_number(spreads.get("2s10s_bps"), decimals=1, suffix=" bps"),
        )
        c3.metric(
            "5s30s",
            _format_optional_number(spreads.get("5s30s_bps"), decimals=1, suffix=" bps"),
        )
        c4.metric(
            "10Y Treasury",
            _format_optional_number(curve.get("10Y"), decimals=2, suffix="%"),
        )

        st.markdown("**Treasury Curve**")

        curve_df = curve_payload_to_dataframe(treasury_payload)

        if curve_df.empty:
            st.warning("No Treasury curve data returned.")
        else:
            st.dataframe(
                curve_df.style.format(
                    {"yield_pct": lambda value: _format_optional_number(value, decimals=2, suffix="%")}
                ),
                use_container_width=True,
            )

        st.markdown("**Curve Spreads**")

        spreads_df = spreads_payload_to_dataframe(treasury_payload)

        if spreads_df.empty:
            st.warning("No curve spread data returned.")
        else:
            st.dataframe(
                spreads_df.style.format(
                    {"value_bps": lambda value: _format_optional_number(value, decimals=1, suffix=" bps")}
                ),
                use_container_width=True,
            )

        st.markdown("**Desk Read**")

        for line in treasury_payload.get("desk_read", []):
            st.markdown(f"- {line}")

        bond_proxy_payload = payload.get("bond_etf_proxies", {})

        if bond_proxy_payload:
            st.markdown("**Bond ETF Proxy Snapshot**")
            bond_proxy_df = bond_proxy_quotes_to_dataframe(bond_proxy_payload)

            if bond_proxy_df.empty:
                st.warning("No ETF proxy data returned.")
            else:
                st.dataframe(
                    bond_proxy_df.style.format(
                        {
                            "price": lambda value: _format_optional_number(value, decimals=4),
                            "change_pct": lambda value: _format_optional_number(value, decimals=2, suffix="%"),
                        }
                    ),
                    use_container_width=True,
                )

        st.caption(
            f"Rates source: {treasury_payload.get('source')} | "
            f"Rates mode: {treasury_payload.get('data_mode')} | "
            f"As of: {treasury_payload.get('as_of_date')} | "
            f"Updated: {treasury_payload.get('timestamp_utc')}"
        )
        st.caption(payload.get("disclaimer", ""))


def render() -> None:
    render_module_header(
        title="Fixed Income Risk",
        caption="Bond portfolio risk analytics: duration, convexity, DV01, curve shocks, and risk reports.",
        objective=(
            "Objective: help a sales, trader, PM, or risk analyst understand where bond portfolio risk "
            "is concentrated and how the portfolio reacts to yield curve and spread shocks."
        ),
    )

    _render_rates_bond_market_snapshot()

    st.divider()

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


    st.subheader("Excel Risk Report")

    report_bytes = generate_fixed_income_risk_report(
        summary=summary_dict,
        risk_df=risk_df,
        bucket_df=bucket_df,
        scenario_df=scenario_df,
        commentary=commentary,
    )

    st.download_button(
        label="Download Fixed Income Risk Report",
        data=report_bytes,
        file_name="fixed_income_risk_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

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
