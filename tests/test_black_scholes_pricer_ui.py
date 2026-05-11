import pandas as pd

from app_pages.structured_products import (
    _bsm_greeks_to_dataframe,
    _bsm_outputs_to_dataframe,
    _format_pricer_number,
)
from engines.options_pricing_engine import build_black_scholes_snapshot


def test_format_pricer_number_handles_numbers_strings_and_none():
    assert _format_pricer_number(None) == "N/A"
    assert _format_pricer_number("Unlimited") == "Unlimited"
    assert _format_pricer_number(10.123456, decimals=2) == "10.12"
    assert _format_pricer_number(4.2, decimals=1, suffix="%") == "4.2%"


def test_bsm_outputs_to_dataframe_contains_pricing_metrics():
    snapshot = build_black_scholes_snapshot(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
    )

    df = _bsm_outputs_to_dataframe(snapshot)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["metric", "value"]
    assert "Theoretical Value" in list(df["metric"])
    assert "Intrinsic Value" in list(df["metric"])
    assert "Time Value" in list(df["metric"])


def test_bsm_greeks_to_dataframe_contains_greeks():
    snapshot = build_black_scholes_snapshot(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
    )

    df = _bsm_greeks_to_dataframe(snapshot)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["greek", "value", "interpretation"]
    assert "Delta" in list(df["greek"])
    assert "Gamma" in list(df["greek"])
    assert "Vega" in list(df["greek"])
    assert "Theta Daily" in list(df["greek"])
    assert "Rho" in list(df["greek"])
