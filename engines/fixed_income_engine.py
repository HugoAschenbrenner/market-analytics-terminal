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
