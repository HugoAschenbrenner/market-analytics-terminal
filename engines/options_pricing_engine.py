"""
Black-Scholes-Merton option pricing engine.

This module adds transparent vanilla European option pricing and Greeks for
educational/demo use. It is not a volatility-surface model, American option
model, market-data calibration layer, execution system, or bank-grade risk
engine.

Conventions:
- volatility, rates, dividend yield are decimals, not percentages
- maturity is expressed in years
- vega and rho are returned per 1 percentage point move
- theta is returned both annualized and daily
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import erf, exp, log, pi, sqrt
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


DISCLAIMER = (
    "Black-Scholes-Merton outputs are theoretical European option pricing estimates "
    "for educational/demo use only. They assume constant volatility, continuous rates, "
    "continuous dividend yield, frictionless markets, and European exercise. They are "
    "not executable quotes, investment advice, or bank-grade pricing."
)

SUPPORTED_OPTION_TYPES = ["Call", "Put"]


@dataclass(frozen=True)
class BlackScholesInputs:
    option_type: str
    spot: float
    strike: float
    maturity_years: float
    risk_free_rate: float
    volatility: float
    dividend_yield: float = 0.0


@dataclass(frozen=True)
class BlackScholesOutputs:
    option_type: str
    price: float
    intrinsic_value: float
    time_value: float
    d1: float
    d2: float
    delta: float
    gamma: float
    vega_1pct: float
    theta_annual: float
    theta_daily: float
    rho_1pct: float
    moneyness_pct: float
    disclaimer: str


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return exp(-0.5 * x * x) / sqrt(2.0 * pi)


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def normalize_option_type(option_type: str) -> str:
    """Normalize option type labels."""
    if not option_type:
        raise ValueError("option_type cannot be empty.")

    cleaned = str(option_type).strip().lower()

    if cleaned == "call":
        return "Call"

    if cleaned == "put":
        return "Put"

    raise ValueError("option_type must be 'Call' or 'Put'.")


def validate_black_scholes_inputs(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> BlackScholesInputs:
    """Validate and normalize Black-Scholes-Merton inputs."""
    normalized_option_type = normalize_option_type(option_type)

    spot = float(spot)
    strike = float(strike)
    maturity_years = float(maturity_years)
    risk_free_rate = float(risk_free_rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)

    if spot <= 0:
        raise ValueError("spot must be strictly positive.")

    if strike <= 0:
        raise ValueError("strike must be strictly positive.")

    if maturity_years <= 0:
        raise ValueError("maturity_years must be strictly positive.")

    if volatility <= 0:
        raise ValueError("volatility must be strictly positive.")

    return BlackScholesInputs(
        option_type=normalized_option_type,
        spot=spot,
        strike=strike,
        maturity_years=maturity_years,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
    )


def calculate_d1_d2(
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> Dict[str, float]:
    """Calculate Black-Scholes-Merton d1 and d2."""
    inputs = validate_black_scholes_inputs(
        option_type="Call",
        spot=spot,
        strike=strike,
        maturity_years=maturity_years,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
    )

    sqrt_t = sqrt(inputs.maturity_years)

    d1 = (
        log(inputs.spot / inputs.strike)
        + (
            inputs.risk_free_rate
            - inputs.dividend_yield
            + 0.5 * inputs.volatility * inputs.volatility
        )
        * inputs.maturity_years
    ) / (inputs.volatility * sqrt_t)

    d2 = d1 - inputs.volatility * sqrt_t

    return {"d1": d1, "d2": d2}


def option_intrinsic_value(option_type: str, spot: float, strike: float) -> float:
    """Calculate vanilla option intrinsic value."""
    normalized_option_type = normalize_option_type(option_type)
    spot = float(spot)
    strike = float(strike)

    if normalized_option_type == "Call":
        return max(spot - strike, 0.0)

    return max(strike - spot, 0.0)


def black_scholes_price(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> float:
    """Calculate theoretical European option value under Black-Scholes-Merton."""
    inputs = validate_black_scholes_inputs(
        option_type,
        spot,
        strike,
        maturity_years,
        risk_free_rate,
        volatility,
        dividend_yield,
    )

    d_values = calculate_d1_d2(
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        inputs.dividend_yield,
    )

    d1 = d_values["d1"]
    d2 = d_values["d2"]

    discounted_spot = inputs.spot * exp(-inputs.dividend_yield * inputs.maturity_years)
    discounted_strike = inputs.strike * exp(-inputs.risk_free_rate * inputs.maturity_years)

    if inputs.option_type == "Call":
        price = discounted_spot * norm_cdf(d1) - discounted_strike * norm_cdf(d2)
    else:
        price = discounted_strike * norm_cdf(-d2) - discounted_spot * norm_cdf(-d1)

    return round(float(price), 10)


def black_scholes_greeks(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> Dict[str, float]:
    """
    Calculate Black-Scholes-Merton Greeks.

    Vega and rho are scaled per 1 percentage point move.
    Theta is returned annualized and daily.
    """
    inputs = validate_black_scholes_inputs(
        option_type,
        spot,
        strike,
        maturity_years,
        risk_free_rate,
        volatility,
        dividend_yield,
    )

    d_values = calculate_d1_d2(
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        inputs.dividend_yield,
    )

    d1 = d_values["d1"]
    d2 = d_values["d2"]
    sqrt_t = sqrt(inputs.maturity_years)

    dividend_discount = exp(-inputs.dividend_yield * inputs.maturity_years)
    rate_discount = exp(-inputs.risk_free_rate * inputs.maturity_years)

    gamma = (
        dividend_discount
        * norm_pdf(d1)
        / (inputs.spot * inputs.volatility * sqrt_t)
    )

    vega_1pct = (
        inputs.spot
        * dividend_discount
        * norm_pdf(d1)
        * sqrt_t
        / 100.0
    )

    first_theta_term = -(
        inputs.spot
        * dividend_discount
        * norm_pdf(d1)
        * inputs.volatility
        / (2.0 * sqrt_t)
    )

    if inputs.option_type == "Call":
        delta = dividend_discount * norm_cdf(d1)
        theta_annual = (
            first_theta_term
            - inputs.risk_free_rate * inputs.strike * rate_discount * norm_cdf(d2)
            + inputs.dividend_yield * inputs.spot * dividend_discount * norm_cdf(d1)
        )
        rho_1pct = (
            inputs.strike
            * inputs.maturity_years
            * rate_discount
            * norm_cdf(d2)
            / 100.0
        )

    else:
        delta = dividend_discount * (norm_cdf(d1) - 1.0)
        theta_annual = (
            first_theta_term
            + inputs.risk_free_rate * inputs.strike * rate_discount * norm_cdf(-d2)
            - inputs.dividend_yield * inputs.spot * dividend_discount * norm_cdf(-d1)
        )
        rho_1pct = -(
            inputs.strike
            * inputs.maturity_years
            * rate_discount
            * norm_cdf(-d2)
            / 100.0
        )

    return {
        "delta": round(float(delta), 10),
        "gamma": round(float(gamma), 10),
        "vega_1pct": round(float(vega_1pct), 10),
        "theta_annual": round(float(theta_annual), 10),
        "theta_daily": round(float(theta_annual / 365.0), 10),
        "rho_1pct": round(float(rho_1pct), 10),
    }


def build_black_scholes_snapshot(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> Dict[str, Any]:
    """Build full Black-Scholes-Merton pricing payload."""
    inputs = validate_black_scholes_inputs(
        option_type,
        spot,
        strike,
        maturity_years,
        risk_free_rate,
        volatility,
        dividend_yield,
    )

    d_values = calculate_d1_d2(
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        inputs.dividend_yield,
    )

    price = black_scholes_price(
        inputs.option_type,
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        inputs.dividend_yield,
    )

    greeks = black_scholes_greeks(
        inputs.option_type,
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        inputs.dividend_yield,
    )

    intrinsic = option_intrinsic_value(inputs.option_type, inputs.spot, inputs.strike)
    time_value = max(price - intrinsic, 0.0)
    moneyness_pct = (inputs.spot / inputs.strike - 1.0) * 100.0

    output = BlackScholesOutputs(
        option_type=inputs.option_type,
        price=round(price, 6),
        intrinsic_value=round(intrinsic, 6),
        time_value=round(time_value, 6),
        d1=round(d_values["d1"], 6),
        d2=round(d_values["d2"], 6),
        delta=round(greeks["delta"], 6),
        gamma=round(greeks["gamma"], 6),
        vega_1pct=round(greeks["vega_1pct"], 6),
        theta_annual=round(greeks["theta_annual"], 6),
        theta_daily=round(greeks["theta_daily"], 6),
        rho_1pct=round(greeks["rho_1pct"], 6),
        moneyness_pct=round(moneyness_pct, 4),
        disclaimer=DISCLAIMER,
    )

    return {
        "inputs": asdict(inputs),
        "outputs": asdict(output),
    }


def build_pricing_sensitivity_table(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    spot_shocks: Optional[Iterable[float]] = None,
    volatility_shocks: Optional[Iterable[float]] = None,
) -> pd.DataFrame:
    """
    Build spot/volatility sensitivity table.

    spot_shocks are relative moves, e.g. 0.10 = +10%.
    volatility_shocks are absolute volatility moves, e.g. 0.05 = +5 vol points.
    """
    spot_moves = list(spot_shocks if spot_shocks is not None else [-0.2, -0.1, 0.0, 0.1, 0.2])
    vol_moves = list(volatility_shocks if volatility_shocks is not None else [-0.1, -0.05, 0.0, 0.05, 0.1])

    rows: List[Dict[str, Any]] = []

    for spot_move in spot_moves:
        shocked_spot = float(spot) * (1.0 + float(spot_move))

        for vol_move in vol_moves:
            shocked_vol = max(float(volatility) + float(vol_move), 0.0001)

            snapshot = build_black_scholes_snapshot(
                option_type=option_type,
                spot=shocked_spot,
                strike=strike,
                maturity_years=maturity_years,
                risk_free_rate=risk_free_rate,
                volatility=shocked_vol,
                dividend_yield=dividend_yield,
            )

            outputs = snapshot["outputs"]

            rows.append(
                {
                    "scenario": f"Spot {spot_move:+.0%}, Vol {vol_move * 100:+.0f} vol pts",
                    "spot": round(shocked_spot, 6),
                    "volatility": round(shocked_vol, 6),
                    "price": outputs["price"],
                    "delta": outputs["delta"],
                    "vega_1pct": outputs["vega_1pct"],
                    "theta_daily": outputs["theta_daily"],
                }
            )

    return pd.DataFrame(rows)


def generate_pricing_desk_interpretation(snapshot: Dict[str, Any]) -> List[str]:
    """Generate desk-style interpretation bullets from BSM pricing outputs."""
    inputs = snapshot["inputs"]
    outputs = snapshot["outputs"]

    option_type = inputs["option_type"]
    volatility = inputs["volatility"]
    maturity = inputs["maturity_years"]

    bullets = [
        f"The {option_type.lower()} theoretical value is {outputs['price']:.2f} under Black-Scholes-Merton assumptions.",
        f"Intrinsic value is {outputs['intrinsic_value']:.2f}; time value is {outputs['time_value']:.2f}.",
        f"Delta is {outputs['delta']:.3f}, showing first-order sensitivity to the underlying.",
        f"Vega is {outputs['vega_1pct']:.3f} per 1 vol point, so the option is sensitive to implied volatility assumptions.",
    ]

    if outputs["theta_daily"] < 0:
        bullets.append(f"Theta is negative at {outputs['theta_daily']:.4f} per day: time decay is a cost to the holder.")
    else:
        bullets.append(f"Theta is positive at {outputs['theta_daily']:.4f} per day: time decay benefits the position.")

    if maturity < 0.25:
        bullets.append("Short maturity means gamma/theta effects can dominate small spot moves.")
    elif volatility > 0.35:
        bullets.append("High volatility assumption increases option time value and vega exposure.")
    else:
        bullets.append("Pricing is mainly driven by spot, strike, volatility, rates, dividends, and time to maturity.")

    bullets.append("This is theoretical European pricing, not an executable market quote.")

    return bullets


SUPPORTED_BSM_CURVE_VARIABLES = ["Spot", "Strike", "Maturity", "Volatility", "Rate"]


def normalize_bsm_curve_variable(variable: str) -> str:
    """Normalize BSM curve variable labels for sensitivity charts."""
    cleaned = str(variable).strip().lower().replace("_", " ").replace("-", " ")

    mapping = {
        "spot": "Spot",
        "stock": "Spot",
        "stock price": "Spot",
        "strike": "Strike",
        "strike price": "Strike",
        "maturity": "Maturity",
        "time": "Maturity",
        "time to maturity": "Maturity",
        "expiry": "Maturity",
        "vol": "Volatility",
        "volatility": "Volatility",
        "implied volatility": "Volatility",
        "rate": "Rate",
        "risk free rate": "Rate",
        "risk-free rate": "Rate",
        "r": "Rate",
    }

    if cleaned not in mapping:
        raise ValueError(
            "variable must be one of: Spot, Strike, Maturity, Volatility, Rate."
        )

    return mapping[cleaned]


def _linear_space(start: float, stop: float, points: int) -> list[float]:
    """Small dependency-free linspace helper."""
    points = int(points)

    if points < 3:
        raise ValueError("points must be at least 3.")

    if stop <= start:
        raise ValueError("stop must be greater than start.")

    step = (stop - start) / float(points - 1)
    return [start + idx * step for idx in range(points)]


def _build_bsm_curve_axis(
    variable: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    points: int = 81,
) -> list[float]:
    """Build a sensible axis range for an interactive BSM sensitivity chart."""
    normalized_variable = normalize_bsm_curve_variable(variable)

    if normalized_variable == "Spot":
        return _linear_space(max(spot * 0.50, 0.01), spot * 1.50, points)

    if normalized_variable == "Strike":
        return _linear_space(max(strike * 0.50, 0.01), strike * 1.50, points)

    if normalized_variable == "Maturity":
        upper = max(maturity_years * 2.0, maturity_years + 1.0, 0.25)
        return _linear_space(0.01, upper, points)

    if normalized_variable == "Volatility":
        lower = max(volatility * 0.25, 0.01)
        upper = max(volatility * 2.0, volatility + 0.30, 0.10)
        return _linear_space(lower, upper, points)

    if normalized_variable == "Rate":
        lower = max(risk_free_rate - 0.05, -0.05)
        upper = min(risk_free_rate + 0.05, 0.25)

        if upper <= lower:
            upper = lower + 0.05

        return _linear_space(lower, upper, points)

    raise ValueError("Unsupported BSM curve variable.")


def build_bsm_sensitivity_curve(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    variable: str = "Spot",
    points: int = 81,
) -> pd.DataFrame:
    """
    Build an interactive Black-Scholes-Merton sensitivity curve.

    The output is designed for Streamlit charts:
    - price curve
    - first-order Greeks across the selected axis
    - tangent-line / slope visualizations
    """
    inputs = validate_black_scholes_inputs(
        option_type=option_type,
        spot=spot,
        strike=strike,
        maturity_years=maturity_years,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
    )

    normalized_variable = normalize_bsm_curve_variable(variable)

    axis_values = _build_bsm_curve_axis(
        normalized_variable,
        inputs.spot,
        inputs.strike,
        inputs.maturity_years,
        inputs.risk_free_rate,
        inputs.volatility,
        points=points,
    )

    rows: list[dict[str, Any]] = []

    for axis_value in axis_values:
        shocked_spot = inputs.spot
        shocked_strike = inputs.strike
        shocked_maturity = inputs.maturity_years
        shocked_rate = inputs.risk_free_rate
        shocked_volatility = inputs.volatility

        if normalized_variable == "Spot":
            shocked_spot = axis_value
        elif normalized_variable == "Strike":
            shocked_strike = axis_value
        elif normalized_variable == "Maturity":
            shocked_maturity = axis_value
        elif normalized_variable == "Volatility":
            shocked_volatility = axis_value
        elif normalized_variable == "Rate":
            shocked_rate = axis_value

        price = black_scholes_price(
            option_type=inputs.option_type,
            spot=shocked_spot,
            strike=shocked_strike,
            maturity_years=shocked_maturity,
            risk_free_rate=shocked_rate,
            volatility=shocked_volatility,
            dividend_yield=inputs.dividend_yield,
        )

        greeks = black_scholes_greeks(
            option_type=inputs.option_type,
            spot=shocked_spot,
            strike=shocked_strike,
            maturity_years=shocked_maturity,
            risk_free_rate=shocked_rate,
            volatility=shocked_volatility,
            dividend_yield=inputs.dividend_yield,
        )

        rows.append(
            {
                "axis": normalized_variable,
                "axis_value": round(float(axis_value), 8),
                "price": round(float(price), 8),
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "vega_1pct": greeks["vega_1pct"],
                "theta_daily": greeks["theta_daily"],
                "rho_1pct": greeks["rho_1pct"],
            }
        )

    return pd.DataFrame(rows)


def estimate_local_curve_slope(
    curve_df: pd.DataFrame,
    x_col: str = "axis_value",
    y_col: str = "price",
    selected_x: Optional[float] = None,
) -> Dict[str, float]:
    """
    Estimate local slope around the selected x-value using neighboring points.

    This is used to explain Greeks visually as local sensitivities.
    """
    required_cols = {x_col, y_col}

    if not required_cols.issubset(curve_df.columns):
        raise ValueError(f"curve_df must contain columns: {sorted(required_cols)}")

    if len(curve_df) < 3:
        raise ValueError("curve_df must contain at least three rows.")

    df = curve_df[[x_col, y_col]].dropna().sort_values(x_col).reset_index(drop=True)

    if df.empty or len(df) < 3:
        raise ValueError("curve_df must contain at least three valid numeric rows.")

    target_x = float(selected_x) if selected_x is not None else float(df[x_col].median())

    nearest_idx = int((df[x_col] - target_x).abs().idxmin())

    if nearest_idx == 0:
        left_idx, right_idx = 0, 1
    elif nearest_idx == len(df) - 1:
        left_idx, right_idx = len(df) - 2, len(df) - 1
    else:
        left_idx, right_idx = nearest_idx - 1, nearest_idx + 1

    x_left = float(df.loc[left_idx, x_col])
    x_right = float(df.loc[right_idx, x_col])
    y_left = float(df.loc[left_idx, y_col])
    y_right = float(df.loc[right_idx, y_col])

    if x_right == x_left:
        raise ValueError("Cannot estimate slope with duplicate x values.")

    slope = (y_right - y_left) / (x_right - x_left)

    anchor_x = float(df.loc[nearest_idx, x_col])
    anchor_y = float(df.loc[nearest_idx, y_col])

    return {
        "anchor_x": round(anchor_x, 8),
        "anchor_y": round(anchor_y, 8),
        "slope": round(float(slope), 8),
    }


def build_local_tangent_line(
    curve_df: pd.DataFrame,
    x_col: str = "axis_value",
    y_col: str = "price",
    selected_x: Optional[float] = None,
    width_fraction: float = 0.18,
) -> pd.DataFrame:
    """
    Build tangent-line data around a selected point on a curve.

    Returns a small dataframe with the same x-axis and a tangent value.
    """
    slope_payload = estimate_local_curve_slope(
        curve_df=curve_df,
        x_col=x_col,
        y_col=y_col,
        selected_x=selected_x,
    )

    df = curve_df[[x_col, y_col]].dropna().sort_values(x_col).reset_index(drop=True)

    x_min = float(df[x_col].min())
    x_max = float(df[x_col].max())
    span = x_max - x_min
    half_width = max(span * float(width_fraction), span / max(len(df), 1))

    anchor_x = slope_payload["anchor_x"]
    anchor_y = slope_payload["anchor_y"]
    slope = slope_payload["slope"]

    tangent_x_values = [
        max(x_min, anchor_x - half_width),
        anchor_x,
        min(x_max, anchor_x + half_width),
    ]

    rows = []

    for x_value in tangent_x_values:
        tangent_value = anchor_y + slope * (x_value - anchor_x)
        rows.append(
            {
                x_col: round(float(x_value), 8),
                "tangent_value": round(float(tangent_value), 8),
                "anchor_x": anchor_x,
                "anchor_y": anchor_y,
                "local_slope": slope,
            }
        )

    return pd.DataFrame(rows)


def build_bsm_interactive_explorer_payload(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    points: int = 81,
) -> Dict[str, Any]:
    """
    Build all data needed for an interactive BSM / Greeks explorer.

    This powers charts replacing static pricing tables:
    - price vs spot / strike / maturity / volatility / rate
    - Greeks curves
    - local tangent line for price vs spot
    """
    snapshot = build_black_scholes_snapshot(
        option_type=option_type,
        spot=spot,
        strike=strike,
        maturity_years=maturity_years,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
    )

    curves = {
        variable: build_bsm_sensitivity_curve(
            option_type=option_type,
            spot=spot,
            strike=strike,
            maturity_years=maturity_years,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            dividend_yield=dividend_yield,
            variable=variable,
            points=points,
        )
        for variable in SUPPORTED_BSM_CURVE_VARIABLES
    }

    spot_tangent = build_local_tangent_line(
        curves["Spot"],
        x_col="axis_value",
        y_col="price",
        selected_x=spot,
    )

    return {
        "snapshot": snapshot,
        "curves": curves,
        "spot_price_tangent": spot_tangent,
        "disclaimer": DISCLAIMER,
    }
