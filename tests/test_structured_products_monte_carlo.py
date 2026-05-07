import pandas as pd
import pytest

from engines.structured_products_engine import (
    AutocallableTerms,
    build_constant_correlation_matrix,
    calculate_monte_carlo_results_table,
    generate_monte_carlo_commentary,
    simulate_single_underlying_paths,
    simulate_worst_of_basket_paths,
    summarize_monte_carlo_results,
)


def _phoenix_terms():
    return AutocallableTerms(
        product_type="Phoenix",
        nominal=1_000_000,
        coupon_rate_per_period=0.02,
        autocall_barrier=0.00,
        coupon_barrier=-0.30,
        protection_barrier=-0.40,
        memory_coupon=True,
    )


def test_single_underlying_simulation_shape():
    paths = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    assert paths.shape == (100, 4)


def test_single_underlying_simulation_is_reproducible_with_seed():
    paths_1 = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )
    paths_2 = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    assert (paths_1 == paths_2).all()


def test_correlation_matrix_shape_and_diagonal():
    matrix = build_constant_correlation_matrix(
        n_underlyings=3,
        correlation=0.50,
    )

    assert matrix.shape == (3, 3)
    assert matrix[0, 0] == 1.0
    assert matrix[1, 1] == 1.0
    assert matrix[2, 2] == 1.0


def test_invalid_correlation_raises_error():
    with pytest.raises(ValueError):
        build_constant_correlation_matrix(
            n_underlyings=3,
            correlation=1.0,
        )


def test_worst_of_basket_simulation_shapes():
    simulation = simulate_worst_of_basket_paths(
        number_of_observations=4,
        n_underlyings=3,
        n_simulations=100,
        volatility=0.25,
        correlation=0.50,
        seed=42,
    )

    assert simulation["underlying_performance_paths"].shape == (100, 4, 3)
    assert simulation["worst_of_performance_paths"].shape == (100, 4)


def test_worst_of_path_is_less_than_or_equal_to_each_underlying():
    simulation = simulate_worst_of_basket_paths(
        number_of_observations=4,
        n_underlyings=3,
        n_simulations=100,
        volatility=0.25,
        correlation=0.50,
        seed=42,
    )

    underlying_paths = simulation["underlying_performance_paths"]
    worst_paths = simulation["worst_of_performance_paths"]

    assert (worst_paths <= underlying_paths[:, :, 0]).all()
    assert (worst_paths <= underlying_paths[:, :, 1]).all()
    assert (worst_paths <= underlying_paths[:, :, 2]).all()


def test_monte_carlo_results_table_returns_dataframe():
    terms = _phoenix_terms()
    paths = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    results_df = calculate_monte_carlo_results_table(terms, paths)

    assert isinstance(results_df, pd.DataFrame)
    assert len(results_df) == 100
    assert "total_payoff" in results_df.columns
    assert "autocalled" in results_df.columns


def test_monte_carlo_summary_probabilities_are_between_zero_and_one():
    terms = _phoenix_terms()
    paths = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    results_df = calculate_monte_carlo_results_table(terms, paths)
    summary = summarize_monte_carlo_results(results_df)

    assert 0 <= summary["autocall_probability"] <= 1
    assert 0 <= summary["barrier_breach_probability"] <= 1
    assert summary["number_of_simulations"] == 100


def test_monte_carlo_summary_has_required_keys():
    terms = _phoenix_terms()
    paths = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    results_df = calculate_monte_carlo_results_table(terms, paths)
    summary = summarize_monte_carlo_results(results_df)

    required_keys = {
        "number_of_simulations",
        "autocall_probability",
        "barrier_breach_probability",
        "expected_payoff",
        "expected_pnl",
        "expected_return",
        "payoff_volatility",
        "expected_coupons",
        "expected_redemption",
        "p5_payoff",
        "p50_payoff",
        "p95_payoff",
    }

    assert required_keys.issubset(summary.keys())


def test_monte_carlo_commentary_returns_non_empty_list():
    terms = _phoenix_terms()
    paths = simulate_single_underlying_paths(
        number_of_observations=4,
        n_simulations=100,
        volatility=0.20,
        seed=42,
    )

    results_df = calculate_monte_carlo_results_table(terms, paths)
    summary = summarize_monte_carlo_results(results_df)
    commentary = generate_monte_carlo_commentary(summary, is_worst_of=False)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
