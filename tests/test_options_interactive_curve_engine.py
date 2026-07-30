import pandas as pd
import pytest

from engines.options_pricing_engine import (
    SUPPORTED_BSM_CURVE_VARIABLES,
    build_bsm_interactive_explorer_payload,
    build_bsm_sensitivity_curve,
    build_local_tangent_line,
    estimate_local_curve_slope,
    normalize_bsm_curve_variable,
)


def test_normalize_bsm_curve_variable():
    assert normalize_bsm_curve_variable("spot") == "Spot"
    assert normalize_bsm_curve_variable("risk-free rate") == "Rate"
    assert normalize_bsm_curve_variable("implied volatility") == "Volatility"

    with pytest.raises(ValueError):
        normalize_bsm_curve_variable("credit spread")


def test_build_bsm_sensitivity_curve_for_spot():
    curve = build_bsm_sensitivity_curve(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
        variable="Spot",
        points=21,
    )

    assert isinstance(curve, pd.DataFrame)
    assert curve.shape[0] == 21
    assert list(curve.columns) == [
        "axis",
        "axis_value",
        "price",
        "delta",
        "gamma",
        "vega_1pct",
        "theta_daily",
        "rho_1pct",
    ]
    assert curve["axis"].iloc[0] == "Spot"
    assert curve["price"].iloc[-1] > curve["price"].iloc[0]


def test_build_bsm_sensitivity_curve_for_volatility_has_positive_prices():
    curve = build_bsm_sensitivity_curve(
        option_type="Put",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.03,
        volatility=0.25,
        variable="Volatility",
        points=11,
    )

    assert curve.shape[0] == 11
    assert (curve["price"] > 0).all()
    assert curve["axis"].iloc[0] == "Volatility"


def test_estimate_local_curve_slope_and_tangent_line():
    curve = build_bsm_sensitivity_curve(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        variable="Spot",
        points=41,
    )

    slope_payload = estimate_local_curve_slope(curve, selected_x=100)
    tangent = build_local_tangent_line(curve, selected_x=100)

    assert set(slope_payload.keys()) == {"anchor_x", "anchor_y", "slope"}
    assert 95 <= slope_payload["anchor_x"] <= 105
    assert slope_payload["slope"] > 0
    assert tangent.shape[0] == 3
    assert "tangent_value" in tangent.columns
    assert "local_slope" in tangent.columns


def test_build_bsm_interactive_explorer_payload_contains_all_curves():
    payload = build_bsm_interactive_explorer_payload(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
        points=21,
    )

    assert "snapshot" in payload
    assert "curves" in payload
    assert "spot_price_tangent" in payload
    assert set(payload["curves"].keys()) == set(SUPPORTED_BSM_CURVE_VARIABLES)

    for curve in payload["curves"].values():
        assert isinstance(curve, pd.DataFrame)
        assert curve.shape[0] == 21
