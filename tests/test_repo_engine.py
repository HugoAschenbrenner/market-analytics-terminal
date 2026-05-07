from datetime import date

import pandas as pd
import pytest

from engines.repo_engine import (
    calculate_adjusted_collateral_value,
    calculate_cash_amount,
    calculate_eligible_collateral,
    calculate_margin_call,
    calculate_margin_stress_table,
    calculate_repurchase_amount,
    calculate_repo_days,
    calculate_repo_interest,
    calculate_repo_sensitivity_table,
    calculate_repo_trade,
    generate_repo_margin_commentary,
    identify_margin_driver,
    margin_result_to_dict,
    repo_result_to_dict,
)


START_DATE = date(2026, 5, 6)
END_DATE = date(2026, 6, 5)


def test_repo_days_calculation():
    days = calculate_repo_days(START_DATE, END_DATE)

    assert days == 30


def test_end_date_must_be_after_start_date():
    with pytest.raises(ValueError):
        calculate_repo_days(END_DATE, START_DATE)


def test_cash_amount_decreases_when_haircut_increases():
    collateral_value = 10_000_000

    cash_low_haircut = calculate_cash_amount(
        collateral_market_value=collateral_value,
        haircut=0.02,
    )
    cash_high_haircut = calculate_cash_amount(
        collateral_market_value=collateral_value,
        haircut=0.05,
    )

    assert cash_high_haircut < cash_low_haircut


def test_cash_amount_formula():
    cash_amount = calculate_cash_amount(
        collateral_market_value=10_000_000,
        haircut=0.02,
    )

    assert cash_amount == 9_800_000


def test_repo_interest_increases_when_repo_rate_increases():
    cash_amount = 10_000_000
    days = 30

    interest_low_rate = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=0.02,
        repo_days=days,
        day_count_basis=360,
    )
    interest_high_rate = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=0.04,
        repo_days=days,
        day_count_basis=360,
    )

    assert interest_high_rate > interest_low_rate


def test_repo_interest_increases_with_longer_maturity():
    cash_amount = 10_000_000
    repo_rate = 0.04

    interest_30_days = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=repo_rate,
        repo_days=30,
        day_count_basis=360,
    )
    interest_60_days = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=repo_rate,
        repo_days=60,
        day_count_basis=360,
    )

    assert interest_60_days > interest_30_days


def test_repurchase_amount_equals_cash_plus_interest():
    repurchase_amount = calculate_repurchase_amount(
        cash_amount=9_800_000,
        repo_interest=32_666.67,
    )

    assert abs(repurchase_amount - 9_832_666.67) < 1e-6


def test_calculate_repo_trade_outputs_consistent_cashflows():
    result = calculate_repo_trade(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=START_DATE,
        end_date=END_DATE,
        day_count_basis=360,
        currency="EUR",
    )

    assert result.cash_amount == 9_800_000
    assert result.repo_days == 30
    assert abs(result.repo_interest - 32_666.666666666664) < 1e-6
    assert abs(result.repurchase_amount - 9_832_666.666666666) < 1e-6


def test_repo_result_to_dict_converts_dates_to_iso_strings():
    result = calculate_repo_trade(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=START_DATE,
        end_date=END_DATE,
        day_count_basis=360,
        currency="EUR",
    )

    result_dict = repo_result_to_dict(result)

    assert result_dict["start_date"] == "2026-05-06"
    assert result_dict["end_date"] == "2026-06-05"


def test_invalid_haircut_raises_error():
    with pytest.raises(ValueError):
        calculate_repo_trade(
            collateral_market_value=10_000_000,
            haircut=1.20,
            repo_rate=0.04,
            start_date=START_DATE,
            end_date=END_DATE,
        )


def test_sensitivity_table_returns_dataframe():
    sensitivity_df = calculate_repo_sensitivity_table(
        collateral_market_value=10_000_000,
        haircut=0.02,
        repo_rate=0.04,
        start_date=START_DATE,
        end_date=END_DATE,
        day_count_basis=360,
        currency="EUR",
    )

    assert isinstance(sensitivity_df, pd.DataFrame)
    assert len(sensitivity_df) == 5
    assert "cash_amount" in sensitivity_df.columns
    assert "repurchase_amount" in sensitivity_df.columns


def test_adjusted_collateral_value_after_price_drop():
    adjusted_value = calculate_adjusted_collateral_value(
        collateral_market_value=10_000_000,
        collateral_price_shock=-0.05,
    )

    assert adjusted_value == 9_500_000


