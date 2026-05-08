"""
Excel Exporter.

This module centralizes Excel report generation for the platform.

Current implemented report:
- Fixed Income Risk Report
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def _auto_adjust_columns(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    """Auto-adjust Excel column widths based on dataframe content.

    Robust against strings, floats, integers, booleans, None, and mixed object columns.
    """

    worksheet = writer.sheets[sheet_name]

    for idx, column in enumerate(df.columns):
        values = df[column].to_numpy().flatten()
        max_length = max(
            [len(str(column))] + [len(str(value)) for value in values]
        )
        worksheet.set_column(idx, idx, min(max_length + 2, 45))


def _write_methodology_sheet(writer: pd.ExcelWriter, methodology_items: list[str]) -> None:
    """Write a methodology sheet with assumptions and limitations."""

    methodology_df = pd.DataFrame({"Methodology / Assumption": methodology_items})
    methodology_df.to_excel(writer, sheet_name="Methodology", index=False, startrow=2)

    workbook = writer.book
    worksheet = writer.sheets["Methodology"]

    title_format = workbook.add_format(
        {"bold": True, "font_size": 16, "border": 0}
    )
    header_format = workbook.add_format(
        {"bold": True, "bg_color": "#D9EAF7", "border": 1}
    )
    wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

    worksheet.write(0, 0, "Fixed Income Risk Report — Methodology", title_format)
    worksheet.set_row(2, None, header_format)
    worksheet.set_column(0, 0, 120, wrap_format)


def generate_fixed_income_risk_report(
    summary: dict[str, Any],
    risk_df: pd.DataFrame,
    bucket_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    commentary: list[str],
) -> bytes:
    """Generate a desk-style Fixed Income Risk Report as Excel bytes.

    Sheets:
    1. Summary
    2. Bond_Level_Risk
    3. DV01_Buckets
    4. Scenario_PnL
    5. Methodology

    The report uses simplified analytics and synthetic/sample data. It is not
    investment advice and not a bank-grade risk system.
    """

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        title_format = workbook.add_format(
            {"bold": True, "font_size": 16, "border": 0}
        )
        section_format = workbook.add_format(
            {"bold": True, "font_size": 12, "bg_color": "#D9EAF7", "border": 1}
        )
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#EAF3F8", "border": 1}
        )
        money_format = workbook.add_format({"num_format": "#,##0"})
        percent_format = workbook.add_format({"num_format": "0.00%"})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        text_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})

        # ------------------------------------------------------------------
        # Summary sheet
        # ------------------------------------------------------------------
        summary_rows = [
            ("Total Market Value", summary.get("total_market_value")),
            ("Weighted Average Yield", summary.get("weighted_average_yield")),
            (
                "Weighted Average Modified Duration",
                summary.get("weighted_average_modified_duration"),
            ),
            ("Weighted Average Convexity", summary.get("weighted_average_convexity")),
            ("Total DV01", summary.get("total_dv01")),
            ("Number of Bonds", summary.get("number_of_bonds")),
        ]

        summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False, startrow=3)

        summary_ws = writer.sheets["Summary"]
        summary_ws.write(0, 0, "Fixed Income Risk Report", title_format)
        summary_ws.write(
            1,
            0,
            "Desk-oriented analytics report using simplified bond risk approximations.",
        )
        summary_ws.set_row(3, None, header_format)
        summary_ws.set_column(0, 0, 42)
        summary_ws.set_column(1, 1, 22)

        # Format selected rows manually.
        summary_ws.set_column(1, 1, 22, number_format)

        # Commentary section
        start_commentary_row = len(summary_df) + 6
        summary_ws.write(start_commentary_row, 0, "Desk Commentary", section_format)

        for offset, comment in enumerate(commentary, start=1):
            summary_ws.write(start_commentary_row + offset, 0, comment, text_wrap)

        summary_ws.set_column(0, 0, 110, text_wrap)

        # ------------------------------------------------------------------
        # Bond-level risk
        # ------------------------------------------------------------------
        bond_report_cols = [
            "bond_id",
            "issuer",
            "currency",
            "coupon_rate",
            "maturity_date",
            "frequency",
            "clean_price",
            "accrued_interest_per_100",
            "dirty_price",
            "yield_to_maturity",
            "years_to_maturity",
            "modified_duration",
            "convexity",
            "market_value",
            "dv01",
            "rating",
            "sector",
            "spread_bps",
            "curve_bucket",
        ]

        bond_report = risk_df[bond_report_cols].copy()
        bond_report.to_excel(writer, sheet_name="Bond_Level_Risk", index=False)

        bond_ws = writer.sheets["Bond_Level_Risk"]
        bond_ws.set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Bond_Level_Risk", bond_report)

        # ------------------------------------------------------------------
        # DV01 buckets
        # ------------------------------------------------------------------
        bucket_df.to_excel(writer, sheet_name="DV01_Buckets", index=False)

        bucket_ws = writer.sheets["DV01_Buckets"]
        bucket_ws.set_row(0, None, header_format)
        _auto_adjust_columns(writer, "DV01_Buckets", bucket_df)

        # ------------------------------------------------------------------
        # Scenario P&L
        # ------------------------------------------------------------------
        scenario_df.to_excel(writer, sheet_name="Scenario_PnL", index=False)

        scenario_ws = writer.sheets["Scenario_PnL"]
        scenario_ws.set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Scenario_PnL", scenario_df)

        # ------------------------------------------------------------------
        # Methodology
        # ------------------------------------------------------------------
        methodology_items = [
            "Clean price is quoted per 100 notional.",
            "Dirty price equals clean price plus accrued interest per 100.",
            "Market value equals clean price / 100 multiplied by notional.",
            "Coupon rate and yield to maturity are stored as decimals, e.g. 5% = 0.05.",
            "Duration and convexity are calculated using transparent yield-implied cashflow approximations.",
            "DV01 is positive and represents the approximate gain for a 1 bp fall in yield.",
            "Estimated P&L for a positive yield shock is negative under the project convention.",
            "Scenario P&L uses duration and convexity approximation, not full bond revaluation.",
            "Credit spread shock uses modified duration as a simplified spread-duration proxy.",
            "The dataset is synthetic and for demonstration only.",
            "This report is not investment advice, not a trading signal, and not a bank-grade risk report.",
        ]

        _write_methodology_sheet(writer, methodology_items)

    output.seek(0)
    return output.getvalue()

def _write_key_value_sheet(
    writer: pd.ExcelWriter,
    sheet_name: str,
    title: str,
    data: dict,
    commentary: list[str] | None = None,
) -> None:
    """Write a key-value summary sheet with optional commentary."""

    workbook = writer.book
    title_format = workbook.add_format({"bold": True, "font_size": 16})
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
    wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

    summary_df = pd.DataFrame(
        [{"Metric": key, "Value": value} for key, value in data.items()]
    )

    summary_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=3)

    worksheet = writer.sheets[sheet_name]
    worksheet.write(0, 0, title, title_format)
    worksheet.set_row(3, None, header_format)
    worksheet.set_column(0, 0, 42)
    worksheet.set_column(1, 1, 45)

    if commentary:
        start_row = len(summary_df) + 6
        worksheet.write(start_row, 0, "Desk Commentary", header_format)

        for offset, comment in enumerate(commentary, start=1):
            worksheet.write(start_row + offset, 0, comment, wrap_format)

        worksheet.set_column(0, 0, 120, wrap_format)


def generate_financing_margin_report(
    repo_summary: dict[str, Any],
    repo_sensitivity_df: pd.DataFrame,
    margin_summary: dict[str, Any],
    margin_stress_df: pd.DataFrame,
    repo_commentary: list[str],
    sec_lending_summary: dict[str, Any],
    borrow_comparison_df: pd.DataFrame,
    sec_lending_commentary: list[str],
) -> bytes:
    """Generate a Repo & Securities Lending Financing/Margin Excel report.

    Sheets:
    1. Repo_Summary
    2. Repo_Sensitivity
    3. Margin_Summary
    4. Margin_Stress
    5. Sec_Lending_Summary
    6. Borrow_Comparison
    7. Methodology

    The report uses simplified analytics and synthetic/manual inputs. It is not
    a legal, collateral management, settlement, or counterparty risk system.
    """

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#EAF3F8", "border": 1}
        )
        title_format = workbook.add_format({"bold": True, "font_size": 16})
        wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Repo_Summary",
            title="Repo Cashflow Summary",
            data=repo_summary,
            commentary=None,
        )

        repo_sensitivity_df.to_excel(
            writer,
            sheet_name="Repo_Sensitivity",
            index=False,
        )
        writer.sheets["Repo_Sensitivity"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Repo_Sensitivity", repo_sensitivity_df)

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Margin_Summary",
            title="Repo Margin Call Summary",
            data=margin_summary,
            commentary=repo_commentary,
        )

        margin_stress_df.to_excel(
            writer,
            sheet_name="Margin_Stress",
            index=False,
        )
        writer.sheets["Margin_Stress"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Margin_Stress", margin_stress_df)

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Sec_Lending_Summary",
            title="Securities Lending Summary",
            data=sec_lending_summary,
            commentary=sec_lending_commentary,
        )

        borrow_comparison_df.to_excel(
            writer,
            sheet_name="Borrow_Comparison",
            index=False,
        )
        writer.sheets["Borrow_Comparison"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Borrow_Comparison", borrow_comparison_df)

        methodology_items = [
            "Repo haircut is stored as a decimal, e.g. 2% = 0.02.",
            "Repo cash amount equals collateral market value multiplied by one minus haircut.",
            "Repo interest equals cash amount multiplied by repo rate multiplied by days divided by day-count basis.",
            "Repurchase amount equals cash amount plus repo interest.",
            "Adjusted collateral value equals collateral market value multiplied by one plus collateral price shock.",
            "Eligible collateral equals adjusted collateral value multiplied by one minus stressed haircut.",
            "Margin deficit equals max(0, cash amount minus eligible collateral).",
            "Margin surplus equals max(0, eligible collateral minus cash amount).",
            "Securities lending borrow fee is an annualized decimal rate.",
            "Collateral required equals security market value multiplied by collateralization rate.",
            "Borrow fee amount equals security market value multiplied by borrow fee rate multiplied by days divided by day-count basis.",
            "Rebate amount equals collateral required multiplied by rebate rate multiplied by days divided by day-count basis.",
            "Simplified net lending revenue equals borrow fee amount minus rebate amount.",
            "Specialness classification is a heuristic based on borrow fee, utilization proxy, and manual special flag.",
            "This report is a simplified analytics proxy and does not model legal close-out, settlement timing, counterparty default, dividend events, recall risk, or full securities finance economics.",
        ]

        methodology_df = pd.DataFrame({"Methodology / Assumption": methodology_items})
        methodology_df.to_excel(
            writer,
            sheet_name="Methodology",
            index=False,
            startrow=2,
        )

        methodology_ws = writer.sheets["Methodology"]
        methodology_ws.write(0, 0, "Financing & Margin Report — Methodology", title_format)
        methodology_ws.set_row(2, None, header_format)
        methodology_ws.set_column(0, 0, 130, wrap_format)

    output.seek(0)
    return output.getvalue()

def generate_structured_products_report(
    terms_summary: dict[str, Any],
    custom_path_result: dict[str, Any],
    single_scenario_df: pd.DataFrame,
    basket_scenario_df: pd.DataFrame,
    monte_carlo_summary: dict[str, Any],
    monte_carlo_results_df: pd.DataFrame,
) -> bytes:
    """Generate a Structured Products Excel report.

    Sheets:
    1. Terms
    2. Custom_Path_Result
    3. Single_Scenarios
    4. Worst_Of_Basket
    5. Monte_Carlo_Summary
    6. MC_Distribution
    7. Methodology

    The report uses deterministic payoff logic and simplified Monte Carlo
    analytics. It is not bank-grade pricing and not investment advice.
    """

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#EAF3F8", "border": 1}
        )
        title_format = workbook.add_format({"bold": True, "font_size": 16})
        wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Terms",
            title="Structured Product Terms",
            data=terms_summary,
            commentary=[
                "Terms are represented as simplified deterministic payoff inputs.",
                "Barrier levels are stored as performance thresholds versus initial level.",
            ],
        )

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Custom_Path_Result",
            title="Custom Path Payoff Result",
            data=custom_path_result,
            commentary=[
                "Custom path result is calculated from the user-defined observation path.",
            ],
        )

        single_scenario_df.to_excel(
            writer,
            sheet_name="Single_Scenarios",
            index=False,
        )
        writer.sheets["Single_Scenarios"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Single_Scenarios", single_scenario_df)

        basket_scenario_df.to_excel(
            writer,
            sheet_name="Worst_Of_Basket",
            index=False,
        )
        writer.sheets["Worst_Of_Basket"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Worst_Of_Basket", basket_scenario_df)

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Monte_Carlo_Summary",
            title="Monte Carlo Proxy Summary",
            data=monte_carlo_summary,
            commentary=[
                "Monte Carlo output is a simplified GBM-based proxy.",
                "The output should be used for intuition, not calibrated pricing or fair value.",
            ],
        )

        mc_distribution_cols = [
            "autocalled",
            "autocall_observation",
            "final_performance",
            "total_coupons_paid",
            "redemption_amount",
            "capital_pnl",
            "total_payoff",
            "total_pnl",
            "payoff_return",
            "protection_barrier_breached",
        ]

        mc_distribution = monte_carlo_results_df[mc_distribution_cols].copy()
        mc_distribution.to_excel(
            writer,
            sheet_name="MC_Distribution",
            index=False,
        )
        writer.sheets["MC_Distribution"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "MC_Distribution", mc_distribution)

        methodology_items = [
            "Nominal is the invested notional.",
            "Performance values are measured versus initial level.",
            "Autocall barrier at 100% of initial corresponds to 0% performance threshold.",
            "Protection barrier at 60% of initial corresponds to -40% performance threshold.",
            "Worst-of basket payoff is driven by the weakest underlying at each observation.",
            "Athena logic is simplified as accumulated coupon paid if autocall occurs.",
            "Phoenix coupon is paid when coupon condition is met.",
            "Phoenix memory coupon recovers missed coupons if the coupon condition is later met.",
            "Capital loss applies if final performance is below the protection barrier.",
            "Monte Carlo uses simplified geometric Brownian motion paths.",
            "Worst-of Monte Carlo uses a constant-correlation proxy.",
            "This report is not bank-grade pricing, not fair value, not investment advice, and not a trading signal.",
        ]

        methodology_df = pd.DataFrame({"Methodology / Assumption": methodology_items})
        methodology_df.to_excel(
            writer,
            sheet_name="Methodology",
            index=False,
            startrow=2,
        )

        methodology_ws = writer.sheets["Methodology"]
        methodology_ws.write(0, 0, "Structured Products Report — Methodology", title_format)
        methodology_ws.set_row(2, None, header_format)
        methodology_ws.set_column(0, 0, 130, wrap_format)

    output.seek(0)
    return output.getvalue()

def generate_portfolio_risk_report(
    summary: dict[str, Any],
    weights_df: pd.DataFrame,
    risk_contribution_df: pd.DataFrame,
    correlation_matrix: pd.DataFrame,
    stress_df: pd.DataFrame,
    portfolio_returns_df: pd.DataFrame,
    drawdown_df: pd.DataFrame,
) -> bytes:
    """Generate a Portfolio Risk Excel report.

    Sheets:
    1. Portfolio_Summary
    2. Weights
    3. Risk_Contribution
    4. Correlation_Matrix
    5. Stress_Scenarios
    6. Portfolio_Returns
    7. Drawdown
    8. Methodology

    The report is a simplified analytics output and is not a production risk system.
    """

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#EAF3F8", "border": 1}
        )
        title_format = workbook.add_format({"bold": True, "font_size": 16})
        wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

        _write_key_value_sheet(
            writer=writer,
            sheet_name="Portfolio_Summary",
            title="Portfolio Risk Summary",
            data=summary,
            commentary=[
                "Portfolio risk metrics are calculated from historical/simple returns.",
                "VaR and CVaR are historical and reported as positive loss numbers.",
                "This is a simplified risk report, not a production risk system.",
            ],
        )

        weights_df.to_excel(writer, sheet_name="Weights", index=False)
        writer.sheets["Weights"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Weights", weights_df)

        risk_contribution_df.to_excel(writer, sheet_name="Risk_Contribution", index=False)
        writer.sheets["Risk_Contribution"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Risk_Contribution", risk_contribution_df)

        correlation_matrix.to_excel(writer, sheet_name="Correlation_Matrix", index=True)
        writer.sheets["Correlation_Matrix"].set_row(0, None, header_format)
        writer.sheets["Correlation_Matrix"].set_column(0, len(correlation_matrix.columns), 18)

        stress_df.to_excel(writer, sheet_name="Stress_Scenarios", index=False)
        writer.sheets["Stress_Scenarios"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Stress_Scenarios", stress_df)

        portfolio_returns_df.to_excel(writer, sheet_name="Portfolio_Returns", index=False)
        writer.sheets["Portfolio_Returns"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Portfolio_Returns", portfolio_returns_df)

        drawdown_df.to_excel(writer, sheet_name="Drawdown", index=False)
        writer.sheets["Drawdown"].set_row(0, None, header_format)
        _auto_adjust_columns(writer, "Drawdown", drawdown_df)

        methodology_items = [
            "Price data is converted into simple returns.",
            "Portfolio return is the weighted sum of asset returns.",
            "Weights are normalized before risk calculations.",
            "Annualized return equals average periodic return multiplied by periods per year.",
            "Annualized volatility equals periodic volatility multiplied by square root of periods per year.",
            "Sharpe ratio equals annualized excess return divided by annualized volatility.",
            "Historical VaR is reported as a positive loss number.",
            "Historical CVaR is the average tail loss beyond VaR.",
            "Max drawdown is calculated from the cumulative return index.",
            "Risk contribution uses covariance-based contribution to portfolio volatility.",
            "Stress scenarios are simplified generic shocks based on asset labels.",
            "This report does not model liquidity, transaction costs, slippage, factor risk, or intraday risk.",
            "This report is not investment advice, not a trading signal, and not a production risk system.",
        ]

        methodology_df = pd.DataFrame({"Methodology / Assumption": methodology_items})
        methodology_df.to_excel(
            writer,
            sheet_name="Methodology",
            index=False,
            startrow=2,
        )

        methodology_ws = writer.sheets["Methodology"]
        methodology_ws.write(0, 0, "Portfolio Risk Report — Methodology", title_format)
        methodology_ws.set_row(2, None, header_format)
        methodology_ws.set_column(0, 0, 130, wrap_format)

    output.seek(0)
    return output.getvalue()
