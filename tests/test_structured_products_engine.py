import pandas as pd
import pytest

from engines.structured_products_engine import (
    AutocallableTerms,
    build_standard_scenario_paths,
    calculate_athena_payoff,
    calculate_autocallable_payoff,
    calculate_capital_redemption,
    calculate_phoenix_payoff,
    calculate_scenario_table,
    calculate_worst_of_performance,
    generate_structured_product_commentary,
    is_autocall_triggered,
    is_coupon_paid,
    is_protection_breached,
    payoff_result_to_dict,
)


def _athena_terms():
    return AutocallableTerms(
        product_type="Athena",
        nominal=1_000_000,
        coupon_rate_per_period=0.02,
        autocall_barrier=0.00,
        coupon_barrier=-0.30,
        protection_barrier=-0.40,
        memory_coupon=False,
    )


def _phoenix_terms(memory_coupon=True):
    return AutocallableTerms(
        product_type="Phoenix",
        nominal=1_000_000,
        coupon_rate_per_period=0.02,
        autocall_barrier=0.00,
        coupon_barrier=-0.30,
        protection_barrier=-0.40,
        memory_coupon=memory_coupon,
    )


def test_worst_of_performance_returns_minimum_performance():
    worst = calculate_worst_of_performance([0.05, -0.20, 0.10])

    assert worst == -0.20


def test_autocall_trigger_condition():
    assert is_autocall_triggered(performance=0.01, autocall_barrier=0.00) is True
    assert is_autocall_triggered(performance=-0.01, autocall_barrier=0.00) is False


def test_coupon_paid_condition():
    assert is_coupon_paid(performance=-0.20, coupon_barrier=-0.30) is True
    assert is_coupon_paid(performance=-0.40, coupon_barrier=-0.30) is False


def test_protection_breach_condition():
    assert is_protection_breached(final_performance=-0.50, protection_barrier=-0.40) is True
    assert is_protection_breached(final_performance=-0.20, protection_barrier=-0.40) is False


def test_capital_redemption_when_barrier_not_breached():
    redemption = calculate_capital_redemption(
        nominal=1_000_000,
        final_performance=-0.20,
        protection_barrier=-0.40,
    )

    assert redemption == 1_000_000


def test_capital_redemption_when_barrier_breached():
    redemption = calculate_capital_redemption(
        nominal=1_000_000,
        final_performance=-0.50,
        protection_barrier=-0.40,
    )

    assert redemption == 500_000


def test_athena_autocalls_and_pays_accumulated_coupon():
    terms = _athena_terms()
    result = calculate_athena_payoff(terms, [-0.10, 0.02, -0.20, -0.30])

    assert result.autocalled is True
    assert result.autocall_observation == 2
    assert result.total_coupons_paid == 40_000
    assert result.total_payoff == 1_040_000


def test_athena_no_autocall_protected_capital():
    terms = _athena_terms()
    result = calculate_athena_payoff(terms, [-0.10, -0.20, -0.30, -0.20])

    assert result.autocalled is False
    assert result.protection_barrier_breached is False
    assert result.redemption_amount == 1_000_000
    assert result.total_pnl == 0


def test_athena_barrier_breach_creates_capital_loss():
    terms = _athena_terms()
    result = calculate_athena_payoff(terms, [-0.10, -0.20, -0.30, -0.50])

    assert result.autocalled is False
    assert result.protection_barrier_breached is True
    assert result.redemption_amount == 500_000
    assert result.total_pnl == -500_000


def test_phoenix_pays_coupon_when_coupon_barrier_met():
    terms = _phoenix_terms(memory_coupon=False)
    result = calculate_phoenix_payoff(terms, [-0.20, -0.20, -0.20, -0.20])

    assert result.total_coupons_paid == 80_000
    assert result.redemption_amount == 1_000_000
    assert result.total_payoff == 1_080_000


def test_phoenix_memory_coupon_recovers_missed_coupon():
    terms = _phoenix_terms(memory_coupon=True)
    result = calculate_phoenix_payoff(terms, [-0.40, -0.20, -0.20, -0.20])

    # Obs 1 misses coupon, obs 2 pays two coupons, obs 3 and 4 pay one each.
    assert result.total_coupons_paid == 80_000


def test_phoenix_without_memory_does_not_recover_missed_coupon():
    terms = _phoenix_terms(memory_coupon=False)
    result = calculate_phoenix_payoff(terms, [-0.40, -0.20, -0.20, -0.20])

    assert result.total_coupons_paid == 60_000


def test_phoenix_autocall_after_coupon_logic():
    terms = _phoenix_terms(memory_coupon=True)
    result = calculate_phoenix_payoff(terms, [-0.40, 0.02, -0.20, -0.20])

    assert result.autocalled is True
    assert result.autocall_observation == 2
    assert result.total_coupons_paid == 40_000
    assert result.total_payoff == 1_040_000


def test_calculate_autocallable_payoff_routes_by_product_type():
    athena_result = calculate_autocallable_payoff(_athena_terms(), [0.01, -0.20])
    phoenix_result = calculate_autocallable_payoff(_phoenix_terms(), [0.01, -0.20])

    assert athena_result.product_type == "Athena"
    assert phoenix_result.product_type == "Phoenix"


def test_payoff_result_to_dict_returns_dictionary():
    result = calculate_autocallable_payoff(_athena_terms(), [0.01, -0.20])
    result_dict = payoff_result_to_dict(result)

    assert isinstance(result_dict, dict)
    assert "total_payoff" in result_dict


def test_standard_scenario_paths_returns_expected_scenarios():
    scenario_paths = build_standard_scenario_paths(4)

    assert "Early autocall" in scenario_paths
    assert "Barrier breach / capital loss" in scenario_paths
    assert len(scenario_paths["Early autocall"]) == 4


def test_scenario_table_returns_dataframe():
    terms = _phoenix_terms()
    scenario_paths = build_standard_scenario_paths(4)
    scenario_df = calculate_scenario_table(terms, scenario_paths)

    assert isinstance(scenario_df, pd.DataFrame)
    assert len(scenario_df) == 5
    assert "total_payoff" in scenario_df.columns


def test_invalid_empty_path_raises_error():
    with pytest.raises(ValueError):
        calculate_autocallable_payoff(_athena_terms(), [])


def test_commentary_returns_non_empty_list():
    terms = _phoenix_terms()
    result = calculate_autocallable_payoff(terms, [-0.40, 0.02, -0.20])
    commentary = generate_structured_product_commentary(terms, result)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
