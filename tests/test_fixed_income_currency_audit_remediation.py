from pathlib import Path

import pandas as pd
import pytest

from engines.fixed_income_engine import (
    apply_fx_conversion,
    build_currency_exposure_table,
    calculate_dv01_by_bucket,
    calculate_scenario_pnl,
    summarize_portfolio,
    validate_fx_rates,
)


def _two_currency_risk_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bond_id": ["EUR-1", "USD-1"],
            "currency": ["EUR", "USD"],
            "curve_bucket": ["2-5Y", "2-5Y"],
            "market_value": [1_000_000.0, 1_000_000.0],
            "dv01": [500.0, 500.0],
            "yield_to_maturity": [0.03, 0.05],
            "modified_duration": [5.0, 5.0],
            "convexity": [25.0, 25.0],
        }
    )


def test_missing_fx_rate_is_rejected():
    with pytest.raises(ValueError, match="Missing FX-to-base"):
        apply_fx_conversion(
            _two_currency_risk_df(),
            base_currency="EUR",
            fx_rates={"EUR": 1.0},
        )


def test_base_currency_rate_must_equal_one():
    with pytest.raises(ValueError, match="must equal 1.0"):
        validate_fx_rates(
            currencies={"EUR", "USD"},
            base_currency="EUR",
            fx_rates={"EUR": 0.99, "USD": 0.92},
        )


def test_non_positive_fx_rate_is_rejected():
    with pytest.raises(ValueError, match="strictly positive"):
        apply_fx_conversion(
            _two_currency_risk_df(),
            base_currency="EUR",
            fx_rates={"EUR": 1.0, "USD": 0.0},
        )


def test_fx_conversion_is_dimensionally_exact():
    converted = apply_fx_conversion(
        _two_currency_risk_df(),
        base_currency="EUR",
        fx_rates={"EUR": 1.0, "USD": 0.92},
    )
    usd = converted.loc[
        converted["currency"] == "USD"
    ].iloc[0]

    assert usd["market_value_base"] == pytest.approx(920_000.0)
    assert usd["dv01_base"] == pytest.approx(460.0)
    assert usd["market_value"] == pytest.approx(1_000_000.0)
    assert usd["dv01"] == pytest.approx(500.0)


def test_summary_uses_base_currency_not_raw_currency_sum():
    converted = apply_fx_conversion(
        _two_currency_risk_df(),
        base_currency="EUR",
        fx_rates={"EUR": 1.0, "USD": 0.92},
    )
    summary = summarize_portfolio(
        converted,
        base_currency="EUR",
    )

    assert summary.base_currency == "EUR"
    assert summary.total_market_value == pytest.approx(1_920_000.0)
    assert summary.total_dv01 == pytest.approx(960.0)
    assert summary.total_market_value != pytest.approx(
        converted["market_value"].sum()
    )


def test_unconverted_multicurrency_data_cannot_be_aggregated():
    with pytest.raises(
        ValueError,
        match="requires explicit FX conversion",
    ):
        summarize_portfolio(
            _two_currency_risk_df(),
            base_currency="EUR",
        )


def test_currency_bucket_and_scenario_totals_use_base_currency():
    converted = apply_fx_conversion(
        _two_currency_risk_df(),
        base_currency="EUR",
        fx_rates={"EUR": 1.0, "USD": 0.92},
    )
    currency_df = build_currency_exposure_table(converted)
    bucket_df = calculate_dv01_by_bucket(converted)
    scenario_df = calculate_scenario_pnl(converted)

    assert currency_df["market_value_base"].sum() == pytest.approx(
        1_920_000.0
    )
    assert bucket_df["dv01_base"].sum() == pytest.approx(960.0)

    spread_loss = scenario_df.loc[
        scenario_df["scenario_name"] == "Credit spread +50 bps",
        "estimated_pnl",
    ].iloc[0]

    assert spread_loss == pytest.approx(-48_000.0)
    assert set(scenario_df["currency"]) == {"EUR"}


def test_ui_and_report_expose_currency_contract():
    report = Path("reports/excel_exporter.py").read_text()

    assert "Currency_Exposure" in report
    assert "FX-to-base" in report
