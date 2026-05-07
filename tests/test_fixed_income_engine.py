from datetime import date

import pandas as pd

from engines.fixed_income_engine import (
    calculate_bond_risk_metrics,
    calculate_dv01,
    calculate_dv01_by_bucket,
    calculate_hedge_units,
    calculate_market_value,
    calculate_scenario_pnl,
    estimate_pnl_from_yield_move,
    estimate_pnl_with_duration_convexity,
    generate_fixed_income_commentary,
    identify_worst_scenario,
    load_bond_data,
    summarize_portfolio,
)


VALUATION_DATE = date(2026, 5, 6)


def _risk_df():
    bonds = load_bond_data("data/sample_bonds.csv")
    return calculate_bond_risk_metrics(bonds, valuation_date=VALUATION_DATE)


def test_sample_bond_data_loads_successfully():
    df = load_bond_data("data/sample_bonds.csv")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 12


def test_dirty_price_equals_clean_price_plus_accrued_interest():
    risk_df = _risk_df()

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


def test_duration_convexity_pnl_is_negative_for_positive_shock():
    pnl_components = estimate_pnl_with_duration_convexity(
        modified_duration=5.0,
        convexity=30.0,
        market_value=1_000_000,
        yield_move_bps=25,
    )

    assert pnl_components["estimated_pnl"] < 0
    assert pnl_components["duration_pnl"] < 0
    assert pnl_components["convexity_pnl"] > 0


def test_portfolio_dv01_equals_sum_of_bond_dv01s():
    risk_df = _risk_df()
    summary = summarize_portfolio(risk_df)

    assert abs(summary.total_dv01 - risk_df["dv01"].sum()) < 1e-6


def test_weighted_average_duration_is_between_min_and_max_duration():
    risk_df = _risk_df()
    summary = summarize_portfolio(risk_df)

    min_duration = risk_df["modified_duration"].min()
    max_duration = risk_df["modified_duration"].max()

    assert min_duration <= summary.weighted_average_modified_duration <= max_duration


def test_total_market_value_is_positive():
    risk_df = _risk_df()
    summary = summarize_portfolio(risk_df)

    assert summary.total_market_value > 0


def test_all_bond_dv01_values_are_non_negative():
    risk_df = _risk_df()

    assert (risk_df["dv01"] >= 0).all()


def test_bucket_dv01_sums_to_total_dv01():
    risk_df = _risk_df()
    bucket_df = calculate_dv01_by_bucket(risk_df)

    assert abs(bucket_df["dv01"].sum() - risk_df["dv01"].sum()) < 1e-6


def test_bucket_percentages_sum_to_one():
    risk_df = _risk_df()
    bucket_df = calculate_dv01_by_bucket(risk_df)

    assert abs(bucket_df["pct_total_dv01"].sum() - 1.0) < 1e-9


def test_positive_parallel_shock_creates_negative_scenario_pnl():
    risk_df = _risk_df()
    scenario_df = calculate_scenario_pnl(risk_df)

    shock_25 = scenario_df.loc[
        scenario_df["scenario_name"] == "+25 bps parallel", "estimated_pnl"
    ].iloc[0]

    assert shock_25 < 0


def test_50_bps_loss_is_larger_than_25_bps_loss():
    risk_df = _risk_df()
    scenario_df = calculate_scenario_pnl(risk_df)

    shock_25 = scenario_df.loc[
        scenario_df["scenario_name"] == "+25 bps parallel", "estimated_pnl"
    ].iloc[0]

    shock_50 = scenario_df.loc[
        scenario_df["scenario_name"] == "+50 bps parallel", "estimated_pnl"
    ].iloc[0]

    assert shock_50 < shock_25


def test_negative_parallel_shock_creates_positive_scenario_pnl():
    risk_df = _risk_df()
    scenario_df = calculate_scenario_pnl(risk_df)

    shock_minus_25 = scenario_df.loc[
        scenario_df["scenario_name"] == "-25 bps parallel", "estimated_pnl"
    ].iloc[0]

    assert shock_minus_25 > 0


def test_identify_worst_scenario_returns_loss_scenario():
    risk_df = _risk_df()
    scenario_df = calculate_scenario_pnl(risk_df)
    worst = identify_worst_scenario(scenario_df)

    assert worst["estimated_pnl"] == scenario_df["estimated_pnl"].min()


def test_hedge_units_calculation():
    hedge_units = calculate_hedge_units(
        portfolio_dv01=48_000,
        hedge_instrument_dv01=75,
    )

    assert hedge_units == 640


def test_commentary_returns_non_empty_list():
    risk_df = _risk_df()
    bucket_df = calculate_dv01_by_bucket(risk_df)
    scenario_df = calculate_scenario_pnl(risk_df)

    commentary = generate_fixed_income_commentary(risk_df, bucket_df, scenario_df)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
