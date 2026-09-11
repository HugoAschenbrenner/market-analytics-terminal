from dataclasses import replace
from pathlib import Path

import pytest

from engines.cross_asset_dashboard_engine import (
    build_default_cross_asset_inputs,
    calculate_cross_asset_stress_table,
    calculate_cross_asset_summary,
)


def _scenario_row(stress_df, scenario: str):
    return stress_df.loc[
        stress_df["scenario"] == scenario
    ].iloc[0]


def test_default_rates_scenario_reconciles_to_common_nav():
    inputs = build_default_cross_asset_inputs()
    stress_df = calculate_cross_asset_stress_table(inputs)
    row = _scenario_row(
        stress_df,
        "Parallel rates +100bp / funding pressure",
    )

    assert row["rates_pnl_amount"] == pytest.approx(-2_440_300.0)
    assert row["structured_products_pnl_amount"] == pytest.approx(-600_000.0)
    assert row["residual_portfolio_pnl_amount"] == pytest.approx(-725_000.0)
    assert row["economic_pnl_amount"] == pytest.approx(-3_765_300.0)
    assert row["economic_pnl_pct_nav"] == pytest.approx(-0.037653)


def test_financing_liquidity_is_not_included_in_economic_pnl():
    inputs = build_default_cross_asset_inputs()
    stress_df = calculate_cross_asset_stress_table(inputs)
    row = _scenario_row(
        stress_df,
        "Parallel rates +100bp / funding pressure",
    )

    component_sum = (
        row["rates_pnl_amount"]
        + row["structured_products_pnl_amount"]
        + row["residual_portfolio_pnl_amount"]
    )

    assert row["economic_pnl_amount"] == pytest.approx(component_sum)
    assert row["incremental_financing_liquidity_change_amount"] == pytest.approx(
        100_000.0
    )
    assert row["stressed_financing_liquidity_requirement_amount"] == pytest.approx(
        425_000.0
    )
    assert row["economic_pnl_amount"] != pytest.approx(
        component_sum - 100_000.0
    )


def test_collateral_value_changes_liquidity_not_economic_pnl():
    base = build_default_cross_asset_inputs()
    doubled_collateral = replace(
        base,
        collateral_market_value=20_000_000.0,
    )

    base_row = _scenario_row(
        calculate_cross_asset_stress_table(base),
        "Parallel rates +100bp / funding pressure",
    )
    doubled_row = _scenario_row(
        calculate_cross_asset_stress_table(doubled_collateral),
        "Parallel rates +100bp / funding pressure",
    )

    assert doubled_row["economic_pnl_amount"] == pytest.approx(
        base_row["economic_pnl_amount"]
    )
    assert doubled_row[
        "incremental_financing_liquidity_change_amount"
    ] == pytest.approx(
        2.0 * base_row["incremental_financing_liquidity_change_amount"]
    )


def test_nav_changes_percentage_not_economic_amount():
    base = build_default_cross_asset_inputs()
    larger_nav = replace(base, portfolio_nav=200_000_000.0)

    base_row = _scenario_row(
        calculate_cross_asset_stress_table(base),
        "Parallel rates +100bp / funding pressure",
    )
    larger_row = _scenario_row(
        calculate_cross_asset_stress_table(larger_nav),
        "Parallel rates +100bp / funding pressure",
    )

    assert larger_row["economic_pnl_amount"] == pytest.approx(
        base_row["economic_pnl_amount"]
    )
    assert larger_row["economic_pnl_pct_nav"] == pytest.approx(
        0.5 * base_row["economic_pnl_pct_nav"]
    )


def test_overlapping_sleeves_above_nav_are_rejected():
    invalid = replace(
        build_default_cross_asset_inputs(),
        residual_portfolio_notional=60_000_000.0,
    )

    with pytest.raises(
        ValueError,
        match="cannot exceed portfolio NAV",
    ):
        calculate_cross_asset_summary(invalid)


def test_stress_table_carries_one_explicit_base_currency():
    inputs = replace(
        build_default_cross_asset_inputs(),
        base_currency="USD",
    )
    stress_df = calculate_cross_asset_stress_table(inputs)

    assert set(stress_df["base_currency"]) == {"USD"}


def test_old_dimensionally_invalid_columns_are_removed():
    stress_df = calculate_cross_asset_stress_table(
        build_default_cross_asset_inputs()
    )

    assert "financing_impact_amount" not in stress_df.columns
    assert "total_proxy_impact_pct" not in stress_df.columns
    assert "economic_pnl_amount" in stress_df.columns
    assert "economic_pnl_pct_nav" in stress_df.columns
