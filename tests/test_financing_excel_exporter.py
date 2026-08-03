from io import BytesIO
from datetime import date

from openpyxl import load_workbook

from engines.repo_engine import (
    calculate_contractual_variation_margin,
    calculate_refinancing_stress_table,
    calculate_repo_sensitivity_table,
    calculate_repo_trade,
    contractual_margin_result_to_dict,
    generate_contractual_margin_commentary,
    repo_result_to_dict,
)
from engines.sec_lending_engine import (
    calculate_borrow_fee_comparison_table,
    calculate_securities_lending_trade,
    generate_sec_lending_commentary,
    sec_lending_result_to_dict,
)
from reports.excel_exporter import generate_financing_margin_report


def test_financing_margin_excel_report_generates_valid_workbook():
    repo_result = calculate_repo_trade(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=date(2026, 5, 6),
        end_date=date(2026, 6, 5),
        day_count_basis=360,
        currency="EUR",
    )

    repo_sensitivity_df = calculate_repo_sensitivity_table(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=date(2026, 5, 6),
        end_date=date(2026, 6, 5),
        day_count_basis=360,
        currency="EUR",
    )

    margin_result = calculate_contractual_variation_margin(
        cash_amount=repo_result.cash_amount,
        repo_rate=repo_result.repo_rate,
        start_date=repo_result.start_date,
        end_date=repo_result.end_date,
        margin_date=date(2026, 5, 21),
        day_count_basis=repo_result.day_count_basis,
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=repo_result.haircut,
        transaction_direction="Cash lender / reverse repo",
        threshold=0.0,
        minimum_transfer_amount=0.0,
        rounding_increment=1.0,
        rounding_method="Nearest",
        currency="EUR",
        netting_set_id="NS-TEST",
    )

    margin_stress_df = calculate_refinancing_stress_table(
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=repo_result.haircut,
        currency="EUR",
    )
    repo_commentary = generate_contractual_margin_commentary(margin_result)

    sec_result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.65,
        is_special=False,
        agent_fee_share=0.0,
        other_costs=0.0,
    )

    borrow_comparison_df = calculate_borrow_fee_comparison_table(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        agent_fee_share=0.0,
        other_costs=0.0,
        utilization_proxy=0.65,
    )

    sec_commentary = generate_sec_lending_commentary(sec_result)

    report_bytes = generate_financing_margin_report(
        repo_summary=repo_result_to_dict(repo_result),
        repo_sensitivity_df=repo_sensitivity_df,
        margin_summary=contractual_margin_result_to_dict(margin_result),
        margin_stress_df=margin_stress_df,
        repo_commentary=repo_commentary,
        sec_lending_summary=sec_lending_result_to_dict(sec_result),
        borrow_comparison_df=borrow_comparison_df,
        sec_lending_commentary=sec_commentary,
    )

    assert isinstance(report_bytes, bytes)
    assert len(report_bytes) > 0

    workbook = load_workbook(BytesIO(report_bytes), read_only=True)

    expected_sheets = {
        "Repo_Summary",
        "Repo_Sensitivity",
        "Contractual_VM",
        "Refinancing_Stress",
        "Sec_Lending_Summary",
        "Borrow_Comparison",
        "Methodology",
    }

    assert expected_sheets.issubset(set(workbook.sheetnames))
