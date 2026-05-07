"""
Fixed Income Risk Engine.

This module implements transparent fixed income analytics for a synthetic
bond portfolio.

Financial conventions:
- clean_price is quoted per 100 notional.
- coupon_rate and yield_to_maturity are decimals, e.g. 5% = 0.05.
- market_value = clean_price / 100 * notional.
- dirty_price = clean_price + accrued_interest_per_100.
- DV01 is positive and represents the approximate gain for a 1 bp fall in yield.
- P&L for a positive yield move is negative:
  estimated_pnl = -DV01 * yield_move_bps.

Important limitation:
This MVP uses transparent approximations. It is not a bank-grade bond pricing
or curve construction engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


REQUIRED_BOND_COLUMNS = [
    "bond_id",
    "issuer",
    "currency",
    "coupon_rate",
    "maturity_date",
    "issue_date",
    "frequency",
    "clean_price",
    "yield_to_maturity",
    "notional",
    "rating",
    "sector",
    "spread_bps",
    "curve_bucket",
]


@dataclass(frozen=True)
class PortfolioSummary:
    """Aggregated fixed income portfolio metrics."""

    total_market_value: float
    weighted_average_yield: float
    weighted_average_modified_duration: float
    weighted_average_convexity: float
    total_dv01: float
    number_of_bonds: int


def load_bond_data(path: str | Path = "data/sample_bonds.csv") -> pd.DataFrame:
    """Load and validate the bond dataset."""

    df = pd.read_csv(path)

    missing_columns = [col for col in REQUIRED_BOND_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    if df[REQUIRED_BOND_COLUMNS].isnull().any().any():
        raise ValueError("Bond dataset contains missing values in required columns.")

    return df


def _to_timestamp(value) -> pd.Timestamp:
    """Convert a date-like value to pandas Timestamp."""

    return pd.to_datetime(value)


def years_to_maturity(maturity_date, valuation_date: Optional[date] = None) -> float:
    """Calculate approximate years to maturity using ACT/365."""

    if valuation_date is None:
        valuation_date = date.today()

    maturity = _to_timestamp(maturity_date)
    valuation = pd.Timestamp(valuation_date)

    days = (maturity - valuation).days
    return max(days / 365.0, 0.0)


def calculate_accrued_interest_per_100(
    coupon_rate: float,
    frequency: int,
    issue_date,
    maturity_date,
    valuation_date: Optional[date] = None,
) -> float:
    """Approximate accrued interest per 100 notional.

    The function estimates the current coupon period using the issue date,
    coupon frequency, and valuation date.

    If the valuation date is before the issue date or after maturity, accrued
    interest is set to zero.

    This is a transparent approximation and does not handle every bond market
    day-count convention.
    """

    if valuation_date is None:
        valuation_date = date.today()

    issue = _to_timestamp(issue_date)
    maturity = _to_timestamp(maturity_date)
    valuation = pd.Timestamp(valuation_date)

    if valuation <= issue or valuation >= maturity:
        return 0.0

    months_per_coupon = int(12 / frequency)
    coupon_amount_per_100 = 100.0 * coupon_rate / frequency

    last_coupon = issue
    next_coupon = issue + pd.DateOffset(months=months_per_coupon)

    while next_coupon <= valuation and next_coupon < maturity:
        last_coupon = next_coupon
        next_coupon = next_coupon + pd.DateOffset(months=months_per_coupon)

    if next_coupon > maturity:
        next_coupon = maturity

    coupon_period_days = max((next_coupon - last_coupon).days, 1)
    elapsed_days = max((valuation - last_coupon).days, 0)

    accrual_fraction = min(elapsed_days / coupon_period_days, 1.0)

    return coupon_amount_per_100 * accrual_fraction


def generate_cashflow_times(years: float, frequency: int) -> np.ndarray:
    """Generate approximate cashflow times in years."""

    if years <= 0:
        return np.array([])

    number_of_periods = max(int(np.ceil(years * frequency)), 1)
    times = np.arange(1, number_of_periods + 1, dtype=float) / frequency

    # Adjust final cashflow to maturity if the regular schedule goes beyond it.
    times[-1] = years

    return times


def calculate_yield_implied_cashflows(
    coupon_rate: float,
    yield_to_maturity: float,
    years: float,
    frequency: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate cashflow times, cashflows, and present values per 100 notional."""

    times = generate_cashflow_times(years=years, frequency=frequency)

    if len(times) == 0:
        return times, np.array([]), np.array([])

    coupon_cashflow = 100.0 * coupon_rate / frequency
    cashflows = np.full(len(times), coupon_cashflow)
    cashflows[-1] += 100.0

    discount_base = 1.0 + yield_to_maturity / frequency
    discount_exponents = times * frequency

    present_values = cashflows / np.power(discount_base, discount_exponents)

    return times, cashflows, present_values


