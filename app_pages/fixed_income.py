from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from app_pages.common import render_module_header
from reports.excel_exporter import generate_fixed_income_risk_report
from engines.fixed_income_engine import (
    apply_fx_conversion,
    build_currency_exposure_table,
    build_credit_spread_exposure_table,
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


def _default_demo_fx_to_base(local_currency: str, base_currency: str) -> float:
    """Return transparent demo assumptions, not live FX quotes."""
    if local_currency == base_currency:
        return 1.0
    demo_rates = {
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.087,
    }
    return float(demo_rates.get((local_currency, base_currency), 1.0))


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
        if treasury_payload.get("status") == "sample_fallback":
            st.warning("Public Treasury data is unavailable. The curve and desk read below use a synthetic sample, not current market observations.")
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
        st.caption("ETF prices are unadjusted closes; changes exclude distributions. The observation date/time is the provider bar time; timestamp_utc is retrieval time.")

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
            f"Retrieved: {treasury_payload.get('timestamp_utc')}"
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
        try:
            bonds = pd.read_csv(uploaded_file)
        except (ValueError, UnicodeError) as exc:
            st.error(f"Cannot read bond CSV: {exc}")
            return
        st.info("Using uploaded portfolio.")
    else:
        bonds = load_bond_data("data/sample_bonds.csv")
        st.info("Using default synthetic sample bond dataset.")

    with st.expander("Raw bond data", expanded=False):
        st.dataframe(bonds, use_container_width=True)

    st.subheader("Bond Pricing & Schedule Contract")

    with st.container(border=True):
        p1, p2, p3 = st.columns(3)

        with p1:
            valuation_date = st.date_input(
                "Valuation / settlement date",
                value=date.today(),
                help=(
                    "Coupon schedule, accrued interest and pricing "
                    "are all evaluated from this date."
                ),
            )
            pricing_mode = st.selectbox(
                "Price / YTM reconciliation mode",
                [
                    "Solve YTM from clean price",
                    "Audit supplied YTM against quote",
                ],
                index=0,
                help=(
                    "Default mode solves a yield that exactly reprices "
                    "the quoted clean price plus accrued interest. "
                    "Audit mode preserves the uploaded YTM and displays "
                    "the resulting quote/model gap."
                ),
            )

        with p2:
            default_day_count_convention = st.selectbox(
                "Default day-count convention",
                ["ACT/ACT", "ACT/365F", "30/360"],
                index=0,
                help=(
                    "An optional day_count_convention column in the CSV "
                    "overrides this portfolio-level default."
                ),
            )
            when_issued_policy = st.selectbox(
                "When-issued position policy",
                ["Flag", "Reject"],
                index=0,
                help=(
                    "Flag keeps positions whose issue date is after the "
                    "valuation date and labels them explicitly. Reject "
                    "blocks the portfolio."
                ),
            )

        with p3:
            reconciliation_tolerance = st.number_input(
                "Price reconciliation tolerance (points per 100)",
                min_value=0.0,
                value=0.01,
                step=0.01,
                format="%.4f",
            )

        st.caption(
            "Coupon dates are generated backwards from contractual maturity. "
            "Duration and convexity reprice the same dated cashflows used for "
            "the clean-price/YTM reconciliation."
        )

    try:
        local_risk_df = calculate_bond_risk_metrics(
            bonds,
            valuation_date=valuation_date,
            pricing_mode=pricing_mode,
            default_day_count_convention=(
                default_day_count_convention
            ),
            when_issued_policy=when_issued_policy,
            reconciliation_tolerance_per_100=(
                reconciliation_tolerance
            ),
        )
    except ValueError as exc:
        st.error(
            f"Bond pricing contract validation failed: {exc}"
        )
        return

    reconciliation_count = int(
        local_risk_df["price_reconciled"].sum()
    )
    total_bonds = int(len(local_risk_df))
    max_price_gap = float(
        local_risk_df[
            "dirty_price_reconciliation_error"
        ].abs().max()
    )
    when_issued_count = int(
        local_risk_df["schedule_status"]
        .astype(str)
        .str.contains("When-issued")
        .sum()
    )

    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Reconciled Bonds",
        f"{reconciliation_count}/{total_bonds}",
    )
    r2.metric(
        "Max |Dirty Price Gap|",
        f"{max_price_gap:.4f}",
    )
    r3.metric(
        "When-issued Positions",
        str(when_issued_count),
    )
    r4.metric(
        "Pricing Mode",
        (
            "Price-implied YTM"
            if pricing_mode == "Solve YTM from clean price"
            else "Supplied-YTM audit"
        ),
    )

    if reconciliation_count < total_bonds:
        st.warning(
            "One or more supplied YTMs do not reprice the quoted "
            "clean price within the selected tolerance. Review the "
            "bond-level reconciliation fields before using risk outputs."
        )

    if when_issued_count:
        st.warning(
            f"{when_issued_count} when-issued position(s) are included "
            "and explicitly flagged. Their accrued interest is zero "
            "before issue."
        )

    currencies = sorted(
        local_risk_df["currency"].astype(str).str.upper().unique().tolist()
    )

    st.subheader("Currency Translation Contract")
    with st.container(border=True):
        default_base_index = currencies.index("EUR") if "EUR" in currencies else 0
        base_currency = st.selectbox(
            "Portfolio base currency",
            currencies,
            index=default_base_index,
            help=(
                "All portfolio market value, DV01, scenario P&L, and hedge sizing outputs "
                "are translated into this currency before aggregation."
            ),
        )
        st.caption(
            "FX convention: one unit of local currency equals the entered number of base-currency units. "
            "Rates are manual demo assumptions, not live FX quotes."
        )

        fx_rates: dict[str, float] = {}
        fx_columns = st.columns(min(max(len(currencies), 1), 4))
        for index, currency in enumerate(currencies):
            with fx_columns[index % len(fx_columns)]:
                fx_rates[currency] = st.number_input(
                    f"{currency} to {base_currency}",
                    min_value=0.000001,
                    value=_default_demo_fx_to_base(currency, base_currency),
                    step=0.01,
                    format="%.6f",
                    disabled=(currency == base_currency),
                    key=f"fixed_income_fx_{currency}_to_{base_currency}",
                )

    try:
        risk_df = apply_fx_conversion(
            local_risk_df,
            base_currency=base_currency,
            fx_rates=fx_rates,
        )
        summary = summarize_portfolio(
            risk_df,
            base_currency=base_currency,
        )
    except ValueError as exc:
        st.error(f"Currency translation failed: {exc}")
        return

    summary_dict = portfolio_summary_to_dict(summary)
    currency_df = build_currency_exposure_table(risk_df)
    bucket_df = calculate_dv01_by_bucket(
        risk_df
    )
    credit_exposure_df = (
        build_credit_spread_exposure_table(
            risk_df
        )
    )

    st.subheader("Credit Spread Risk Contract")

    with st.container(border=True):
        st.caption(
            "Credit spread stress is separated from rates risk. "
            "Sovereign and rates-only bonds have zero CS01 and are "
            "excluded. Credit CS01 is calculated by direct +1 bp "
            "contractual-cashflow repricing; it remains a transparent "
            "parallel-spread proxy rather than full OAS pricing."
        )

        eligible_credit_df = (
            credit_exposure_df.loc[
                credit_exposure_df[
                    "credit_spread_eligible"
                ]
            ].copy()
        )
        excluded_credit_df = (
            credit_exposure_df.loc[
                ~credit_exposure_df[
                    "credit_spread_eligible"
                ]
            ].copy()
        )

        credit_spread_shocks_bps: dict[
            str,
            float,
        ] = {}

        if eligible_credit_df.empty:
            st.info(
                "No credit-spread-eligible bonds are present. "
                "The credit scenario will report zero P&L."
            )
        else:
            st.markdown(
                "**Spread shocks by "
                "currency / sector / rating curve**"
            )
            shock_columns = st.columns(
                min(
                    max(
                        len(eligible_credit_df),
                        1,
                    ),
                    3,
                )
            )

            for position, (_, exposure_row) in enumerate(
                eligible_credit_df.iterrows()
            ):
                curve_key = str(
                    exposure_row[
                        "credit_curve_key"
                    ]
                )
                with shock_columns[
                    position
                    % len(shock_columns)
                ]:
                    credit_spread_shocks_bps[
                        curve_key
                    ] = st.number_input(
                        f"{curve_key} shock (bps)",
                        value=50.0,
                        step=5.0,
                        format="%.1f",
                        key=(
                            "fixed_income_credit_shock_"
                            + str(position)
                        ),
                    )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Credit CS01 "
            f"({base_currency}/bp)",
            _format_currency(
                float(
                    eligible_credit_df[
                        "cs01_base"
                    ].sum()
                )
            ),
        )
        c2.metric(
            "Credit-Eligible Bonds",
            str(
                int(
                    eligible_credit_df[
                        "bond_count"
                    ].sum()
                )
            ),
        )
        c3.metric(
            "Rates-Only / Sovereign Bonds",
            str(
                int(
                    excluded_credit_df[
                        "bond_count"
                    ].sum()
                )
            ),
        )

        st.dataframe(
            credit_exposure_df.style.format(
                {
                    "full_market_value_base": "{:,.0f}",
                    "cs01_base": "{:,.2f}",
                    "spread_duration": "{:.4f}",
                    "pct_total_credit_cs01": "{:.1%}",
                }
            ),
            use_container_width=True,
        )

    scenario_df = calculate_scenario_pnl(
        risk_df,
        credit_spread_shocks_bps=(
            credit_spread_shocks_bps
        ),
    )
    worst_scenario = identify_worst_scenario(scenario_df)
    commentary = generate_fixed_income_commentary(risk_df, bucket_df, scenario_df)

    st.markdown("**Currency Exposure & Translation**")
    st.dataframe(
        currency_df.style.format(
            {
                "fx_to_base": "{:.6f}",
                "local_clean_market_value": "{:,.0f}",
                "local_full_market_value": "{:,.0f}",
                "local_accrued_interest_amount": "{:,.0f}",
                "clean_market_value_base": "{:,.0f}",
                "full_market_value_base": "{:,.0f}",
                "accrued_interest_amount_base": "{:,.0f}",
                "local_market_value": "{:,.0f}",
                "market_value_base": "{:,.0f}",
                "local_dv01": "{:,.0f}",
                "dv01_base": "{:,.0f}",
                "spread_duration": "{:.4f}",
                "cs01": "{:,.2f}",
                "cs01_base": "{:,.2f}",
                "pct_base_market_value": "{:.1%}",
            }
        ),
        use_container_width=True,
    )

    st.subheader("Portfolio Summary")
    st.caption(
        "Clean value is the quoted-price reporting value. Full value equals clean value plus accrued interest; DV01 and scenario P&L use full value."
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        f"Clean Market Value ({base_currency})",
        _format_currency(summary_dict["total_clean_market_value"]),
    )
    c2.metric(
        f"Full Market Value ({base_currency})",
        _format_currency(summary_dict["total_full_market_value"]),
    )
    c3.metric(
        f"Accrued Interest ({base_currency})",
        _format_currency(summary_dict["total_accrued_interest_amount"]),
    )
    c4.metric(
        "WA Yield",
        _format_percent(summary_dict["weighted_average_yield"]),
    )
    c5.metric(
        "WA Mod Duration",
        f"{summary_dict['weighted_average_modified_duration']:.2f}",
    )
    c6.metric(
        f"Total DV01 ({base_currency}/bp)",
        _format_currency(summary_dict["total_dv01"]),
    )

    st.caption(
        f"Bond count: {summary_dict['number_of_bonds']} | Full value is the economic aggregation and risk basis."
    )
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
                    "clean_market_value_base": "{:,.0f}",
                    "full_market_value_base": "{:,.0f}",
                    "market_value_base": "{:,.0f}",
                    "dv01_base": "{:,.0f}",
                    "pct_total_dv01": "{:.1%}",
                }
            ),
            use_container_width=True,
        )

    with c2:
        fig_bucket = px.bar(
            bucket_df,
            x="curve_bucket",
            y="dv01_base",
            title=f"DV01 by Curve Bucket ({base_currency})",
            labels={"curve_bucket": "Curve Bucket", "dv01_base": f"DV01 ({base_currency}/bp)"},
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
            delta=f"{_format_currency(worst_scenario['estimated_pnl'])} {base_currency}",
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
        f"Hedge instrument DV01 per unit ({base_currency}/bp)",
        min_value=1.0,
        value=75.0,
        step=5.0,
        help="The hedge-instrument DV01 must be expressed in the same base currency as the portfolio DV01.",
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
        currency_df=currency_df,
        credit_exposure_df=credit_exposure_df,
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
        "frequency",
        "valuation_date",
        "issue_date",
        "maturity_date",
        "previous_coupon_date",
        "next_coupon_date",
        "final_cashflow_date",
        "cashflow_count",
        "schedule_status",
        "day_count_convention",
        "pricing_mode",
        "clean_price",
        "accrued_interest_per_100",
        "dirty_price",
        "provided_yield_to_maturity",
        "pricing_yield_used",
        "yield_to_maturity",
        "model_clean_price",
        "model_dirty_price",
        "clean_price_reconciliation_error",
        "dirty_price_reconciliation_error",
        "price_reconciled",
        "pricing_status",
        "years_to_maturity",
        "modified_duration",
        "convexity",
        "clean_market_value",
        "full_market_value",
        "accrued_interest_amount",
        "fx_to_base",
        "clean_market_value_base",
        "full_market_value_base",
        "accrued_interest_amount_base",
        "market_value",
        "market_value_base",
        "dv01",
        "dv01_base",
        "credit_spread_eligible",
        "credit_risk_class",
        "credit_mapping_source",
        "credit_curve_key",
        "spread_duration",
        "cs01",
        "cs01_base",
        "spread_risk_method",
        "base_currency",
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
                "provided_yield_to_maturity": "{:.4%}",
                "pricing_yield_used": "{:.4%}",
                "yield_to_maturity": "{:.4%}",
                "model_clean_price": "{:.4f}",
                "model_dirty_price": "{:.4f}",
                "clean_price_reconciliation_error": "{:+.4f}",
                "dirty_price_reconciliation_error": "{:+.4f}",
                "years_to_maturity": "{:.2f}",
                "modified_duration": "{:.2f}",
                "convexity": "{:.2f}",
                "clean_market_value": "{:,.0f}",
                "full_market_value": "{:,.0f}",
                "accrued_interest_amount": "{:,.0f}",
                "fx_to_base": "{:.6f}",
                "clean_market_value_base": "{:,.0f}",
                "full_market_value_base": "{:,.0f}",
                "accrued_interest_amount_base": "{:,.0f}",
                "market_value": "{:,.0f}",
                "market_value_base": "{:,.0f}",
                "dv01": "{:,.0f}",
                "dv01_base": "{:,.0f}",
            }
        ),
        use_container_width=True,
    )

    st.subheader("DV01 by Bond")

    fig = px.bar(
        risk_df.sort_values("dv01_base", ascending=False),
        x="bond_id",
        y="dv01_base",
        color="curve_bucket",
        title=f"DV01 by Bond ({base_currency})",
        labels={"dv01_base": f"DV01 ({base_currency}/bp)", "bond_id": "Bond"},
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
        f"{_format_currency(pnl)} {base_currency}",
    )

    st.caption(
        "Convention: DV01 is positive and represents the approximate gain for a 1 bp fall in yield. "
        "Therefore, a positive yield move produces negative estimated P&L."
    )

    st.subheader("Methodology Notes")

    st.markdown(
        """
        - Coupon dates are generated backwards from contractual maturity rather than reconstructed from floating-point years-to-maturity.
        - The default pricing mode solves YTM from quoted clean price plus contractual accrued interest.
        - Audit mode preserves supplied YTM and exposes the clean/dirty quote reconciliation error.
        - Day-count convention, valuation date, coupon dates, when-issued status, and pricing status are explicit at bond level.
        - Clean price is quoted per 100 notional.
        - Dirty price = clean price + accrued interest per 100.
        - Local clean market value = clean price / 100 × notional in each bond currency.
        - Local full market value = dirty price / 100 × notional and includes accrued interest.
        - DV01, duration/convexity scenario P&L, portfolio weights, and hedge sizing use full market value.
        - FX-to-base = base-currency units per one unit of local currency.
        - Clean value, full value, accrued interest, DV01, and scenario P&L are aggregated only after FX translation.
        - Duration and convexity are calculated by repricing the same contractual cashflow schedule used for price/YTM reconciliation.
        - DV01 = modified duration × market value × 0.0001.
        - Scenario P&L uses duration/convexity approximation.
        - Credit spread shock uses modified duration as a spread-duration proxy.
        - Hedge approximation uses portfolio DV01 / hedge instrument DV01.
        - This MVP does not yet build a full discount curve or model business-day adjustment, ex-coupon rules, tax, or every market-specific convention.
        """
    )
