import numpy as np
import pandas as pd
import pytest

from engines.structured_products_valuation_engine import (
    DISCLAIMER,
    build_autocallable_valuation_snapshot,
    build_constant_correlation_matrix,
    build_observation_times,
    build_valuation_sensitivity_table,
    evaluate_autocallable_cashflows,
    generate_valuation_desk_interpretation,
    simulate_correlated_gbm_performance_paths,
    summarize_autocallable_cashflows,
    validate_valuation_inputs,
    valuation_summary_to_dataframe,
)


def test_validate_valuation_inputs_normalizes_core_fields():
    inputs = validate_valuation_inputs(
        initial_spots=[100, 90],
        volatilities=[0.20, 0.25],
        simulations=100,
    )

    assert inputs.initial_spots == (100.0, 90.0)
    assert inputs.volatilities == (0.20, 0.25)
    assert inputs.simulations == 100


def test_build_constant_correlation_matrix():
    matrix = build_constant_correlation_matrix(asset_count=3, correlation=0.25)

    assert matrix.shape == (3, 3)
    assert np.allclose(np.diag(matrix), 1.0)
    assert matrix[0, 1] == pytest.approx(0.25)


def test_build_observation_times():
    inputs = validate_valuation_inputs(maturity_years=2, observations_per_year=2)

    times = build_observation_times(inputs)

    assert list(times) == [0.5, 1.0, 1.5, 2.0]


def test_simulate_correlated_gbm_performance_paths_shape_and_reproducibility():
    inputs = validate_valuation_inputs(
        initial_spots=[100, 100],
        volatilities=[0.20, 0.30],
        maturity_years=1,
        observations_per_year=2,
        simulations=50,
        seed=123,
    )

    first = simulate_correlated_gbm_performance_paths(inputs)
    second = simulate_correlated_gbm_performance_paths(inputs)

    assert first.shape == (50, 2, 2)
    assert np.allclose(first, second)


def test_evaluate_autocallable_cashflows_manual_paths():
    inputs = validate_valuation_inputs(
        notional=1000,
        initial_spots=[100],
        volatilities=[0.20],
        maturity_years=2,
        observations_per_year=1,
        autocall_barrier=1.00,
        coupon_barrier=0.80,
        protection_barrier=0.60,
        coupon_rate=0.10,
        risk_free_rate=0.00,
        simulations=3,
    )

    paths = np.array(
        [
            [[1.05], [1.10]],
            [[0.95], [0.85]],
            [[0.95], [0.50]],
        ]
    )

    cashflows = evaluate_autocallable_cashflows(paths, inputs)

    assert list(cashflows["event_type"]) == [
        "autocall",
        "maturity_coupon_paid",
        "maturity_capital_loss",
    ]
    assert list(cashflows["payoff"]) == [1100.0, 1200.0, 500.0]
    assert list(cashflows["coupon_paid"]) == [100.0, 200.0, 0.0]


def test_summarize_autocallable_cashflows_manual_paths():
    inputs = validate_valuation_inputs(
        notional=1000,
        initial_spots=[100],
        volatilities=[0.20],
        maturity_years=2,
        observations_per_year=1,
        autocall_barrier=1.00,
        coupon_barrier=0.80,
        protection_barrier=0.60,
        coupon_rate=0.10,
        risk_free_rate=0.00,
        simulations=3,
    )

    paths = np.array(
        [
            [[1.05], [1.10]],
            [[0.95], [0.85]],
            [[0.95], [0.50]],
        ]
    )

    cashflows = evaluate_autocallable_cashflows(paths, inputs)
    summary = summarize_autocallable_cashflows(cashflows, inputs)

    assert summary["fair_value_proxy"] == pytest.approx(933.333333, rel=1e-6)
    assert summary["fair_value_pct_notional"] == pytest.approx(93.3333, rel=1e-6)
    assert summary["autocall_probability"] == pytest.approx(1 / 3, rel=1e-6)
    assert summary["protection_barrier_breach_probability"] == pytest.approx(1 / 3, rel=1e-6)
    assert summary["expected_maturity_years"] == pytest.approx(5 / 3, rel=1e-6)


def test_build_autocallable_valuation_snapshot_outputs_core_payload():
    snapshot = build_autocallable_valuation_snapshot(
        initial_spots=[100, 100],
        volatilities=[0.20, 0.25],
        correlation=0.40,
        simulations=200,
        seed=7,
    )

    assert "inputs" in snapshot
    assert "summary" in snapshot
    assert isinstance(snapshot["cashflows"], pd.DataFrame)
    assert "fair_value_pct_notional" in snapshot["summary"]
    assert "autocall_probability" in snapshot["summary"]
    assert DISCLAIMER in snapshot["disclaimer"]


def test_valuation_summary_to_dataframe_and_interpretation():
    snapshot = build_autocallable_valuation_snapshot(
        simulations=100,
        seed=11,
    )

    summary_df = valuation_summary_to_dataframe(snapshot["summary"])
    bullets = generate_valuation_desk_interpretation(
        snapshot["summary"],
        validate_valuation_inputs(simulations=100, seed=11),
    )

    assert list(summary_df.columns) == ["metric", "value"]
    assert "Fair Value Proxy" in list(summary_df["metric"])
    assert any("Fair value proxy" in bullet for bullet in bullets)
    assert any("not issuer pricing" in bullet or "not issuer" in bullet.lower() for bullet in bullets)


def test_build_valuation_sensitivity_table_shape_and_columns():
    inputs = validate_valuation_inputs(
        simulations=50,
        seed=42,
        initial_spots=[100, 100],
        volatilities=[0.20, 0.25],
        correlation=0.30,
    )

    table = build_valuation_sensitivity_table(
        inputs,
        volatility_shocks=[0.0, 0.05],
        correlation_shocks=[0.0, 0.10],
    )

    assert table.shape[0] == 4
    assert list(table.columns) == [
        "scenario",
        "avg_volatility",
        "correlation",
        "fair_value_pct_notional",
        "autocall_probability",
        "barrier_breach_probability",
        "expected_maturity_years",
    ]


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        validate_valuation_inputs(initial_spots=[100, 90], volatilities=[0.20])

    with pytest.raises(ValueError):
        validate_valuation_inputs(correlation=1.2)

    with pytest.raises(ValueError):
        validate_valuation_inputs(notional=0)