def calculate_macaulay_duration(
    coupon_rate: float,
    yield_to_maturity: float,
    years: float,
    frequency: int,
) -> float:
    """Calculate approximate Macaulay duration in years."""

    times, _, present_values = calculate_yield_implied_cashflows(
        coupon_rate=coupon_rate,
        yield_to_maturity=yield_to_maturity,
        years=years,
        frequency=frequency,
    )

    if len(times) == 0 or present_values.sum() <= 0:
        return 0.0

    return float(np.sum(times * present_values) / np.sum(present_values))


def calculate_modified_duration(
    macaulay_duration: float,
    yield_to_maturity: float,
    frequency: int,
) -> float:
    """Calculate modified duration from Macaulay duration."""

    denominator = 1.0 + yield_to_maturity / frequency
    if denominator <= 0:
        return np.nan

    return float(macaulay_duration / denominator)


def calculate_convexity(
    coupon_rate: float,
    yield_to_maturity: float,
    years: float,
    frequency: int,
) -> float:
    """Calculate approximate annualized convexity.

    This is a standard duration/convexity approximation using yield-implied
    cashflows and periodic compounding.
    """

    times, _, present_values = calculate_yield_implied_cashflows(
        coupon_rate=coupon_rate,
        yield_to_maturity=yield_to_maturity,
        years=years,
        frequency=frequency,
    )

    price_model = present_values.sum()

    if len(times) == 0 or price_model <= 0:
        return 0.0

    denominator = price_model * (1.0 + yield_to_maturity / frequency) ** 2
    convexity = np.sum(present_values * times * (times + 1.0 / frequency)) / denominator

    return float(convexity)


def calculate_market_value(clean_price: float, notional: float) -> float:
    """Calculate market value from clean price per 100 notional."""

    return float(clean_price / 100.0 * notional)


def calculate_dv01(modified_duration: float, market_value: float) -> float:
    """Calculate positive DV01.

    DV01 is defined here as the approximate gain for a 1 bp fall in yield.

    Formula:
    DV01 = modified_duration * market_value * 0.0001
    """

    return float(modified_duration * market_value * 0.0001)


def estimate_pnl_from_yield_move(dv01: float, yield_move_bps: float) -> float:
    """Estimate P&L from a yield move in basis points.

    Positive yield move implies negative P&L.
    """

    return float(-dv01 * yield_move_bps)


