from pathlib import Path

import numpy as np
import pytest

from engines.structured_products_engine import (
    AutocallableTerms,
    calculate_autocallable_payoff,
    validate_terms,
)
from engines.structured_products_valuation_engine import (
    build_observation_times,
    evaluate_autocallable_cashflows,
    validate_valuation_inputs,
)


def test_quarter_year_maturity_is_exact():
    inputs = validate_valuation_inputs(
        maturity_years=0.25,
        observations_per_year=1,
        simulations=1,
    )

    times = build_observation_times(inputs)

    assert list(times) == [0.25]
    assert times[-1] == pytest.approx(0.25)


def test_fractional_maturity_adds_final_stub():
    inputs = validate_valuation_inputs(
        maturity_years=3.25,
        observations_per_year=1,
        simulations=1,
    )

    times = build_observation_times(inputs)
    time_steps = np.diff(
        np.concatenate(([0.0], times))
    )

    assert list(times) == [
        1.0,
        2.0,
        3.0,
        3.25,
    ]
    assert time_steps.sum() == pytest.approx(3.25)
    assert time_steps[-1] == pytest.approx(0.25)


def test_quarter_year_cashflow_uses_exact_maturity():
    inputs = validate_valuation_inputs(
        notional=1000,
        initial_spots=[100],
        volatilities=[0.20],
        maturity_years=0.25,
        observations_per_year=1,
        autocall_barrier=1.00,
        coupon_barrier=0.80,
        protection_barrier=0.60,
        coupon_rate=0.08,
        risk_free_rate=0.00,
        simulations=1,
    )

    paths = np.array([[[0.90]]])

    cashflows = evaluate_autocallable_cashflows(
        paths,
        inputs,
    )

    row = cashflows.iloc[0]

    assert row["event_time_years"] == pytest.approx(0.25)
    assert row["coupon_paid"] == pytest.approx(20.0)
    assert row["payoff"] == pytest.approx(1020.0)
    assert not bool(
        row["protection_barrier_breached"]
    )


def test_valuation_proxy_rejects_inverted_barriers():
    with pytest.raises(
        ValueError,
        match="autocall_barrier >= coupon_barrier",
    ):
        validate_valuation_inputs(
            autocall_barrier=0.70,
            coupon_barrier=0.80,
            protection_barrier=0.60,
        )

    with pytest.raises(
        ValueError,
        match="coupon_barrier",
    ):
        validate_valuation_inputs(
            autocall_barrier=1.00,
            coupon_barrier=0.50,
            protection_barrier=0.60,
        )


def test_deterministic_engine_rejects_inverted_barriers():
    terms = AutocallableTerms(
        product_type="Phoenix",
        nominal=1000,
        coupon_rate_per_period=0.02,
        autocall_barrier=-0.20,
        coupon_barrier=0.00,
        protection_barrier=-0.40,
        memory_coupon=True,
    )

    with pytest.raises(
        ValueError,
        match="autocall_barrier >= coupon_barrier",
    ):
        validate_terms(terms)


def test_underlying_can_reach_exactly_zero():
    terms = AutocallableTerms(
        product_type="Athena",
        nominal=1000,
        coupon_rate_per_period=0.02,
        autocall_barrier=0.00,
        coupon_barrier=-0.30,
        protection_barrier=-0.40,
        memory_coupon=False,
    )

    result = calculate_autocallable_payoff(
        terms,
        [-1.0],
    )

    assert result.protection_barrier_breached
    assert result.redemption_amount == pytest.approx(0.0)
    assert result.capital_pnl == pytest.approx(-1000.0)
    assert result.total_payoff == pytest.approx(0.0)
