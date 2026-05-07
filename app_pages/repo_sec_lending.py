from datetime import date, timedelta

import streamlit as st

from app_pages.common import render_module_header
from engines.repo_engine import (
    calculate_margin_call,
    calculate_margin_stress_table,
    calculate_repo_sensitivity_table,
    calculate_repo_trade,
    generate_repo_margin_commentary,
    margin_result_to_dict,
    repo_result_to_dict,
)
from engines.sec_lending_engine import (
    calculate_borrow_fee_comparison_table,
    calculate_securities_lending_trade,
    generate_sec_lending_commentary,
    sec_lending_result_to_dict,
)


def _format_currency(value: float, currency: str = "EUR") -> str:
    symbol = "€" if currency == "EUR" else "$" if currency == "USD" else currency
    return f"{symbol}{value:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def render() -> None:
    render_module_header(
        title="Repo & Securities Lending",
        caption="Funding, collateral, haircut, margin call, borrow fee, rebate, and specialness analytics.",
        objective=(
            "Objective: explain how repo and securities lending terms affect funding proceeds, collateral eligibility, "
            "margin calls, borrow cost, and lending revenue."
        ),
    )

    repo_tab, sec_lending_tab = st.tabs(["Repo Cashflow & Margin Analytics", "Securities Lending Analytics"])

    with repo_tab:
        st.subheader("Repo Trade Inputs")

        c1, c2, c3 = st.columns(3)

        with c1:
            currency = st.selectbox("Repo currency", ["EUR", "USD", "GBP", "CHF"])
            collateral_market_value = st.number_input(
                "Collateral market value",
                min_value=1_000.0,
                value=10_000_000.0,
                step=100_000.0,
            )

        with c2:
            haircut_pct = st.number_input(
                "Initial haircut (%)",
                min_value=0.0,
                max_value=99.0,
                value=2.0,
                step=0.25,
            )
            repo_rate_pct = st.number_input(
                "Repo rate (%)",
                min_value=-5.0,
                max_value=25.0,
                value=4.0,
                step=0.10,
            )

        with c3:
            start_date = st.date_input("Repo start date", value=date.today())
            end_date = st.date_input("Repo end date", value=date.today() + timedelta(days=30))
            day_count_basis = st.selectbox("Repo day-count basis", [360, 365], index=0)

        haircut = haircut_pct / 100.0
        repo_rate = repo_rate_pct / 100.0

        result = calculate_repo_trade(
            collateral_market_value=collateral_market_value,
            haircut=haircut,
            repo_rate=repo_rate,
            start_date=start_date,
            end_date=end_date,
            day_count_basis=day_count_basis,
            currency=currency,
        )

        result_dict = repo_result_to_dict(result)

        st.subheader("Repo Cashflow Summary")

        m1, m2, m3, m4, m5 = st.columns(5)

        m1.metric("Collateral Value", _format_currency(result.collateral_market_value, currency))
        m2.metric("Haircut", _format_percent(result.haircut))
        m3.metric("Cash Amount", _format_currency(result.cash_amount, currency))
        m4.metric("Repo Interest", _format_currency(result.repo_interest, currency))
        m5.metric("Repurchase Amount", _format_currency(result.repurchase_amount, currency))

        st.caption(
            "Cash amount = collateral market value x (1 - haircut). "
            "Repo interest = cash amount x repo rate x days / day-count basis."
        )

        st.subheader("Trade Details")

        trade_details = {
            "Currency": str(result.currency),
            "Start Date": str(result_dict["start_date"]),
            "End Date": str(result_dict["end_date"]),
            "Repo Days": str(result.repo_days),
            "Day-Count Basis": str(result.day_count_basis),
            "Repo Rate": _format_percent(result.repo_rate),
        }

        st.dataframe(
            [{"Metric": key, "Value": value} for key, value in trade_details.items()],
            use_container_width=True,
        )

        st.subheader("Collateral Shock & Margin Call")

        s1, s2 = st.columns(2)

        with s1:
            collateral_price_shock_pct = st.number_input(
                "Collateral price shock (%)",
                min_value=-50.0,
                max_value=50.0,
                value=-5.0,
                step=0.5,
            )

        with s2:
            new_haircut_pct = st.number_input(
                "Stressed haircut (%)",
                min_value=0.0,
                max_value=99.0,
                value=haircut_pct + 2.0,
                step=0.25,
            )

        margin_result = calculate_margin_call(
            collateral_market_value=result.collateral_market_value,
            cash_amount=result.cash_amount,
            original_haircut=result.haircut,
            collateral_price_shock=collateral_price_shock_pct / 100.0,
            new_haircut=new_haircut_pct / 100.0,
        )

        margin_dict = margin_result_to_dict(margin_result)
        commentary = generate_repo_margin_commentary(margin_result)

        mc1, mc2, mc3, mc4 = st.columns(4)

        mc1.metric(
            "Adjusted Collateral",
            _format_currency(margin_result.adjusted_collateral_value, currency),
        )
        mc2.metric(
            "Eligible Collateral",
            _format_currency(margin_result.new_eligible_collateral, currency),
        )
        mc3.metric(
            "Margin Deficit",
            _format_currency(margin_result.margin_deficit, currency),
        )
        mc4.metric(
            "Margin Call?",
            "Yes" if margin_result.margin_call_required else "No",
        )

        with st.container(border=True):
            for comment in commentary:
                st.markdown(f"- {comment}")

        st.subheader("Margin Stress Scenarios")

        margin_stress_df = calculate_margin_stress_table(
            collateral_market_value=result.collateral_market_value,
            cash_amount=result.cash_amount,
            original_haircut=result.haircut,
        )

        st.dataframe(
            margin_stress_df.style.format(
                {
                    "collateral_price_shock": "{:.2%}",
                    "original_haircut": "{:.2%}",
                    "new_haircut": "{:.2%}",
                    "adjusted_collateral_value": "{:,.0f}",
                    "new_eligible_collateral": "{:,.0f}",
                    "margin_deficit": "{:,.0f}",
                    "margin_surplus": "{:,.0f}",
                    "deficit_pct_of_original_collateral": "{:.2%}",
                }
            ),
            use_container_width=True,
        )

        st.subheader("Simple Funding Sensitivity")

        sensitivity_df = calculate_repo_sensitivity_table(
            collateral_market_value=collateral_market_value,
            haircut=haircut,
            repo_rate=repo_rate,
            start_date=start_date,
            end_date=end_date,
            day_count_basis=day_count_basis,
            currency=currency,
        )

        st.dataframe(
            sensitivity_df.style.format(
                {
                    "haircut": "{:.2%}",
                    "repo_rate": "{:.2%}",
                    "cash_amount": "{:,.0f}",
                    "repo_interest": "{:,.0f}",
                    "repurchase_amount": "{:,.0f}",
                }
            ),
            use_container_width=True,
        )

        st.subheader("Repo Methodology Notes")

        st.markdown(
            """
            - Haircut is the percentage deduction applied to collateral value.
            - A higher haircut reduces the cash amount available against the same collateral.
            - Repo interest is calculated using a simple money-market convention.
            - Repurchase amount equals initial cash amount plus repo interest.
            - Adjusted collateral value = original collateral value x (1 + collateral price shock).
            - Eligible collateral = adjusted collateral value x (1 - stressed haircut).
            - Margin deficit = max(0, cash amount - eligible collateral).
            - This module does not model legal close-out, settlement frictions, or counterparty default.
            """
        )

    with sec_lending_tab:
        st.subheader("Securities Lending Inputs")

        c1, c2, c3 = st.columns(3)

        with c1:
            sec_currency = st.selectbox("Securities lending currency", ["EUR", "USD", "GBP", "CHF"])
            security_market_value = st.number_input(
                "Security market value",
                min_value=1_000.0,
                value=5_000_000.0,
                step=100_000.0,
            )
            collateralization_pct = st.number_input(
                "Collateralization rate (%)",
                min_value=1.0,
                max_value=200.0,
                value=102.0,
                step=0.5,
            )

        with c2:
            borrow_fee_pct = st.number_input(
                "Borrow fee rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=1.25,
                step=0.10,
            )
            rebate_rate_pct = st.number_input(
                "Rebate rate (%)",
                min_value=-10.0,
                max_value=20.0,
                value=0.50,
                step=0.10,
            )

        with c3:
            loan_days = st.number_input(
                "Loan days",
                min_value=1,
                max_value=365,
                value=30,
                step=1,
            )
            sec_day_count_basis = st.selectbox("Securities lending day-count basis", [360, 365], index=0)
            utilization_pct = st.number_input(
                "Utilization proxy (%)",
                min_value=0.0,
                max_value=100.0,
                value=65.0,
                step=1.0,
            )
            is_special = st.checkbox("Flag as special / hard-to-borrow", value=False)

        sec_result = calculate_securities_lending_trade(
            security_market_value=security_market_value,
            borrow_fee_rate=borrow_fee_pct / 100.0,
            rebate_rate=rebate_rate_pct / 100.0,
            collateralization_rate=collateralization_pct / 100.0,
            loan_days=int(loan_days),
            day_count_basis=int(sec_day_count_basis),
            utilization_proxy=utilization_pct / 100.0,
            is_special=is_special,
        )

        sec_result_dict = sec_lending_result_to_dict(sec_result)
        sec_commentary = generate_sec_lending_commentary(sec_result)

        st.subheader("Securities Lending Summary")

        s1, s2, s3, s4, s5 = st.columns(5)

        s1.metric("Collateral Required", _format_currency(sec_result.collateral_required, sec_currency))
        s2.metric("Borrow Fee Amount", _format_currency(sec_result.borrow_fee_amount, sec_currency))
        s3.metric("Rebate Amount", _format_currency(sec_result.rebate_amount, sec_currency))
        s4.metric("Net Revenue", _format_currency(sec_result.net_lending_revenue, sec_currency))
        s5.metric("Specialness", sec_result.specialness_label)

        with st.container(border=True):
            for comment in sec_commentary:
                st.markdown(f"- {comment}")

        st.subheader("Normal vs Special Borrow Comparison")

        comparison_df = calculate_borrow_fee_comparison_table(
            security_market_value=security_market_value,
            rebate_rate=rebate_rate_pct / 100.0,
            collateralization_rate=collateralization_pct / 100.0,
            loan_days=int(loan_days),
            day_count_basis=int(sec_day_count_basis),
        )

        st.dataframe(
            comparison_df.style.format(
                {
                    "borrow_fee_rate": "{:.2%}",
                    "rebate_rate": "{:.2%}",
                    "utilization_proxy": "{:.2%}",
                    "collateral_required": "{:,.0f}",
                    "borrow_fee_amount": "{:,.0f}",
                    "rebate_amount": "{:,.0f}",
                    "net_lending_revenue": "{:,.0f}",
                }
            ),
            use_container_width=True,
        )

        st.subheader("Securities Lending Methodology Notes")

        st.markdown(
            """
            - Borrow fee is an annualized fee charged for borrowing the security.
            - Rebate is the rate paid on collateral in this simplified framework.
            - Collateral required = security market value x collateralization rate.
            - Borrow fee amount = security market value x borrow fee x days / day-count basis.
            - Rebate amount = collateral required x rebate rate x days / day-count basis.
            - Simplified net lending revenue = borrow fee amount - rebate amount.
            - Specialness classification is based on borrow fee, utilization proxy, and manual special flag.
            - This module does not model recall risk, manufactured dividends, settlement, counterparty risk, or full securities finance economics.
            """
        )