def calculate_bond_risk_metrics(
    bonds: pd.DataFrame,
    valuation_date: Optional[date] = None,
) -> pd.DataFrame:
    """Calculate bond-level fixed income risk metrics."""

    if valuation_date is None:
        valuation_date = date.today()

    df = bonds.copy()

    years = []
    accrued_interest = []
    dirty_prices = []
    market_values = []
    macaulay_durations = []
    modified_durations = []
    convexities = []
    dv01s = []

    for _, row in df.iterrows():
        years_i = years_to_maturity(
            maturity_date=row["maturity_date"],
            valuation_date=valuation_date,
        )

        accrued_i = calculate_accrued_interest_per_100(
            coupon_rate=float(row["coupon_rate"]),
            frequency=int(row["frequency"]),
            issue_date=row["issue_date"],
            maturity_date=row["maturity_date"],
            valuation_date=valuation_date,
        )

        dirty_price_i = float(row["clean_price"]) + accrued_i

        market_value_i = calculate_market_value(
            clean_price=float(row["clean_price"]),
            notional=float(row["notional"]),
        )

        mac_dur_i = calculate_macaulay_duration(
            coupon_rate=float(row["coupon_rate"]),
            yield_to_maturity=float(row["yield_to_maturity"]),
            years=years_i,
            frequency=int(row["frequency"]),
        )

        mod_dur_i = calculate_modified_duration(
            macaulay_duration=mac_dur_i,
            yield_to_maturity=float(row["yield_to_maturity"]),
            frequency=int(row["frequency"]),
        )

        convexity_i = calculate_convexity(
            coupon_rate=float(row["coupon_rate"]),
            yield_to_maturity=float(row["yield_to_maturity"]),
            years=years_i,
            frequency=int(row["frequency"]),
        )

        dv01_i = calculate_dv01(
            modified_duration=mod_dur_i,
            market_value=market_value_i,
        )

        years.append(years_i)
        accrued_interest.append(accrued_i)
        dirty_prices.append(dirty_price_i)
        market_values.append(market_value_i)
        macaulay_durations.append(mac_dur_i)
        modified_durations.append(mod_dur_i)
        convexities.append(convexity_i)
        dv01s.append(dv01_i)

    df["years_to_maturity"] = years
    df["accrued_interest_per_100"] = accrued_interest
    df["dirty_price"] = dirty_prices
    df["market_value"] = market_values
    df["macaulay_duration"] = macaulay_durations
    df["modified_duration"] = modified_durations
    df["convexity"] = convexities
    df["dv01"] = dv01s

    return df


def summarize_portfolio(risk_df: pd.DataFrame) -> PortfolioSummary:
    """Calculate portfolio-level summary metrics."""

    total_market_value = float(risk_df["market_value"].sum())

    if total_market_value <= 0:
        raise ValueError("Total market value must be positive.")

    weights = risk_df["market_value"] / total_market_value

    weighted_average_yield = float(np.sum(weights * risk_df["yield_to_maturity"]))
    weighted_average_modified_duration = float(np.sum(weights * risk_df["modified_duration"]))
    weighted_average_convexity = float(np.sum(weights * risk_df["convexity"]))
    total_dv01 = float(risk_df["dv01"].sum())

    return PortfolioSummary(
        total_market_value=total_market_value,
        weighted_average_yield=weighted_average_yield,
        weighted_average_modified_duration=weighted_average_modified_duration,
        weighted_average_convexity=weighted_average_convexity,
        total_dv01=total_dv01,
        number_of_bonds=int(len(risk_df)),
    )


def portfolio_summary_to_dict(summary: PortfolioSummary) -> dict:
    """Convert PortfolioSummary dataclass to dictionary."""

    return {
        "total_market_value": summary.total_market_value,
        "weighted_average_yield": summary.weighted_average_yield,
        "weighted_average_modified_duration": summary.weighted_average_modified_duration,
        "weighted_average_convexity": summary.weighted_average_convexity,
        "total_dv01": summary.total_dv01,
        "number_of_bonds": summary.number_of_bonds,
    }


# ---------------------------------------------------------------------------
# Step 6: DV01 buckets, scenario P&L, commentary, and hedge approximation
# ---------------------------------------------------------------------------

