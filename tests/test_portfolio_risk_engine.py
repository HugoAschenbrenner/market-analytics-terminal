import pandas as pd
import pytest

from engines.portfolio_risk_engine import (
    build_sample_price_data,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_asset_returns,
    calculate_correlation_matrix,
    calculate_cumulative_return_series,
    calculate_drawdown_series,
    calculate_historical_cvar,
    calculate_historical_var,
    calculate_portfolio_returns,
    calculate_risk_contribution,
    calculate_sharpe_ratio,
    calculate_stress_scenario_table,
    generate_portfolio_risk_commentary,
    normalize_weights,
    portfolio_risk_summary_to_dict,
    summarize_portfolio_risk,
)


def _sample_returns():
    price_df = build_sample_price_data(n_days=252, seed=42)
    return calculate_asset_returns(price_df)


def _sample_weights():
    return {
        "US_EQUITY": 0.35,
        "EUROPE_EQUITY": 0.20,
        "US_TREASURY": 0.20,
        "IG_CREDIT": 0.15,
        "GOLD": 0.10,
    }


def test_sample_price_data_has_expected_columns():
    price_df = build_sample_price_data(n_days=100, seed=42)

    expected_columns = {
        "date",
        "US_EQUITY",
        "EUROPE_EQUITY",
        "US_TREASURY",
        "IG_CREDIT",
        "GOLD",
    }

    assert expected_columns.issubset(set(price_df.columns))
    assert len(price_df) == 100


def test_asset_returns_are_dataframe_and_not_empty():
    price_df = build_sample_price_data(n_days=100, seed=42)
    returns_df = calculate_asset_returns(price_df)

    assert isinstance(returns_df, pd.DataFrame)
    assert not returns_df.empty
    assert len(returns_df) == 99


def test_normalize_weights_sum_to_one():
    weights = normalize_weights({"A": 50, "B": 50})

    assert abs(sum(weights.values()) - 1.0) < 1e-12


def test_zero_total_weight_raises_error():
    with pytest.raises(ValueError):
        normalize_weights({"A": 0, "B": 0})


def test_portfolio_returns_length_matches_asset_returns():
    returns_df = _sample_returns()
    portfolio_returns = calculate_portfolio_returns(returns_df, _sample_weights())

    assert len(portfolio_returns) == len(returns_df)


def test_portfolio_returns_are_weighted_sum():
    returns_df = pd.DataFrame(
        {
            "A": [0.10, 0.00],
            "B": [0.00, 0.10],
        }
    )

    weights = {"A": 0.50, "B": 0.50}
    portfolio_returns = calculate_portfolio_returns(returns_df, weights)

    assert list(portfolio_returns) == [0.05, 0.05]


def test_cumulative_return_series_starts_after_first_period():
    returns = pd.Series([0.10, -0.05])
    cumulative = calculate_cumulative_return_series(returns)

    assert abs(cumulative.iloc[-1] - 1.045) < 1e-12


def test_drawdown_is_never_positive():
    returns = pd.Series([0.10, -0.05, 0.02])
    drawdown = calculate_drawdown_series(returns)

    assert (drawdown <= 0).all()


def test_var_is_positive_loss_number():
    returns = pd.Series([0.01, -0.02, -0.05, 0.03, -0.01])
    var = calculate_historical_var(returns, confidence_level=0.95)

    assert var >= 0


def test_cvar_is_at_least_var_or_equal_under_small_samples():
    returns = pd.Series([0.01, -0.02, -0.05, 0.03, -0.01])
    var = calculate_historical_var(returns, confidence_level=0.80)
    cvar = calculate_historical_cvar(returns, confidence_level=0.80)

    assert cvar >= var


def test_annualized_return_calculation():
    returns = pd.Series([0.01, 0.01])
    annualized_return = calculate_annualized_return(returns, periods_per_year=252)

    assert annualized_return == 2.52


def test_annualized_volatility_is_positive_for_variable_returns():
    returns = pd.Series([0.01, -0.01, 0.02, -0.02])
    annualized_vol = calculate_annualized_volatility(returns, periods_per_year=252)

    assert annualized_vol > 0


def test_sharpe_ratio_zero_when_volatility_zero():
    sharpe = calculate_sharpe_ratio(
        annualized_return=0.10,
        annualized_volatility=0.0,
        risk_free_rate=0.02,
    )

    assert sharpe == 0.0


def test_portfolio_risk_summary_returns_valid_metrics():
    returns_df = _sample_returns()
    summary = summarize_portfolio_risk(
        returns_df=returns_df,
        weights=_sample_weights(),
        risk_free_rate=0.02,
    )

    assert summary.number_of_assets == 5
    assert summary.number_of_observations == len(returns_df)
    assert summary.annualized_volatility > 0


def test_portfolio_risk_summary_to_dict_returns_dictionary():
    returns_df = _sample_returns()
    summary = summarize_portfolio_risk(
        returns_df=returns_df,
        weights=_sample_weights(),
        risk_free_rate=0.02,
    )
    summary_dict = portfolio_risk_summary_to_dict(summary)

    assert isinstance(summary_dict, dict)
    assert "annualized_volatility" in summary_dict


def test_correlation_matrix_is_square():
    returns_df = _sample_returns()
    corr = calculate_correlation_matrix(returns_df)

    assert corr.shape[0] == corr.shape[1]
    assert corr.shape[0] == len(returns_df.columns)


def test_risk_contribution_percentages_sum_to_one():
    returns_df = _sample_returns()
    risk_contribution = calculate_risk_contribution(returns_df, _sample_weights())

    assert abs(risk_contribution["pct_contribution_to_volatility"].sum() - 1.0) < 1e-9


def test_stress_scenario_table_returns_dataframe():
    stress_df = calculate_stress_scenario_table(_sample_weights())

    assert isinstance(stress_df, pd.DataFrame)
    assert len(stress_df) == 5
    assert "estimated_portfolio_return" in stress_df.columns


def test_portfolio_risk_commentary_returns_non_empty_list():
    returns_df = _sample_returns()
    weights = _sample_weights()
    summary = summarize_portfolio_risk(returns_df, weights)
    risk_contribution = calculate_risk_contribution(returns_df, weights)
    stress_df = calculate_stress_scenario_table(weights)

    commentary = generate_portfolio_risk_commentary(
        summary=summary,
        risk_contribution_df=risk_contribution,
        stress_df=stress_df,
    )

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
