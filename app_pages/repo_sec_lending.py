from datetime import date, timedelta

import streamlit as st

from app_pages.common import render_module_header
from reports.excel_exporter import generate_financing_margin_report
from engines.repo_engine import (
    calculate_contractual_variation_margin,
    calculate_margin_call,
    calculate_margin_stress_table,
    calculate_refinancing_haircut_stress,
    calculate_refinancing_stress_table,
    calculate_repo_sensitivity_table,
    calculate_repo_trade,
    contractual_margin_result_to_dict,
    generate_contractual_margin_commentary,
    generate_repo_margin_commentary,
    margin_result_to_dict,
    refinancing_stress_result_to_dict,
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

        st.subheader("Contractual Variation Margin")
        st.info(
            "The existing repo keeps its contractual haircut. Variation "
            "margin is calculated against the accrued repurchase price on "
            "the selected margin date and the current dirty collateral value. "
            "A stressed haircut is handled separately as refinancing/re-roll "
            "liquidity risk."
        )

        margin_1, margin_2, margin_3 = st.columns(3)
        default_margin_date = min(
            start_date + timedelta(days=max(1, int(result.repo_days // 2))),
            end_date,
        )

        with margin_1:
            transaction_direction = st.selectbox(
                "Transaction direction",
                ["Cash lender / reverse repo", "Cash borrower / repo"],
                index=0,
            )
            margin_date = st.date_input(
                "Contractual margin date",
                value=default_margin_date,
                min_value=start_date,
                max_value=end_date,
            )
            netting_set_id = st.text_input("Netting-set ID", value="NS-1")

        with margin_2:
            current_dirty_collateral_value = st.number_input(
                "Current dirty collateral value",
                min_value=0.0,
                value=float(result.collateral_market_value * 0.95),
                step=100_000.0,
                help=(
                    "Enter the collateral dirty value at the margin date, "
                    "including accrued interest where relevant."
                ),
            )
            threshold = st.number_input(
                "Contractual threshold",
                min_value=0.0,
                value=0.0,
                step=10_000.0,
            )
            minimum_transfer_amount = st.number_input(
                "Minimum transfer amount (MTA)",
                min_value=0.0,
                value=0.0,
                step=10_000.0,
            )

        with margin_3:
            rounding_increment = st.number_input(
                "Margin rounding increment",
                min_value=0.0,
                value=1.0,
                step=1_000.0,
            )
            rounding_method = st.selectbox(
                "Margin rounding method",
                ["Nearest", "Away from zero", "None"],
                index=0,
            )

        try:
            margin_result = calculate_contractual_variation_margin(
                cash_amount=result.cash_amount,
                repo_rate=result.repo_rate,
                start_date=result.start_date,
                end_date=result.end_date,
                margin_date=margin_date,
                day_count_basis=result.day_count_basis,
                current_dirty_collateral_value=current_dirty_collateral_value,
                contractual_haircut=result.haircut,
                transaction_direction=transaction_direction,
                threshold=threshold,
                minimum_transfer_amount=minimum_transfer_amount,
                rounding_increment=rounding_increment,
                rounding_method=rounding_method,
                currency=currency,
                netting_set_id=netting_set_id,
            )
        except ValueError as exc:
            st.error(f"Repo margin contract error: {exc}")
            return

        margin_dict = contractual_margin_result_to_dict(margin_result)
        commentary = generate_contractual_margin_commentary(margin_result)

        vm1, vm2, vm3, vm4, vm5 = st.columns(5)
        vm1.metric(
            "Accrued Repurchase Price",
            _format_currency(margin_result.accrued_repurchase_price, currency),
        )
        vm2.metric(
            "Dirty Collateral",
            _format_currency(
                margin_result.current_dirty_collateral_value,
                currency,
            ),
        )
        vm3.metric(
            "Eligible Collateral",
            _format_currency(margin_result.current_eligible_collateral, currency),
        )
        vm4.metric(
            "Securities Transfer (Dirty Value)",
            _format_currency(margin_result.collateral_transfer_amount, currency),
        )
        vm5.metric(
            "Transfer Required?",
            "Yes" if margin_result.margin_transfer_required else "No",
        )
        st.caption(margin_result.transfer_direction)
        st.caption(
            f"Cash-equivalent contractual VM: {abs(margin_result.contractual_margin_transfer):,.2f} {currency}. "
            "Threshold, MTA and rounding apply to that amount. Securities dirty value equals cash-equivalent VM divided by (1 − contractual haircut)."
        )

        with st.container(border=True):
            for comment in commentary:
                st.markdown(f"- {comment}")

        st.subheader("Refinancing / Re-roll Haircut Stress")
        st.caption(
            "This section estimates funding-capacity and liquidity changes "
            "on a refinancing or renegotiation. It is not contractual "
            "variation margin on the existing repo."
        )

        refi_1, refi_2 = st.columns(2)
        with refi_1:
            refinancing_price_shock_pct = st.number_input(
                "Additional refinancing collateral shock (%)",
                min_value=-50.0,
                max_value=50.0,
                value=0.0,
                step=0.5,
            )
        with refi_2:
            refinancing_haircut_pct = st.number_input(
                "Refinancing / re-roll haircut (%)",
                min_value=0.0,
                max_value=99.0,
                value=haircut_pct + 2.0,
                step=0.25,
            )

        refinancing_result = calculate_refinancing_haircut_stress(
            current_dirty_collateral_value=current_dirty_collateral_value,
            contractual_haircut=result.haircut,
            refinancing_haircut=refinancing_haircut_pct / 100.0,
            collateral_price_shock=refinancing_price_shock_pct / 100.0,
            currency=currency,
        )

        rf1, rf2, rf3, rf4 = st.columns(4)
        rf1.metric(
            "Current Funding Capacity",
            _format_currency(refinancing_result.current_funding_capacity, currency),
        )
        rf2.metric(
            "Stressed Refinance Capacity",
            _format_currency(
                refinancing_result.stressed_refinancing_funding_capacity,
                currency,
            ),
        )
        rf3.metric(
            "Refinancing Liquidity Shortfall",
            _format_currency(
                refinancing_result.refinancing_liquidity_shortfall,
                currency,
            ),
        )
        rf4.metric("Contractual Margin Call?", "No — separate liquidity stress")
        st.caption(f"Main refinancing driver: {refinancing_result.driver}.")

        margin_stress_df = calculate_refinancing_stress_table(
            current_dirty_collateral_value=current_dirty_collateral_value,
            contractual_haircut=result.haircut,
            currency=currency,
        )
        st.dataframe(
            margin_stress_df.style.format(
                {
                    "collateral_price_shock": "{:.2%}",
                    "contractual_haircut": "{:.2%}",
                    "refinancing_haircut": "{:.2%}",
                    "current_dirty_collateral_value": "{:,.0f}",
                    "shocked_dirty_collateral_value": "{:,.0f}",
                    "current_funding_capacity": "{:,.0f}",
                    "price_shocked_capacity_at_contractual_haircut": "{:,.0f}",
                    "stressed_refinancing_funding_capacity": "{:,.0f}",
                    "collateral_price_liquidity_change": "{:,.0f}",
                    "haircut_reset_liquidity_change": "{:,.0f}",
                    "total_liquidity_change": "{:,.0f}",
                    "refinancing_liquidity_shortfall": "{:,.0f}",
                    "refinancing_liquidity_surplus": "{:,.0f}",
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
            - Cash amount = collateral market value × (1 − contractual haircut).
            - Repo interest uses the selected money-market day-count basis.
            - Accrued repurchase price at the margin date = initial cash + repo interest accrued to that date.
            - Current collateral is entered as a **dirty value** at the margin date.
            - Contractual eligible collateral = current dirty collateral value × (1 − contractual haircut).
            - The contractual haircut remains fixed for variation margin on the existing repo.
            - Threshold, MTA and rounding are applied explicitly before an executable transfer is shown.
            - A higher stressed haircut belongs to **refinancing/re-roll liquidity stress**, not automatically to variation margin.
            - Repo and reverse-repo direction changes the transfer label, while the cash-lender exposure gap remains explicit.
            - Currency and netting-set ID are recorded; this proxy does not implement full GMRA netting, disputes, settlement timing or legal close-out.
            """
        )
    with sec_lending_tab:
        st.subheader("Securities Lending Inputs")

        st.info(
            "Choose one collateral path. Non-cash economics use a securities "
            "loan fee. Cash-collateral economics use reinvestment income less "
            "the rebate. The two revenue conventions are mutually exclusive."
        )

        setup_1, setup_2 = st.columns(2)

        with setup_1:
            collateral_type = st.selectbox(
                "Collateral type",
                ["Non-cash", "Cash"],
                index=0,
                help=(
                    "Non-cash collateral uses a securities loan fee. "
                    "Cash collateral uses reinvestment yield less rebate."
                ),
            )

        with setup_2:
            perspective = st.selectbox(
                "Revenue perspective",
                ["Beneficial owner", "Lending agent"],
                index=0,
                help=(
                    "Beneficial owner receives gross lending revenue less "
                    "the lending-agent share and entered costs. The lending "
                    "agent receives its fee share less entered costs."
                ),
            )

        c1, c2, c3 = st.columns(3)

        with c1:
            sec_currency = st.selectbox(
                "Securities lending currency",
                ["EUR", "USD", "GBP", "CHF"],
            )
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
                "Non-cash borrow fee rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=1.25,
                step=0.10,
                disabled=collateral_type == "Cash",
                help=(
                    "Used only for non-cash collateral. It is excluded "
                    "from the cash-collateral revenue path."
                ),
            )
            rebate_rate_pct = st.number_input(
                "Cash rebate rate (%)",
                min_value=-10.0,
                max_value=20.0,
                value=0.50,
                step=0.10,
                disabled=collateral_type == "Non-cash",
                help=(
                    "Used only for cash collateral. It is the annualized "
                    "rate credited on cash collateral."
                ),
            )
            reinvestment_yield_pct = st.number_input(
                "Cash reinvestment yield (%)",
                min_value=-10.0,
                max_value=30.0,
                value=4.00,
                step=0.10,
                disabled=collateral_type == "Non-cash",
                help=(
                    "Used only for cash collateral. Gross cash revenue is "
                    "reinvestment income less the rebate."
                ),
            )

        with c3:
            loan_days = st.number_input(
                "Loan days",
                min_value=1,
                max_value=365,
                value=30,
                step=1,
            )
            sec_day_count_basis = st.selectbox(
                "Securities lending day-count basis",
                [360, 365],
                index=0,
            )
            utilization_pct = st.number_input(
                "Utilization proxy (%)",
                min_value=0.0,
                max_value=100.0,
                value=65.0,
                step=1.0,
            )
            is_special = st.checkbox(
                "Flag as special / hard-to-borrow",
                value=False,
            )

        fee_1, fee_2 = st.columns(2)

        with fee_1:
            agent_fee_share_pct = st.number_input(
                "Lending-agent share of positive gross revenue (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
            )

        with fee_2:
            other_costs = st.number_input(
                "Other perspective-specific costs",
                min_value=0.0,
                value=0.0,
                step=100.0,
            )

        effective_borrow_fee_rate = (
            borrow_fee_pct / 100.0
            if collateral_type == "Non-cash"
            else 0.0
        )
        effective_rebate_rate = (
            rebate_rate_pct / 100.0
            if collateral_type == "Cash"
            else 0.0
        )
        effective_reinvestment_yield = (
            reinvestment_yield_pct / 100.0
            if collateral_type == "Cash"
            else 0.0
        )

        try:
            sec_result = calculate_securities_lending_trade(
                security_market_value=security_market_value,
                collateral_type=collateral_type,
                perspective=perspective,
                borrow_fee_rate=effective_borrow_fee_rate,
                rebate_rate=effective_rebate_rate,
                reinvestment_yield=effective_reinvestment_yield,
                collateralization_rate=collateralization_pct / 100.0,
                loan_days=int(loan_days),
                day_count_basis=int(sec_day_count_basis),
                utilization_proxy=utilization_pct / 100.0,
                is_special=is_special,
                agent_fee_share=agent_fee_share_pct / 100.0,
                other_costs=float(other_costs),
            )
        except ValueError as exc:
            st.error(f"Securities-lending input error: {exc}")
            return

        sec_result_dict = sec_lending_result_to_dict(sec_result)
        sec_commentary = generate_sec_lending_commentary(sec_result)

        st.subheader("Securities Lending Economics")

        s1, s2, s3, s4, s5, s6 = st.columns(6)

        s1.metric(
            "Collateral Required",
            _format_currency(
                sec_result.collateral_required,
                sec_currency,
            ),
        )

        if collateral_type == "Non-cash":
            s2.metric(
                "Non-cash Fee Income",
                _format_currency(
                    sec_result.borrow_fee_amount,
                    sec_currency,
                ),
            )
            s3.metric(
                "Agent Fee",
                _format_currency(
                    sec_result.agent_fee_amount,
                    sec_currency,
                ),
            )
            s4.metric(
                "Other Costs",
                _format_currency(
                    sec_result.other_costs,
                    sec_currency,
                ),
            )
        else:
            s2.metric(
                "Reinvestment Income",
                _format_currency(
                    sec_result.reinvestment_income,
                    sec_currency,
                ),
            )
            s3.metric(
                "Rebate Paid",
                _format_currency(
                    sec_result.rebate_amount,
                    sec_currency,
                ),
            )
            s4.metric(
                "Gross Cash Spread Revenue",
                _format_currency(
                    sec_result.gross_lending_revenue,
                    sec_currency,
                ),
            )

        s5.metric(
            f"Net Revenue — {perspective}",
            _format_currency(
                sec_result.net_lending_revenue,
                sec_currency,
            ),
        )
        s6.metric(
            "Specialness Heuristic",
            sec_result.specialness_label,
        )

        st.caption(sec_result.revenue_convention)

        with st.container(border=True):
            for comment in sec_commentary:
                st.markdown(f"- {comment}")

        st.subheader("Collateral Economics Comparison")

        comparison_df = calculate_borrow_fee_comparison_table(
            security_market_value=security_market_value,
            collateral_type=collateral_type,
            perspective=perspective,
            rebate_rate=effective_rebate_rate,
            reinvestment_yield=effective_reinvestment_yield,
            collateralization_rate=collateralization_pct / 100.0,
            loan_days=int(loan_days),
            day_count_basis=int(sec_day_count_basis),
            agent_fee_share=agent_fee_share_pct / 100.0,
            other_costs=float(other_costs),
            utilization_proxy=utilization_pct / 100.0,
        )

        comparison_columns = [
            "scenario",
            "collateral_type",
            "perspective",
            "borrow_fee_rate",
            "rebate_rate",
            "reinvestment_yield",
            "borrow_fee_amount",
            "reinvestment_income",
            "rebate_amount",
            "gross_lending_revenue",
            "agent_fee_amount",
            "other_costs",
            "net_lending_revenue",
            "specialness_label",
        ]

        st.dataframe(
            comparison_df[
                comparison_columns
            ].style.format(
                {
                    "borrow_fee_rate": "{:.2%}",
                    "rebate_rate": "{:.2%}",
                    "reinvestment_yield": "{:.2%}",
                    "borrow_fee_amount": "{:,.0f}",
                    "reinvestment_income": "{:,.0f}",
                    "rebate_amount": "{:,.0f}",
                    "gross_lending_revenue": "{:,.0f}",
                    "agent_fee_amount": "{:,.0f}",
                    "other_costs": "{:,.0f}",
                    "net_lending_revenue": "{:,.0f}",
                }
            ),
            use_container_width=True,
        )

        st.subheader("Financing & Margin Excel Report")

        financing_report_bytes = generate_financing_margin_report(
            repo_summary=result_dict,
            repo_sensitivity_df=sensitivity_df,
            margin_summary=margin_dict,
            margin_stress_df=margin_stress_df,
            repo_commentary=commentary,
            sec_lending_summary=sec_result_dict,
            borrow_comparison_df=comparison_df[
                comparison_columns
            ],
            sec_lending_commentary=sec_commentary,
        )

        st.download_button(
            label="Download Financing & Margin Report",
            data=financing_report_bytes,
            file_name="financing_margin_report.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        st.subheader("Securities Lending Methodology Notes")
        st.markdown(
            """
            - **Collateral paths are mutually exclusive.**
            - **Non-cash collateral:** gross lender revenue equals security market value × borrow fee × days / day-count basis.
            - **Cash collateral:** gross lender revenue equals collateral required × (reinvestment yield − rebate rate) × days / day-count basis.
            - Agent fee equals the selected share of positive gross lender revenue.
            - Beneficial-owner net revenue equals gross lender revenue less agent fee and entered costs.
            - Lending-agent net revenue equals agent fee less entered costs.
            - Collateral required equals security market value × collateralization rate.
            - Rebate and reinvestment yield are never applied to the non-cash path.
            - Borrow fee is never applied to the cash-collateral path.
            - Specialness is an illustrative heuristic based on fee, utilization proxy, and the manual flag; it is not calibrated to live inventory.
            - This proxy excludes recall risk, manufactured dividends, settlement, counterparty default, tax, indemnification, and full reinvestment-risk modelling.
            """
        )
