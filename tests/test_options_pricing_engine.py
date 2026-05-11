import pytest

from engines.options_pricing_engine import (
    DISCLAIMER,
    black_scholes_greeks,
    black_scholes_price,
    build_black_scholes_snapshot,
    build_pricing_sensitivity_table,
    calculate_d1_d2,
    generate_pricing_desk_interpretation,
    norm_cdf,
    norm_pdf,
    normalize_option_type,
    option_intrinsic_value,
)


def test_normal_distribution_helpers():
    assert norm_cdf(0.0) == pytest.approx(0.5, abs=1e-10)
    assert norm_pdf(0.0) == pytest.approx(0.39894228, rel=1e-6)


def test_normalize_option_type():
    assert normalize_option_type(" call ") == "Call"
    assert normalize_option_type("PUT") == "Put"

    with pytest.raises(ValueError):
        normalize_option_type("digital")


def test_calculate_d1_d2_known_values():
    result = calculate_d1_d2(
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
    )

    assert result["d1"] == pytest.approx(0.35, rel=1e-6)
    assert result["d2"] == pytest.approx(0.15, rel=1e-6)


def test_black_scholes_call_put_prices_known_values():
    call_price = black_scholes_price(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
    )
    put_price = black_scholes_price(
        option_type="Put",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
    )

    assert call_price == pytest.approx(10.4506, rel=1e-4)
    assert put_price == pytest.approx(5.5735, rel=1e-4)


def test_put_call_parity_without_dividends():
    spot = 100
    strike = 100
    maturity = 1
    rate = 0.05
    volatility = 0.20

    call_price = black_scholes_price("Call", spot, strike, maturity, rate, volatility)
    put_price = black_scholes_price("Put", spot, strike, maturity, rate, volatility)

    parity_left = call_price - put_price
    parity_right = spot - strike * 2.718281828459045 ** (-rate * maturity)

    assert parity_left == pytest.approx(parity_right, rel=1e-6)


def test_black_scholes_greeks_known_values():
    greeks = black_scholes_greeks(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
    )

    assert greeks["delta"] == pytest.approx(0.6368, rel=1e-4)
    assert greeks["gamma"] == pytest.approx(0.018762, rel=1e-4)
    assert greeks["vega_1pct"] == pytest.approx(0.3752, rel=1e-3)
    assert greeks["theta_annual"] == pytest.approx(-6.4140, rel=1e-3)
    assert greeks["rho_1pct"] == pytest.approx(0.5323, rel=1e-3)


def test_option_intrinsic_value():
    assert option_intrinsic_value("Call", spot=110, strike=100) == 10
    assert option_intrinsic_value("Call", spot=90, strike=100) == 0
    assert option_intrinsic_value("Put", spot=90, strike=100) == 10
    assert option_intrinsic_value("Put", spot=110, strike=100) == 0


def test_build_black_scholes_snapshot_outputs_core_fields():
    snapshot = build_black_scholes_snapshot(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        dividend_yield=0.0,
    )

    outputs = snapshot["outputs"]

    assert snapshot["inputs"]["option_type"] == "Call"
    assert outputs["price"] == pytest.approx(10.4506, rel=1e-4)
    assert outputs["intrinsic_value"] == 0
    assert outputs["time_value"] == pytest.approx(outputs["price"], rel=1e-6)
    assert "delta" in outputs
    assert DISCLAIMER in outputs["disclaimer"]


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        black_scholes_price("Call", 0, 100, 1, 0.05, 0.20)

    with pytest.raises(ValueError):
        black_scholes_price("Call", 100, 100, 0, 0.05, 0.20)

    with pytest.raises(ValueError):
        black_scholes_price("Call", 100, 100, 1, 0.05, 0)


def test_build_pricing_sensitivity_table_shape_and_columns():
    table = build_pricing_sensitivity_table(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
        spot_shocks=[0.0, 0.1],
        volatility_shocks=[0.0, 0.05],
    )

    assert table.shape[0] == 4
    assert list(table.columns) == [
        "scenario",
        "spot",
        "volatility",
        "price",
        "delta",
        "vega_1pct",
        "theta_daily",
    ]
    assert "Spot +0%, Vol +0 vol pts" in list(table["scenario"])


def test_generate_pricing_desk_interpretation_contains_key_terms():
    snapshot = build_black_scholes_snapshot(
        option_type="Call",
        spot=100,
        strike=100,
        maturity_years=1,
        risk_free_rate=0.05,
        volatility=0.20,
    )

    bullets = generate_pricing_desk_interpretation(snapshot)

    assert any("theoretical value" in bullet for bullet in bullets)
    assert any("Delta" in bullet for bullet in bullets)
    assert any("Vega" in bullet for bullet in bullets)
    assert any("not an executable market quote" in bullet for bullet in bullets)
