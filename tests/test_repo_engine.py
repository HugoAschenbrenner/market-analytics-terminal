from datetime import date

import pandas as pd
import pytest

from engines.repo_engine import (
    calculate_cash_amount,
    calculate_repurchase_amount,
    calculate_repo_days,
    calculate_repo_interest,
    calculate_repo_sensitivity_table,
    calculate_repo_trade,
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