def calculate_dv01_by_bucket(risk_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate DV01 and market value by curve bucket.

    Returns a table with:
    - curve_bucket
    - market_value
    - dv01
    - pct_total_dv01

    Financial convention:
    DV01 is positive and represents the approximate gain for a 1 bp fall in yield.
    """

    required_columns = {"curve_bucket", "market_value", "dv01"}
    missing = required_columns - set(risk_df.columns)
    if missing:
        raise ValueError(f"Missing required columns for DV01 bucket calculation: {missing}")

    bucket_df = (
        risk_df.groupby("curve_bucket", as_index=False)
        .agg(
            market_value=("market_value", "sum"),
            dv01=("dv01", "sum"),
        )
        .sort_values("curve_bucket")
    )

    total_dv01 = float(bucket_df["dv01"].sum())

    if total_dv01 <= 0:
        bucket_df["pct_total_dv01"] = 0.0
    else:
        bucket_df["pct_total_dv01"] = bucket_df["dv01"] / total_dv01

    return bucket_df


def estimate_pnl_with_duration_convexity(
    modified_duration: float,
    convexity: float,
    market_value: float,
    yield_move_bps: float,
) -> dict:
    """Estimate P&L from a yield move using duration and convexity.

    Formula:
    price_change = -modified_duration * market_value * delta_y
                   + 0.5 * convexity * market_value * delta_y^2

    where delta_y is in decimal rate terms.

    Interpretation:
    - Positive yield move usually creates negative P&L.
    - Positive convexity partially offsets losses for large moves.
    """

    delta_y = yield_move_bps / 10_000.0

    duration_pnl = -modified_duration * market_value * delta_y
    convexity_pnl = 0.5 * convexity * market_value * (delta_y**2)
    estimated_pnl = duration_pnl + convexity_pnl

    return {
        "duration_pnl": float(duration_pnl),
        "convexity_pnl": float(convexity_pnl),
        "estimated_pnl": float(estimated_pnl),
    }


def _bucket_shock_bps_for_scenario(curve_bucket: str, scenario_name: str) -> float:
    """Map curve bucket to shock in bps for predefined rate scenarios."""

    if scenario_name == "+25 bps parallel":
        return 25.0

    if scenario_name == "+50 bps parallel":
        return 50.0

    if scenario_name == "-25 bps parallel":
        return -25.0

    if scenario_name == "2s10s steepener":
        shock_map = {
            "0-2Y": 10.0,
            "2-5Y": 15.0,
            "5-10Y": 25.0,
            "10Y+": 35.0,
        }
        return shock_map.get(curve_bucket, 25.0)

    if scenario_name == "2s10s flattener":
        shock_map = {
            "0-2Y": 35.0,
            "2-5Y": 25.0,
            "5-10Y": 15.0,
            "10Y+": 10.0,
        }
        return shock_map.get(curve_bucket, 25.0)

    raise ValueError(f"Unknown scenario name: {scenario_name}")


def calculate_scenario_pnl(risk_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate desk-style scenario P&L for the fixed income portfolio.

    Scenarios:
    - +25 bps parallel rates shock
    - +50 bps parallel rates shock
    - -25 bps parallel rates shock
    - 2s10s steepener proxy
    - 2s10s flattener proxy
    - credit spread +50 bps proxy

    Spread shock note:
    The spread shock uses modified duration as a proxy for spread duration.
    This is transparent and useful for demonstration, but not a substitute for
    issuer-specific spread duration or full curve analytics.
    """

    required_columns = {
        "bond_id",
        "curve_bucket",
        "market_value",
        "modified_duration",
        "convexity",
        "dv01",
    }

    missing = required_columns - set(risk_df.columns)
    if missing:
        raise ValueError(f"Missing required columns for scenario P&L: {missing}")

    scenario_names = [
        "+25 bps parallel",
        "+50 bps parallel",
        "-25 bps parallel",
        "2s10s steepener",
        "2s10s flattener",
    ]

    scenario_rows = []

    for scenario_name in scenario_names:
        total_duration_pnl = 0.0
        total_convexity_pnl = 0.0
        total_estimated_pnl = 0.0

        for _, row in risk_df.iterrows():
            shock_bps = _bucket_shock_bps_for_scenario(
                curve_bucket=row["curve_bucket"],
                scenario_name=scenario_name,
            )

            pnl_components = estimate_pnl_with_duration_convexity(
                modified_duration=float(row["modified_duration"]),
                convexity=float(row["convexity"]),
                market_value=float(row["market_value"]),
                yield_move_bps=shock_bps,
            )

            total_duration_pnl += pnl_components["duration_pnl"]
            total_convexity_pnl += pnl_components["convexity_pnl"]
            total_estimated_pnl += pnl_components["estimated_pnl"]

        scenario_rows.append(
            {
                "scenario_name": scenario_name,
                "risk_factor": "rates",
                "shock_description": _describe_fixed_income_scenario(scenario_name),
                "duration_pnl": total_duration_pnl,
                "convexity_pnl": total_convexity_pnl,
                "estimated_pnl": total_estimated_pnl,
                "main_driver": "Rates duration / curve exposure",
            }
        )

    spread_shock_bps = 50.0
    spread_pnl = float(-(risk_df["dv01"] * spread_shock_bps).sum())

    scenario_rows.append(
        {
            "scenario_name": "Credit spread +50 bps",
            "risk_factor": "credit",
            "shock_description": "All credit spreads widen by 50 bps. Uses modified duration as spread-duration proxy.",
            "duration_pnl": spread_pnl,
            "convexity_pnl": 0.0,
            "estimated_pnl": spread_pnl,
            "main_driver": "Credit spread duration proxy",
        }
    )

    return pd.DataFrame(scenario_rows)


def _describe_fixed_income_scenario(scenario_name: str) -> str:
    """Return a readable description for fixed income scenario labels."""

    descriptions = {
        "+25 bps parallel": "All yield buckets increase by 25 bps.",
        "+50 bps parallel": "All yield buckets increase by 50 bps.",
        "-25 bps parallel": "All yield buckets decrease by 25 bps.",
        "2s10s steepener": "Long-end rates rise more than front-end rates.",
        "2s10s flattener": "Front-end rates rise more than long-end rates.",
    }

    return descriptions.get(scenario_name, scenario_name)


def identify_worst_scenario(scenario_df: pd.DataFrame) -> dict:
    """Identify the scenario with the largest estimated loss."""

    if scenario_df.empty:
        raise ValueError("Scenario DataFrame is empty.")

    worst_row = scenario_df.loc[scenario_df["estimated_pnl"].idxmin()]
    return worst_row.to_dict()


def generate_fixed_income_commentary(
    risk_df: pd.DataFrame,
    bucket_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
) -> list[str]:
    """Generate concise desk-style commentary for the fixed income module."""

    comments = []

    if bucket_df.empty:
        return ["No DV01 bucket data available."]

    largest_bucket = bucket_df.loc[bucket_df["dv01"].idxmax()]
    largest_bucket_name = largest_bucket["curve_bucket"]
    largest_bucket_pct = float(largest_bucket["pct_total_dv01"])

    if largest_bucket_name in ["10Y+", "5-10Y"]:
        concentration_label = "long-end"
    elif largest_bucket_name == "0-2Y":
        concentration_label = "front-end"
    else:
        concentration_label = "belly"

    comments.append(
        f"DV01 is concentrated in the {largest_bucket_name} bucket "
        f"({largest_bucket_pct:.1%} of total DV01), indicating mainly {concentration_label} rate exposure."
    )

    worst_scenario = identify_worst_scenario(scenario_df)
    comments.append(
        f"The largest estimated loss comes from '{worst_scenario['scenario_name']}' "
        f"with estimated P&L of {worst_scenario['estimated_pnl']:,.0f}."
    )

    if largest_bucket_pct >= 0.50:
        comments.append(
            "Risk is materially concentrated in one maturity bucket. A hedge or risk reduction should focus first on that bucket."
        )
    else:
        comments.append(
            "DV01 is relatively diversified across curve buckets, but scenario P&L should still be monitored under non-parallel curve moves."
        )

    comments.append(
        "Scenario P&L uses duration/convexity approximations and should be treated as a desk analytics proxy, not a full revaluation engine."
    )

    return comments


def calculate_hedge_units(portfolio_dv01: float, hedge_instrument_dv01: float) -> float:
    """Calculate approximate hedge units from DV01.

    Formula:
    hedge_units = portfolio_dv01 / hedge_instrument_dv01

    This is an approximation and not an execution recommendation.
    """

    if hedge_instrument_dv01 <= 0:
        raise ValueError("Hedge instrument DV01 must be positive.")

    return float(portfolio_dv01 / hedge_instrument_dv01)