def test_eligible_collateral_formula():
    eligible = calculate_eligible_collateral(
        collateral_market_value=10_000_000,
        haircut=0.02,
    )

    assert eligible == 9_800_000


def test_no_shock_same_haircut_creates_no_artificial_deficit():
    collateral_value = 10_000_000
    haircut = 0.02
    cash_amount = calculate_cash_amount(collateral_value, haircut)

    result = calculate_margin_call(
        collateral_market_value=collateral_value,
        cash_amount=cash_amount,
        original_haircut=haircut,
        collateral_price_shock=0.0,
        new_haircut=haircut,
    )

    assert result.margin_deficit == 0.0
    assert result.margin_surplus == 0.0
    assert result.margin_call_required is False


def test_collateral_price_drop_increases_or_maintains_margin_deficit():
    collateral_value = 10_000_000
    haircut = 0.02
    cash_amount = calculate_cash_amount(collateral_value, haircut)

    base_result = calculate_margin_call(
        collateral_market_value=collateral_value,
        cash_amount=cash_amount,
        original_haircut=haircut,
        collateral_price_shock=0.0,
        new_haircut=haircut,
    )

    shocked_result = calculate_margin_call(
        collateral_market_value=collateral_value,
        cash_amount=cash_amount,
        original_haircut=haircut,
        collateral_price_shock=-0.05,
        new_haircut=haircut,
    )

    assert shocked_result.margin_deficit >= base_result.margin_deficit


def test_haircut_increase_increases_or_maintains_margin_deficit():
    collateral_value = 10_000_000
    haircut = 0.02
    cash_amount = calculate_cash_amount(collateral_value, haircut)

    base_result = calculate_margin_call(
        collateral_market_value=collateral_value,
        cash_amount=cash_amount,
        original_haircut=haircut,
        collateral_price_shock=0.0,
        new_haircut=haircut,
    )

    shocked_result = calculate_margin_call(
        collateral_market_value=collateral_value,
        cash_amount=cash_amount,
        original_haircut=haircut,
        collateral_price_shock=0.0,
        new_haircut=0.05,
    )

    assert shocked_result.margin_deficit >= base_result.margin_deficit


def test_margin_deficit_cannot_be_negative():
    result = calculate_margin_call(
        collateral_market_value=10_000_000,
        cash_amount=9_800_000,
        original_haircut=0.02,
        collateral_price_shock=0.05,
        new_haircut=0.02,
    )

    assert result.margin_deficit >= 0
    assert result.margin_surplus >= 0


def test_margin_call_required_under_adverse_combined_shock():
    result = calculate_margin_call(
        collateral_market_value=10_000_000,
        cash_amount=9_800_000,
        original_haircut=0.02,
        collateral_price_shock=-0.10,
        new_haircut=0.07,
    )

    assert result.margin_call_required is True
    assert result.margin_deficit > 0


def test_margin_result_to_dict_returns_dictionary():
    result = calculate_margin_call(
        collateral_market_value=10_000_000,
        cash_amount=9_800_000,
        original_haircut=0.02,
        collateral_price_shock=-0.05,
        new_haircut=0.04,
    )

    result_dict = margin_result_to_dict(result)

    assert isinstance(result_dict, dict)
    assert "margin_deficit" in result_dict
    assert "margin_call_required" in result_dict


def test_margin_stress_table_returns_dataframe():
    stress_df = calculate_margin_stress_table(
        collateral_market_value=10_000_000,
        cash_amount=9_800_000,
        original_haircut=0.02,
    )

    assert isinstance(stress_df, pd.DataFrame)
    assert len(stress_df) == 5
    assert "margin_deficit" in stress_df.columns
    assert "margin_call_required" in stress_df.columns


def test_identify_margin_driver_combined_shock():
    driver = identify_margin_driver(
        collateral_price_shock=-0.05,
        original_haircut=0.02,
        new_haircut=0.04,
    )

    assert driver == "Collateral depreciation and haircut increase"


def test_margin_commentary_returns_non_empty_list():
    result = calculate_margin_call(
        collateral_market_value=10_000_000,
        cash_amount=9_800_000,
        original_haircut=0.02,
        collateral_price_shock=-0.05,
        new_haircut=0.04,
    )

    commentary = generate_repo_margin_commentary(result)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
