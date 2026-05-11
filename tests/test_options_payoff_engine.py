import pytest

from engines.options_payoff_engine import (
    DISCLAIMER,
    SUPPORTED_STRATEGIES,
    build_options_strategy_snapshot,
    build_price_grid,
    build_strategy_legs,
    estimate_breakevens,
    normalize_strategy_name,
    option_leg_pnl,
)


def test_supported_strategy_normalization():
    assert normalize_strategy_name(" long call ") == "Long Call"
    assert "Bull Call Spread" in SUPPORTED_STRATEGIES


def test_build_price_grid_around_spot():
    grid = build_price_grid(spot=100, lower_pct=0.8, upper_pct=1.2, points=5)

    assert list(grid) == [80.0, 90.0, 100.0, 110.0, 120.0]


def test_long_call_snapshot_has_expected_breakeven_and_risk_profile():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.8,
        upper_pct=1.2,
        points=41,
    )

    assert snapshot["strategy"] == "Long Call"
    assert snapshot["risk_profile"]["max_gain"] == "Unlimited"
    assert snapshot["risk_profile"]["max_loss"] == 5
    assert 105.0 in snapshot["breakevens"]
    assert DISCLAIMER in snapshot["disclaimer"]


def test_long_put_snapshot_has_expected_breakeven():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Put",
        spot=100,
        strike=100,
        premium=4,
        lower_pct=0.8,
        upper_pct=1.2,
        points=41,
    )

    assert snapshot["risk_profile"]["max_loss"] == 4
    assert 96.0 in snapshot["breakevens"]


def test_bull_call_spread_has_capped_gain_and_loss():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Bull Call Spread",
        spot=100,
        strike=100,
        premium=6,
        strike_2=110,
        premium_2=2,
        lower_pct=0.8,
        upper_pct=1.2,
        points=41,
    )

    assert snapshot["risk_profile"]["max_gain"] == 6
    assert snapshot["risk_profile"]["max_loss"] == 4
    assert 104.0 in snapshot["breakevens"]
    assert len(snapshot["legs"]) == 2


def test_covered_call_includes_underlying_and_short_call():
    legs = build_strategy_legs(
        strategy_name="Covered Call",
        spot=100,
        strike=110,
        premium=3,
    )

    assert [leg.instrument for leg in legs] == ["underlying", "call"]
    assert [leg.position for leg in legs] == ["long", "short"]


def test_long_straddle_has_two_breakevens():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Straddle",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.8,
        upper_pct=1.2,
        points=81,
    )

    assert 90.0 in snapshot["breakevens"]
    assert 110.0 in snapshot["breakevens"]
    assert snapshot["risk_profile"]["max_loss"] == 10


def test_estimate_breakevens_handles_no_crossing():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Short Put",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=1.1,
        upper_pct=1.3,
        points=11,
    )

    breakevens = estimate_breakevens(snapshot["payoff_table"])

    assert breakevens == []


def test_invalid_strategy_raises():
    with pytest.raises(ValueError):
        normalize_strategy_name("Random Strategy")


def test_option_leg_pnl_uses_premium_cashflow():
    leg = build_strategy_legs("Long Call", spot=100, strike=100, premium=5)[0]

    pnl = option_leg_pnl([90, 100, 110], leg)

    assert list(pnl) == [-5.0, -5.0, 5.0]


def test_scenario_table_is_included():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
    )

    scenario_df = snapshot["scenario_table"]

    assert list(scenario_df.columns) == ["scenario", "underlying_price", "payoff", "pnl"]
    assert "+0%" in list(scenario_df["scenario"])
