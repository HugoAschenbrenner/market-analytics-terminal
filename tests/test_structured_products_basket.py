import pandas as pd
import pytest

from engines.structured_products_engine import (
    AutocallableTerms,
    build_standard_basket_scenario_paths,
    calculate_basket_scenario_table,
    calculate_worst_of_basket_payoff,
    calculate_worst_of_path,
    generate_worst_of_basket_commentary,
    identify_worst_performer,
    identify_worst_performer_at_maturity,
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


def test_calculate_worst_of_path_returns_minimum_each_observation():
    paths = {
        "A": [0.05, -0.10, -0.20],
        "B": [0.03, -0.30, -0.10],
        "C": [0.01, -0.15, -0.25],
    }

    worst_path = calculate_worst_of_path(paths)

    assert worst_path == [0.01, -0.30, -0.25]


def test_worst_of_path_raises_error_for_unequal_path_lengths():
    paths = {
        "A": [0.05, -0.10],
        "B": [0.03],
    }

    with pytest.raises(ValueError):
        calculate_worst_of_path(paths)


def test_identify_worst_performer_returns_lowest_name():
    worst = identify_worst_performer(
        {
            "A": 0.05,
            "B": -0.20,
            "C": -0.10,
        }
    )

    assert worst["underlying"] == "B"
    assert worst["performance"] == -0.20


def test_identify_worst_performer_at_maturity_uses_final_observation():
    paths = {
        "A": [0.05, -0.10],
        "B": [0.03, -0.25],
        "C": [0.01, -0.15],
    }

    worst = identify_worst_performer_at_maturity(paths)

    assert worst["underlying"] == "B"
    assert worst["performance"] == -0.25


def test_worst_of_basket_payoff_can_autocall():
    terms = _phoenix_terms()
    paths = {
        "A": [0.05, -0.10],
        "B": [0.02, -0.20],
        "C": [0.01, -0.30],
    }

    result = calculate_worst_of_basket_payoff(terms, paths)

    payoff = result["payoff_result"]

    assert payoff.autocalled is True
    assert payoff.autocall_observation == 1
    assert payoff.total_payoff == 1_020_000


def test_worst_of_basket_barrier_breach_creates_capital_loss():
    terms = _phoenix_terms()
    paths = {
        "A": [-0.20, -0.20],
        "B": [-0.20, -0.50],
        "C": [-0.20, -0.25],
    }

    result = calculate_worst_of_basket_payoff(terms, paths)
    payoff = result["payoff_result"]

    assert payoff.protection_barrier_breached is True
    assert payoff.redemption_amount == 500_000
    assert result["worst_performer_at_maturity"] == "B"


def test_standard_basket_scenario_paths_have_expected_structure():
    scenarios = build_standard_basket_scenario_paths(4)

    assert "Single-name barrier breach" in scenarios
    assert len(scenarios["Single-name barrier breach"]) == 3

    for underlying_paths in scenarios.values():
        for path in underlying_paths.values():
            assert len(path) == 4


def test_basket_scenario_table_returns_dataframe():
    terms = _phoenix_terms()
    scenarios = build_standard_basket_scenario_paths(4)

    scenario_df = calculate_basket_scenario_table(terms, scenarios)

    assert isinstance(scenario_df, pd.DataFrame)
    assert len(scenario_df) == 5
    assert "worst_of_path" in scenario_df.columns
    assert "worst_performer_at_maturity" in scenario_df.columns
    assert "total_payoff" in scenario_df.columns


def test_basket_scenario_table_contains_barrier_breach_scenario():
    terms = _phoenix_terms()
    scenarios = build_standard_basket_scenario_paths(4)

    scenario_df = calculate_basket_scenario_table(terms, scenarios)

    assert scenario_df["protection_barrier_breached"].any()


def test_worst_of_basket_commentary_returns_non_empty_list():
    terms = _phoenix_terms()
    scenarios = build_standard_basket_scenario_paths(4)

    commentary = generate_worst_of_basket_commentary(
        terms=terms,
        underlying_paths=scenarios["Single-name barrier breach"],
    )

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
