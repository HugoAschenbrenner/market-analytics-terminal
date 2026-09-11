from pathlib import Path

import pytest

from engines.sec_lending_engine import (
    calculate_securities_lending_trade,
)


def test_default_audit_examples_are_separate_paths():
    non_cash = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
    )

    cash = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0,
        rebate_rate=0.005,
        reinvestment_yield=0.04,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
    )

    assert non_cash.net_lending_revenue == pytest.approx(
        5_208.333333333333
    )
    assert cash.net_lending_revenue == pytest.approx(
        14_875.0
    )
    assert non_cash.rebate_amount == 0.0
    assert cash.borrow_fee_amount == 0.0






def test_engine_and_report_remove_hybrid_formula():
    engine = Path(
        "engines/sec_lending_engine.py"
    ).read_text()
    report = Path(
        "reports/excel_exporter.py"
    ).read_text()

    forbidden = (
        "Simplified net lending revenue equals "
        "borrow fee amount minus rebate amount."
    )

    assert forbidden not in report
    assert (
        "net_lending_revenue = "
        "borrow_fee_amount - rebate_amount"
        not in engine
    )

    assert (
        "Non-cash collateral uses only the securities loan fee"
        in report
    )
    assert (
        "Cash collateral uses reinvestment income less the rebate"
        in report
    )
