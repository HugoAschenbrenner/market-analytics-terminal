from datetime import date

import pandas as pd

from engines.fixed_income_engine import (
    calculate_bond_risk_metrics,
    calculate_dv01,
    calculate_market_value,
    estimate_pnl_from_yield_move,
    load_bond_data,
    summarize_portfolio,
)


VALUATION_DATE = date(2026, 5, 6)


def test_sample_bond_data_loads_successfully():
    df = load_bond_data("data/sample_bonds.csv")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 12


def test_dirty_price_equals_clean_price_plus_accrued_interest():
    bonds = load_bond_data("data/sample_bonds.csv")
    risk_df = calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)

    first_row = risk_df.iloc[0]
    expected_dirty_price = (
        first_row["clean_price"] + first_row["accrued_interest_per_100"]
    )

    assert abs(first_row["dirty_price"] - expected_dirty_price) < 1e-9


def test_market_value_formula_uses_clean_price_per_100():
    market_value = calculate_market_value(clean_price=98.5, notional=1_000_000)

    assert market_value == 985_000


def test_dv01_is_positive_under_project_convention():
    dv01 = calculate_dv01(modified_duration=5.0, market_value=1_000_000)

    assert dv01 > 0
    assert dv01 == 500.0


def test_positive_yield_move_creates_negative_pnl():
    pnl = estimate_pnl_from_yield_move(dv01=10_000, yield_move_bps=25)

    assert pnl == -250_000


def test_negative_yield_move_creates_positive_pnl():
    pnl = estimate_pnl_from_yield_move(dv01=10_000, yield_move_bps=-25)

    assert pnl == 250_000


def test_portfolio_dv01_equals_sum_of_bond_dv01s():
    bonds = load_bond_data("data/sample_bonds.csv")
    risk_df = calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)
    summary = summarize_portfolio(risk_df)

    assert abs(summary.total_dv01 - risk_df["dv01"].sum()) < 1e-6


def test_weighted_average_duration_is_between_min_and_max_duration():
    bonds = load_bond_data("data/sample_bonds.csv")
    risk_df = calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)
    summary = summarize_portfolio(risk_df)

    min_duration = risk_df["modified_duration"].min()
    max_duration = risk_df["modified_duration"].max()

    assert min_duration <= summary.weighted_average_modified_duration <= max_duration


def test_total_market_value_is_positive():
    bonds = load_bond_data("data/sample_bonds.csv")
    risk_df = calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)
    summary = summarize_portfolio(risk_df)

    assert summary.total_market_value > 0


def test_all_bond_dv01_values_are_non_negative():
    bonds = load_bond_data("data/sample_bonds.csv")
    risk_df = calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)

    assert (risk_df["dv01"] >= 0).all()
