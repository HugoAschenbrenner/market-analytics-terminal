from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.portfolio_risk_engine import (
    analyze_price_frequency,
    calculate_cagr,
    calculate_historical_cvar,
    calculate_historical_var,
    calculate_horizon_return_series,
    prepare_price_data,
    resolve_periods_per_year,
    summarize_portfolio_risk,
)


def _monthly_price_data(
    periods: int = 24,
) -> pd.DataFrame:
    dates = pd.date_range(
        "2024-01-31",
        periods=periods,
        freq=pd.offsets.MonthEnd(),
    )

    return pd.DataFrame(
        {
            "date": dates,
            "ASSET_A": np.linspace(
                100.0,
                125.0,
                periods,
            ),
            "ASSET_B": np.linspace(
                100.0,
                110.0,
                periods,
            ),
        }
    )


def test_monthly_frequency_is_inferred_as_12():
    analysis = analyze_price_frequency(
        _monthly_price_data()
    )

    assert analysis.inferred_frequency == "Monthly"
    assert analysis.inferred_periods_per_year == 12
    assert (
        27.0
        <= analysis.median_spacing_days
        <= 32.0
    )


def test_weekly_frequency_is_inferred_as_52():
    dates = pd.date_range(
        "2025-01-03",
        periods=30,
        freq="W-FRI",
    )

    prices = pd.DataFrame(
        {
            "date": dates,
            "A": np.linspace(100, 115, 30),
            "B": np.linspace(100, 108, 30),
        }
    )

    analysis = analyze_price_frequency(prices)

    assert analysis.inferred_frequency == "Weekly"
    assert analysis.inferred_periods_per_year == 52


def test_duplicated_dates_are_rejected():
    prices = _monthly_price_data(6)
    prices.loc[5, "date"] = prices.loc[4, "date"]

    with pytest.raises(
        ValueError,
        match="duplicated dates",
    ):
        prepare_price_data(prices)


def test_missing_and_non_positive_prices_are_rejected():
    missing_prices = _monthly_price_data(6)
    missing_prices.loc[2, "ASSET_A"] = np.nan

    with pytest.raises(
        ValueError,
        match="missing or non-numeric",
    ):
        prepare_price_data(missing_prices)

    zero_prices = _monthly_price_data(6)
    zero_prices.loc[2, "ASSET_A"] = 0.0

    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        prepare_price_data(zero_prices)


def test_material_date_gap_creates_quality_warning():
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-06",
                    "2025-01-07",
                    "2025-02-20",
                    "2025-02-21",
                ]
            ),
            "A": [100, 101, 102, 103, 104, 105],
            "B": [100, 100, 101, 101, 102, 103],
        }
    )

    analysis = analyze_price_frequency(prices)

    assert analysis.inferred_frequency == "Daily"
    assert analysis.data_quality_status == "Review"
    assert analysis.maximum_gap_days > 10
    assert analysis.warnings


def test_cagr_is_geometric_not_arithmetic():
    returns = pd.Series([0.01] * 12)

    cagr = calculate_cagr(
        returns,
        periods_per_year=12,
    )

    assert cagr == pytest.approx(
        1.01 ** 12 - 1.0
    )


def test_horizon_returns_are_compounded():
    returns = pd.Series(
        [0.10, -0.10, 0.00]
    )

    horizon_returns = (
        calculate_horizon_return_series(
            returns,
            horizon_periods=2,
        )
    )

    assert list(horizon_returns) == pytest.approx(
        [-0.01, -0.10]
    )


def test_var_and_cvar_accept_explicit_horizon():
    returns = pd.Series(
        [
            0.02,
            -0.03,
            0.01,
            -0.04,
            0.02,
            -0.01,
        ]
    )

    one_period_var = calculate_historical_var(
        returns,
        confidence_level=0.80,
        horizon_periods=1,
    )

    two_period_var = calculate_historical_var(
        returns,
        confidence_level=0.80,
        horizon_periods=2,
    )

    two_period_cvar = calculate_historical_cvar(
        returns,
        confidence_level=0.80,
        horizon_periods=2,
    )

    assert one_period_var >= 0
    assert two_period_var >= 0
    assert two_period_cvar >= two_period_var


def test_monthly_summary_uses_12_not_252():
    returns_df = pd.DataFrame(
        {
            "A": [0.01, -0.005] * 12,
            "B": [0.005, 0.002] * 12,
        }
    )

    summary = summarize_portfolio_risk(
        returns_df=returns_df,
        weights={"A": 0.60, "B": 0.40},
        periods_per_year=12,
        frequency_label="Monthly",
        var_horizon_periods=3,
    )

    assert summary.periods_per_year == 12
    assert summary.frequency_label == "Monthly"
    assert summary.sample_years == pytest.approx(2.0)
    assert summary.var_horizon_periods == 3
    assert summary.cagr != pytest.approx(
        summary.annualized_return
    )


def test_frequency_override_contract():
    assert (
        resolve_periods_per_year(
            "Auto-detect",
            inferred_periods_per_year=52,
        )
        == 52
    )

    assert (
        resolve_periods_per_year(
            "Monthly",
            inferred_periods_per_year=252,
        )
        == 12
    )

    assert (
        resolve_periods_per_year(
            "Custom",
            inferred_periods_per_year=252,
            custom_periods_per_year=26,
        )
        == 26
    )


def test_portfolio_ui_exposes_frequency_and_horizon():
    page = Path(
        "app_pages/portfolio_risk.py"
    ).read_text()

    assert "Frequency & Data Quality Contract" in page
    assert "Annualization frequency" in page
    assert "Historical VaR / CVaR horizon" in page
    assert "Arithmetic Ann. Return" in page
    assert "Geometric CAGR" in page
    assert (
        "periods_per_year=int(periods_per_year)"
        in page
    )
    assert "var_horizon_periods=int(" in page
