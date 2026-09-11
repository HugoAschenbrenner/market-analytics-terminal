from datetime import date
from pathlib import Path

import pytest

from engines.repo_engine import (
    calculate_accrued_repurchase_price,
    calculate_contractual_variation_margin,
    calculate_refinancing_haircut_stress,
    calculate_refinancing_stress_table,
    calculate_repo_trade,
)


START = date(2026, 5, 6)
END = date(2026, 6, 5)
MARGIN = date(2026, 5, 21)


def _trade():
    return calculate_repo_trade(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=START,
        end_date=END,
        day_count_basis=360,
        currency="EUR",
    )


def test_accrued_repurchase_price_uses_margin_date():
    trade = _trade()
    days, interest, accrued_price = calculate_accrued_repurchase_price(
        cash_amount=trade.cash_amount,
        repo_rate=trade.repo_rate,
        start_date=trade.start_date,
        margin_date=MARGIN,
        day_count_basis=trade.day_count_basis,
        end_date=trade.end_date,
    )
    assert days == 15
    assert interest == pytest.approx(16_333.333333333332)
    assert accrued_price == pytest.approx(9_816_333.333333334)


def test_contractual_margin_uses_accrued_price_and_dirty_collateral():
    trade = _trade()
    result = calculate_contractual_variation_margin(
        cash_amount=trade.cash_amount,
        repo_rate=trade.repo_rate,
        start_date=trade.start_date,
        end_date=trade.end_date,
        margin_date=MARGIN,
        day_count_basis=trade.day_count_basis,
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=trade.haircut,
        transaction_direction="Cash lender / reverse repo",
        rounding_increment=0.0,
        rounding_method="None",
    )
    expected_eligible = 9_500_000 * 0.98
    expected_gap = result.accrued_repurchase_price - expected_eligible
    assert result.current_eligible_collateral == pytest.approx(expected_eligible)
    assert result.cash_lender_exposure_gap == pytest.approx(expected_gap)
    assert result.contractual_margin_transfer == pytest.approx(expected_gap)


def test_contractual_haircut_is_fixed_and_never_reset():
    trade = _trade()
    result = calculate_contractual_variation_margin(
        cash_amount=trade.cash_amount,
        repo_rate=trade.repo_rate,
        start_date=trade.start_date,
        end_date=trade.end_date,
        margin_date=MARGIN,
        day_count_basis=trade.day_count_basis,
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=0.02,
        transaction_direction="Cash lender / reverse repo",
    )
    assert result.contractual_haircut == pytest.approx(0.02)
    assert result.contractual_haircut_reset_applied is False


def test_refinancing_haircut_reset_is_separate_190k_liquidity_stress():
    result = calculate_refinancing_haircut_stress(
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=0.02,
        refinancing_haircut=0.04,
        collateral_price_shock=0.0,
        currency="EUR",
    )
    assert result.current_funding_capacity == pytest.approx(9_310_000)
    assert result.stressed_refinancing_funding_capacity == pytest.approx(9_120_000)
    assert result.haircut_reset_liquidity_change == pytest.approx(-190_000)
    assert result.refinancing_liquidity_shortfall == pytest.approx(190_000)
    assert result.is_contractual_variation_margin is False


def test_threshold_and_mta_can_suppress_transfer():
    trade = _trade()
    result = calculate_contractual_variation_margin(
        cash_amount=trade.cash_amount,
        repo_rate=trade.repo_rate,
        start_date=trade.start_date,
        end_date=trade.end_date,
        margin_date=MARGIN,
        day_count_basis=trade.day_count_basis,
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=trade.haircut,
        transaction_direction="Cash lender / reverse repo",
        threshold=500_000,
        minimum_transfer_amount=10_000,
        rounding_increment=1.0,
    )
    assert abs(result.threshold_adjusted_gap) < 10_000
    assert result.contractual_margin_transfer == 0.0
    assert result.margin_transfer_required is False


def test_margin_rounding_is_explicit():
    trade = _trade()
    target_gap = 10_450.0
    eligible_target = trade.cash_amount - target_gap
    dirty_value = eligible_target / 0.98
    result = calculate_contractual_variation_margin(
        cash_amount=trade.cash_amount,
        repo_rate=0.0,
        start_date=trade.start_date,
        end_date=trade.end_date,
        margin_date=trade.start_date,
        day_count_basis=trade.day_count_basis,
        current_dirty_collateral_value=dirty_value,
        contractual_haircut=trade.haircut,
        transaction_direction="Cash lender / reverse repo",
        rounding_increment=1_000.0,
        rounding_method="Nearest",
    )
    assert result.cash_lender_exposure_gap == pytest.approx(target_gap)
    assert result.contractual_margin_transfer == pytest.approx(10_000.0)


def test_margin_date_outside_trade_is_rejected():
    trade = _trade()
    with pytest.raises(ValueError, match="after repo end date"):
        calculate_contractual_variation_margin(
            cash_amount=trade.cash_amount,
            repo_rate=trade.repo_rate,
            start_date=trade.start_date,
            end_date=trade.end_date,
            margin_date=date(2026, 6, 6),
            day_count_basis=trade.day_count_basis,
            current_dirty_collateral_value=10_000_000,
            contractual_haircut=trade.haircut,
            transaction_direction="Cash lender / reverse repo",
        )


def test_repo_direction_changes_transfer_label_not_exposure_gap():
    trade = _trade()
    common = dict(
        cash_amount=trade.cash_amount,
        repo_rate=trade.repo_rate,
        start_date=trade.start_date,
        end_date=trade.end_date,
        margin_date=MARGIN,
        day_count_basis=trade.day_count_basis,
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=trade.haircut,
    )
    lender = calculate_contractual_variation_margin(
        **common,
        transaction_direction="Cash lender / reverse repo",
    )
    borrower = calculate_contractual_variation_margin(
        **common,
        transaction_direction="Cash borrower / repo",
    )
    assert lender.cash_lender_exposure_gap == pytest.approx(
        borrower.cash_lender_exposure_gap
    )
    assert "receives" in lender.transfer_direction
    assert "posts" in borrower.transfer_direction


def test_refinancing_stress_table_never_labels_liquidity_as_vm():
    table = calculate_refinancing_stress_table(
        current_dirty_collateral_value=9_500_000,
        contractual_haircut=0.02,
        currency="EUR",
    )
    assert len(table) == 5
    assert (table["is_contractual_variation_margin"] == False).all()
    assert {
        "haircut_reset_liquidity_change",
        "refinancing_liquidity_shortfall",
        "stressed_refinancing_funding_capacity",
    }.issubset(table.columns)


def test_ui_and_excel_separate_contractual_vm_from_refinancing():
    report = Path("reports/excel_exporter.py").read_text()
    assert "Contractual_VM" in report
    assert "Refinancing_Stress" in report
    assert "excluded from contractual variation margin" in report
