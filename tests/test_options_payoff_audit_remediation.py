from pathlib import Path

import pytest

from engines.options_payoff_engine import (
    build_options_strategy_snapshot,
    build_scenario_table,
    build_strategy_legs,
)


def _scenario_row(snapshot: dict, scenario: str):
    table = snapshot["scenario_table"]
    row = table.loc[table["scenario"] == scenario]

    assert len(row) == 1

    return row.iloc[0]


def test_long_call_scenarios_are_independent_of_chart_range():
    narrow = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.5,
        upper_pct=1.0,
        points=51,
    )

    wide = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.5,
        upper_pct=2.0,
        points=151,
    )

    narrow_up_20 = _scenario_row(narrow, "+20%")
    wide_up_20 = _scenario_row(wide, "+20%")

    assert narrow_up_20["underlying_price"] == pytest.approx(120.0)
    assert narrow_up_20["payoff"] == pytest.approx(20.0)
    assert narrow_up_20["pnl"] == pytest.approx(15.0)

    assert narrow_up_20["payoff"] == pytest.approx(
        wide_up_20["payoff"]
    )
    assert narrow_up_20["pnl"] == pytest.approx(
        wide_up_20["pnl"]
    )


def test_long_call_breakeven_is_independent_of_display_range():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.5,
        upper_pct=1.0,
        points=51,
    )

    assert (
        snapshot["payoff_table"]["underlying_price"].max()
        == pytest.approx(100.0)
    )
    assert snapshot["breakevens"] == [105.0]


def test_short_put_breakeven_is_found_below_display_range():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Short Put",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=1.1,
        upper_pct=1.3,
        points=21,
    )

    assert snapshot["breakevens"] == [95.0]


def test_long_straddle_accepts_separate_premiums():
    legs = build_strategy_legs(
        strategy_name="Long Straddle",
        spot=100,
        strike=100,
        premium=6,
        premium_2=4,
    )

    assert [leg.instrument for leg in legs] == ["call", "put"]
    assert [leg.premium for leg in legs] == [6.0, 4.0]

    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Straddle",
        spot=100,
        strike=100,
        premium=6,
        premium_2=4,
        lower_pct=0.5,
        upper_pct=1.5,
        points=101,
    )

    assert snapshot["breakevens"] == [90.0, 110.0]
    assert snapshot["risk_profile"]["max_loss"] == pytest.approx(10.0)


def test_net_credit_spread_never_reports_negative_max_loss():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Bull Call Spread",
        spot=100,
        strike=100,
        premium=2,
        strike_2=110,
        premium_2=4,
        lower_pct=0.5,
        upper_pct=1.5,
        points=101,
    )

    profile = snapshot["risk_profile"]

    assert profile["max_loss"] == pytest.approx(0.0)
    assert profile["max_gain"] == pytest.approx(12.0)
    assert profile["min_pnl"] == pytest.approx(2.0)
    assert profile["input_warning"] is not None


def test_negative_underlying_scenario_is_rejected():
    legs = build_strategy_legs(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
    )

    with pytest.raises(ValueError, match="negative underlying price"):
        build_scenario_table(
            spot=100,
            legs=legs,
            scenario_moves=[-1.1],
        )
