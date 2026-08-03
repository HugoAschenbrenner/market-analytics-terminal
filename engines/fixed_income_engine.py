"""
Fixed Income Risk Engine.

This module implements transparent fixed income analytics for a synthetic
bond portfolio.

Financial conventions:
- clean_price is quoted per 100 notional.
- coupon_rate and yield_to_maturity are decimals, e.g. 5% = 0.05.
- clean_market_value = clean_price / 100 * notional in local currency.
- full_market_value = dirty_price / 100 * notional in local currency.
- market_value is a backward-compatible alias for full_market_value.
- portfolio aggregation requires an explicit base currency and FX-to-base rates.
- dirty_price = clean_price + accrued_interest_per_100.
- DV01 uses full_market_value and is positive under the project convention.
- DV01 represents the approximate gain for a 1 bp fall in yield.
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
    """Fixed-income portfolio metrics expressed in one base currency."""

    base_currency: str
    currencies: tuple[str, ...]
    total_clean_market_value: float
    total_full_market_value: float
    total_accrued_interest_amount: float
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


def calculate_value_from_price_per_100(
    price_per_100: float,
    notional: float,
) -> float:
    """Convert a quoted price per 100 into a monetary value."""
    price = float(price_per_100)
    face = float(notional)

    if not np.isfinite(price):
        raise ValueError("Price per 100 must be finite.")
    if not np.isfinite(face) or face < 0:
        raise ValueError("Notional must be finite and non-negative.")

    return float(price / 100.0 * face)


def calculate_market_value(
    clean_price: float,
    notional: float,
) -> float:
    """
    Backward-compatible clean quoted market value helper.

    Bond risk analytics separately calculate clean and full values. DV01 and
    scenario P&L use full value, not this clean quoted value.
    """
    return calculate_value_from_price_per_100(
        price_per_100=clean_price,
        notional=notional,
    )


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
    """
    Calculate bond-level risk with separate clean and full economic values.

    clean_market_value is a quoted-price reporting measure.
    full_market_value includes accrued interest and is used for DV01 and
    duration/convexity scenario P&L. market_value remains an explicit
    backward-compatible alias for full_market_value.
    """
    if valuation_date is None:
        valuation_date = date.today()

    df = bonds.copy()
    years: list[float] = []
    accrued_interest: list[float] = []
    dirty_prices: list[float] = []
    clean_market_values: list[float] = []
    full_market_values: list[float] = []
    accrued_interest_amounts: list[float] = []
    macaulay_durations: list[float] = []
    modified_durations: list[float] = []
    convexities: list[float] = []
    dv01s: list[float] = []

    for _, row in df.iterrows():
        notional_i = float(row["notional"])
        clean_price_i = float(row["clean_price"])
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
        dirty_price_i = clean_price_i + accrued_i

        clean_market_value_i = calculate_value_from_price_per_100(
            price_per_100=clean_price_i,
            notional=notional_i,
        )
        full_market_value_i = calculate_value_from_price_per_100(
            price_per_100=dirty_price_i,
            notional=notional_i,
        )
        accrued_interest_amount_i = (
            full_market_value_i - clean_market_value_i
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
            market_value=full_market_value_i,
        )

        years.append(years_i)
        accrued_interest.append(accrued_i)
        dirty_prices.append(dirty_price_i)
        clean_market_values.append(clean_market_value_i)
        full_market_values.append(full_market_value_i)
        accrued_interest_amounts.append(accrued_interest_amount_i)
        macaulay_durations.append(mac_dur_i)
        modified_durations.append(mod_dur_i)
        convexities.append(convexity_i)
        dv01s.append(dv01_i)

    df["years_to_maturity"] = years
    df["accrued_interest_per_100"] = accrued_interest
    df["dirty_price"] = dirty_prices
    df["clean_market_value"] = clean_market_values
    df["full_market_value"] = full_market_values
    df["accrued_interest_amount"] = accrued_interest_amounts
    df["market_value"] = df["full_market_value"]
    df["macaulay_duration"] = macaulay_durations
    df["modified_duration"] = modified_durations
    df["convexity"] = convexities
    df["dv01"] = dv01s

    return df


def _normalize_currency_code(value: str) -> str:
    """Normalize and validate a three-letter currency code."""
    code = str(value).strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise ValueError(
            f"Invalid currency code '{value}'. Use a three-letter code such as EUR or USD."
        )
    return code


def validate_fx_rates(
    currencies: list[str] | tuple[str, ...] | set[str],
    base_currency: str,
    fx_rates: dict[str, float],
) -> dict[str, float]:
    """
    Validate FX rates expressed as base-currency units per one local-currency unit.

    Example with EUR base: USD -> 0.92 means USD 1 = EUR 0.92.
    """
    base = _normalize_currency_code(base_currency)
    normalized_currencies = sorted(
        {_normalize_currency_code(currency) for currency in currencies}
    )
    normalized_rates = {
        _normalize_currency_code(currency): float(rate)
        for currency, rate in fx_rates.items()
    }

    missing = [
        currency
        for currency in normalized_currencies
        if currency not in normalized_rates
    ]
    if missing:
        raise ValueError(
            "Missing FX-to-base rate(s) for: " + ", ".join(missing)
        )

    for currency in normalized_currencies:
        rate = normalized_rates[currency]
        if not np.isfinite(rate) or rate <= 0:
            raise ValueError(
                f"FX-to-base rate for {currency} must be finite and strictly positive."
            )

    if base not in normalized_rates:
        raise ValueError(
            f"The base currency {base} must have an explicit FX-to-base rate of 1.0."
        )

    if not np.isclose(normalized_rates[base], 1.0, atol=1e-12):
        raise ValueError(
            f"FX-to-base rate for base currency {base} must equal 1.0."
        )

    return {
        currency: normalized_rates[currency]
        for currency in normalized_currencies
    }


def apply_fx_conversion(
    risk_df: pd.DataFrame,
    base_currency: str,
    fx_rates: dict[str, float],
) -> pd.DataFrame:
    """
    Translate clean value, full value, accrued interest and DV01 to base currency.

    For backward compatibility, synthetic risk frames that only contain
    market_value are interpreted as having zero accrued interest and therefore
    equal clean and full values.
    """
    required = {"currency", "market_value", "dv01"}
    missing_columns = required - set(risk_df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing columns for FX conversion: {sorted(missing_columns)}"
        )

    converted = risk_df.copy()
    converted["currency"] = (
        converted["currency"].astype(str).str.strip().str.upper()
    )

    if "full_market_value" not in converted.columns:
        converted["full_market_value"] = converted["market_value"].astype(float)
    if "clean_market_value" not in converted.columns:
        converted["clean_market_value"] = converted["full_market_value"].astype(float)
    if "accrued_interest_amount" not in converted.columns:
        converted["accrued_interest_amount"] = (
            converted["full_market_value"].astype(float)
            - converted["clean_market_value"].astype(float)
        )

    converted["market_value"] = converted["full_market_value"].astype(float)

    base = _normalize_currency_code(base_currency)
    currencies = sorted(converted["currency"].unique().tolist())
    validated_rates = validate_fx_rates(
        currencies=currencies,
        base_currency=base,
        fx_rates=fx_rates,
    )

    converted["base_currency"] = base
    converted["fx_to_base"] = converted["currency"].map(validated_rates)
    converted["clean_market_value_base"] = (
        converted["clean_market_value"].astype(float)
        * converted["fx_to_base"].astype(float)
    )
    converted["full_market_value_base"] = (
        converted["full_market_value"].astype(float)
        * converted["fx_to_base"].astype(float)
    )
    converted["accrued_interest_amount_base"] = (
        converted["accrued_interest_amount"].astype(float)
        * converted["fx_to_base"].astype(float)
    )
    converted["market_value_base"] = converted["full_market_value_base"]
    converted["dv01_base"] = (
        converted["dv01"].astype(float)
        * converted["fx_to_base"].astype(float)
    )

    return converted


def build_currency_exposure_table(
    risk_df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate clean value, full value and DV01 by local currency."""
    required = {
        "bond_id",
        "currency",
        "base_currency",
        "fx_to_base",
        "clean_market_value",
        "full_market_value",
        "accrued_interest_amount",
        "clean_market_value_base",
        "full_market_value_base",
        "accrued_interest_amount_base",
        "dv01",
        "dv01_base",
    }
    missing = required - set(risk_df.columns)
    if missing:
        raise ValueError(
            f"Missing converted columns for currency exposure: {sorted(missing)}"
        )

    base_values = risk_df["base_currency"].dropna().astype(str).unique()
    if len(base_values) != 1:
        raise ValueError("Risk data must contain exactly one base currency.")

    currency_df = (
        risk_df.groupby("currency", as_index=False)
        .agg(
            fx_to_base=("fx_to_base", "first"),
            local_clean_market_value=("clean_market_value", "sum"),
            local_full_market_value=("full_market_value", "sum"),
            local_accrued_interest_amount=("accrued_interest_amount", "sum"),
            clean_market_value_base=("clean_market_value_base", "sum"),
            full_market_value_base=("full_market_value_base", "sum"),
            accrued_interest_amount_base=("accrued_interest_amount_base", "sum"),
            local_dv01=("dv01", "sum"),
            dv01_base=("dv01_base", "sum"),
            bond_count=("bond_id", "count"),
        )
        .sort_values("currency")
        .reset_index(drop=True)
    )

    # Backward-compatible aliases now explicitly refer to full value.
    currency_df["local_market_value"] = currency_df["local_full_market_value"]
    currency_df["market_value_base"] = currency_df["full_market_value_base"]

    total_full_value = float(currency_df["full_market_value_base"].sum())
    currency_df["pct_base_market_value"] = (
        currency_df["full_market_value_base"] / total_full_value
        if total_full_value > 0
        else 0.0
    )
    currency_df["base_currency"] = str(base_values[0])
    return currency_df


def summarize_portfolio(
    risk_df: pd.DataFrame,
    base_currency: str | None = None,
) -> PortfolioSummary:
    """Aggregate the portfolio using full economic value and full-value DV01."""
    required = {
        "currency",
        "base_currency",
        "clean_market_value_base",
        "full_market_value_base",
        "accrued_interest_amount_base",
        "dv01_base",
        "yield_to_maturity",
        "modified_duration",
        "convexity",
    }
    missing = required - set(risk_df.columns)
    if missing:
        raise ValueError(
            "Portfolio aggregation requires explicit FX conversion and full-value fields. "
            f"Missing columns: {sorted(missing)}"
        )

    base_values = risk_df["base_currency"].dropna().astype(str).unique()
    if len(base_values) != 1:
        raise ValueError("Risk data must contain exactly one base currency.")

    resolved_base = _normalize_currency_code(
        base_currency if base_currency is not None else str(base_values[0])
    )
    if resolved_base != str(base_values[0]).upper():
        raise ValueError(
            "Requested base currency does not match the converted risk data."
        )

    total_clean_market_value = float(
        risk_df["clean_market_value_base"].sum()
    )
    total_full_market_value = float(
        risk_df["full_market_value_base"].sum()
    )
    total_accrued_interest_amount = float(
        risk_df["accrued_interest_amount_base"].sum()
    )

    if total_full_market_value <= 0:
        raise ValueError("Total base-currency full market value must be positive.")

    if not np.isclose(
        total_clean_market_value + total_accrued_interest_amount,
        total_full_market_value,
        rtol=1e-10,
        atol=1e-6,
    ):
        raise ValueError(
            "Clean value plus accrued interest does not reconcile to full value."
        )

    weights = risk_df["full_market_value_base"] / total_full_market_value
    weighted_average_yield = float(
        np.sum(weights * risk_df["yield_to_maturity"])
    )
    weighted_average_modified_duration = float(
        np.sum(weights * risk_df["modified_duration"])
    )
    weighted_average_convexity = float(
        np.sum(weights * risk_df["convexity"])
    )
    total_dv01 = float(risk_df["dv01_base"].sum())

    return PortfolioSummary(
        base_currency=resolved_base,
        currencies=tuple(sorted(risk_df["currency"].astype(str).unique())),
        total_clean_market_value=total_clean_market_value,
        total_full_market_value=total_full_market_value,
        total_accrued_interest_amount=total_accrued_interest_amount,
        total_market_value=total_full_market_value,
        weighted_average_yield=weighted_average_yield,
        weighted_average_modified_duration=weighted_average_modified_duration,
        weighted_average_convexity=weighted_average_convexity,
        total_dv01=total_dv01,
        number_of_bonds=int(len(risk_df)),
    )


def portfolio_summary_to_dict(summary: PortfolioSummary) -> dict:
    """Convert PortfolioSummary into explicit clean/full reporting fields."""
    return {
        "base_currency": summary.base_currency,
        "currencies": ", ".join(summary.currencies),
        "total_clean_market_value": summary.total_clean_market_value,
        "total_full_market_value": summary.total_full_market_value,
        "total_accrued_interest_amount": summary.total_accrued_interest_amount,
        "total_market_value": summary.total_market_value,
        "weighted_average_yield": summary.weighted_average_yield,
        "weighted_average_modified_duration": summary.weighted_average_modified_duration,
        "weighted_average_convexity": summary.weighted_average_convexity,
        "total_dv01": summary.total_dv01,
        "number_of_bonds": summary.number_of_bonds,
    }


def calculate_dv01_by_bucket(risk_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate clean value, full value and full-value DV01 by bucket."""
    required = {
        "curve_bucket",
        "base_currency",
        "clean_market_value_base",
        "full_market_value_base",
        "dv01_base",
    }
    missing = required - set(risk_df.columns)
    if missing:
        raise ValueError(
            "DV01 bucket aggregation requires FX-converted full-value data. "
            f"Missing columns: {sorted(missing)}"
        )

    base_values = risk_df["base_currency"].dropna().astype(str).unique()
    if len(base_values) != 1:
        raise ValueError("Risk data must contain exactly one base currency.")

    bucket_df = (
        risk_df.groupby("curve_bucket", as_index=False)
        .agg(
            clean_market_value_base=("clean_market_value_base", "sum"),
            full_market_value_base=("full_market_value_base", "sum"),
            dv01_base=("dv01_base", "sum"),
        )
        .sort_values("curve_bucket")
    )
    bucket_df["market_value_base"] = bucket_df["full_market_value_base"]

    total_dv01 = float(bucket_df["dv01_base"].sum())
    bucket_df["pct_total_dv01"] = (
        bucket_df["dv01_base"] / total_dv01
        if total_dv01 > 0
        else 0.0
    )
    bucket_df["base_currency"] = str(base_values[0])
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
    """Calculate fixed-income scenario P&L in the selected base currency."""
    required = {
        "bond_id",
        "curve_bucket",
        "base_currency",
        "market_value_base",
        "modified_duration",
        "convexity",
        "dv01_base",
    }
    missing = required - set(risk_df.columns)
    if missing:
        raise ValueError(
            "Scenario P&L requires FX-converted data. "
            f"Missing columns: {sorted(missing)}"
        )

    base_values = risk_df["base_currency"].dropna().astype(str).unique()
    if len(base_values) != 1:
        raise ValueError("Risk data must contain exactly one base currency.")
    base_currency = str(base_values[0])

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
                market_value=float(row["market_value_base"]),
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
                "currency": base_currency,
                "main_driver": "Rates duration / curve exposure",
            }
        )

    spread_shock_bps = 50.0
    spread_pnl = float(-(risk_df["dv01_base"] * spread_shock_bps).sum())
    scenario_rows.append(
        {
            "scenario_name": "Credit spread +50 bps",
            "risk_factor": "credit",
            "shock_description": (
                "All credit spreads widen by 50 bps. Uses modified duration "
                "as a spread-duration proxy."
            ),
            "duration_pnl": spread_pnl,
            "convexity_pnl": 0.0,
            "estimated_pnl": spread_pnl,
            "currency": base_currency,
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
    """Generate desk commentary with explicit currency and full-value conventions."""
    if bucket_df.empty:
        return ["No DV01 bucket data available."]

    required = {
        "currency",
        "base_currency",
        "fx_to_base",
        "clean_market_value_base",
        "full_market_value_base",
    }
    missing = required - set(risk_df.columns)
    if missing:
        raise ValueError(
            "Commentary requires FX-converted full-value risk data. "
            f"Missing columns: {sorted(missing)}"
        )

    base_currency = str(risk_df["base_currency"].iloc[0])
    currencies = sorted(risk_df["currency"].astype(str).unique())
    clean_value = float(risk_df["clean_market_value_base"].sum())
    full_value = float(risk_df["full_market_value_base"].sum())
    accrued_amount = full_value - clean_value

    largest_bucket = bucket_df.loc[bucket_df["dv01_base"].idxmax()]
    largest_bucket_name = largest_bucket["curve_bucket"]
    largest_bucket_pct = float(largest_bucket["pct_total_dv01"])

    if largest_bucket_name in ["10Y+", "5-10Y"]:
        concentration_label = "long-end"
    elif largest_bucket_name == "0-2Y":
        concentration_label = "front-end"
    else:
        concentration_label = "belly"

    comments = [
        (
            f"Portfolio aggregation is expressed in {base_currency}. Local values and DV01 "
            f"for {', '.join(currencies)} are translated using the displayed FX-to-base assumptions."
        ),
        (
            f"Clean quoted value is {clean_value:,.0f} {base_currency}; full economic value is "
            f"{full_value:,.0f} {base_currency}, including {accrued_amount:,.0f} of accrued interest. "
            "DV01 and scenario P&L use full value."
        ),
        (
            f"DV01 is concentrated in the {largest_bucket_name} bucket "
            f"({largest_bucket_pct:.1%} of total {base_currency} DV01), indicating mainly "
            f"{concentration_label} rate exposure."
        ),
    ]

    worst_scenario = identify_worst_scenario(scenario_df)
    comments.append(
        f"The largest estimated loss comes from '{worst_scenario['scenario_name']}' "
        f"with estimated P&L of {worst_scenario['estimated_pnl']:,.0f} {base_currency}."
    )

    if largest_bucket_pct >= 0.50:
        comments.append(
            "Risk is materially concentrated in one maturity bucket. Hedge analysis should focus first on that bucket."
        )
    else:
        comments.append(
            "DV01 is relatively diversified across curve buckets, but non-parallel curve moves remain relevant."
        )

    comments.append(
        "FX translation makes aggregation dimensionally valid but does not model FX risk, cross-currency basis, or hedge execution."
    )
    comments.append(
        "Scenario P&L uses full-value duration/convexity approximations and is not a full revaluation engine."
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
