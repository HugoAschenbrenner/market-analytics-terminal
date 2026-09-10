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


SUPPORTED_DAY_COUNT_CONVENTIONS = (
    "ACT/ACT",
    "ACT/365F",
    "30/360",
)

SUPPORTED_BOND_PRICING_MODES = (
    "Solve YTM from clean price",
    "Audit supplied YTM against quote",
)

SUPPORTED_WHEN_ISSUED_POLICIES = (
    "Flag",
    "Reject",
)


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

    parsed = pd.to_datetime(value)
    if pd.isna(parsed):
        raise ValueError("Bond dates must be valid and non-missing.")
    return parsed


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


def _normalize_day_count_convention(
    convention: str,
) -> str:
    normalized = str(convention).strip().upper()
    aliases = {
        "ACTUAL/ACTUAL": "ACT/ACT",
        "ACTUAL/365": "ACT/365F",
        "ACT/365": "ACT/365F",
        "30E/360": "30/360",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized not in SUPPORTED_DAY_COUNT_CONVENTIONS:
        raise ValueError(
            "Unsupported day-count convention. "
            f"Choose one of {SUPPORTED_DAY_COUNT_CONVENTIONS}."
        )
    return normalized


def _normalize_bond_pricing_mode(
    pricing_mode: str,
) -> str:
    mode = str(pricing_mode).strip()
    if mode not in SUPPORTED_BOND_PRICING_MODES:
        raise ValueError(
            "Unsupported bond pricing mode. "
            f"Choose one of {SUPPORTED_BOND_PRICING_MODES}."
        )
    return mode


def _normalize_when_issued_policy(
    policy: str,
) -> str:
    normalized = str(policy).strip().title()
    if normalized not in SUPPORTED_WHEN_ISSUED_POLICIES:
        raise ValueError(
            "Unsupported when-issued policy. "
            f"Choose one of {SUPPORTED_WHEN_ISSUED_POLICIES}."
        )
    return normalized


def _validate_coupon_frequency(
    frequency: int,
) -> int:
    if not np.isfinite(float(frequency)) or float(frequency) != int(frequency):
        raise ValueError("Coupon frequency must be an integer.")
    resolved = int(frequency)
    if resolved <= 0 or 12 % resolved != 0:
        raise ValueError(
            "Coupon frequency must be a positive divisor of 12."
        )
    return resolved


def _thirty_360_us_year_fraction(
    start_date,
    end_date,
) -> float:
    start = _to_timestamp(start_date).normalize()
    end = _to_timestamp(end_date).normalize()

    if end < start:
        raise ValueError(
            "Day-count end date cannot precede start date."
        )

    d1 = int(start.day)
    d2 = int(end.day)
    if start.month == 2 and start.is_month_end:
        if end.month == 2 and end.is_month_end:
            d2 = 30
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30
    d1 = min(d1, 30)

    numerator = (
        (int(end.year) - int(start.year)) * 360
        + (int(end.month) - int(start.month)) * 30
        + (d2 - d1)
    )
    return float(numerator / 360.0)


def calculate_day_count_year_fraction(
    start_date,
    end_date,
    convention: str = "ACT/ACT",
) -> float:
    start = _to_timestamp(start_date).normalize()
    end = _to_timestamp(end_date).normalize()

    if end < start:
        raise ValueError(
            "Day-count end date cannot precede start date."
        )

    resolved = _normalize_day_count_convention(
        convention
    )

    if resolved == "30/360":
        return _thirty_360_us_year_fraction(start, end)

    elapsed_days = float((end - start).days)

    if resolved == "ACT/365F":
        return elapsed_days / 365.0

    # Calendar ACT/ACT (ISDA) for this date-only helper. Bond cashflows
    # use coupon-reference ACT/ACT (ICMA) below, not a 365.25-day proxy.
    fraction = 0.0
    cursor = start
    while cursor < end:
        boundary = min(end, pd.Timestamp(year=cursor.year + 1, month=1, day=1))
        fraction += (boundary - cursor).days / (366.0 if cursor.is_leap_year else 365.0)
        cursor = boundary
    return float(fraction)


def validate_bond_contract_dates(
    issue_date,
    maturity_date,
    valuation_date,
    when_issued_policy: str = "Flag",
) -> str:
    issue = _to_timestamp(issue_date).normalize()
    maturity = _to_timestamp(maturity_date).normalize()
    valuation = _to_timestamp(valuation_date).normalize()
    policy = _normalize_when_issued_policy(
        when_issued_policy
    )

    if issue >= maturity:
        raise ValueError(
            "Bond issue date must be strictly before maturity date."
        )

    if valuation >= maturity:
        raise ValueError(
            "Valuation date must be strictly before maturity date."
        )

    if valuation < issue:
        if policy == "Reject":
            raise ValueError(
                "When-issued position rejected: valuation date "
                "precedes issue date."
            )
        return "When-issued (flagged)"

    return "Active"


def _reference_coupon_grid(start_date, maturity_date, frequency: int) -> pd.DatetimeIndex:
    """Unadjusted maturity-anchored grid including the boundary before start.

    Preserve the maturity day (and month-end convention) on every date;
    repeated subtraction from February would otherwise drift the schedule.
    """
    start = _to_timestamp(start_date).normalize()
    maturity = _to_timestamp(maturity_date).normalize()
    months = 12 // _validate_coupon_frequency(frequency)
    dates = [maturity]
    offset = 1
    while dates[-1] > start:
        current = maturity - pd.DateOffset(months=offset * months)
        if maturity.is_month_end:
            current = current + pd.offsets.MonthEnd(0)
        dates.append(current.normalize())
        offset += 1
    return pd.DatetimeIndex(dates[::-1])


def _coupon_reference_periods(start, end, reference_grid: pd.DatetimeIndex) -> float:
    """Elapsed regular coupon periods, with partial periods on actual days."""
    total = 0.0
    for left, right in zip(reference_grid[:-1], reference_grid[1:]):
        overlap_start = max(pd.Timestamp(start), left)
        overlap_end = min(pd.Timestamp(end), right)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start).days / (right - left).days
    return float(total)


def build_contractual_coupon_schedule(
    issue_date,
    maturity_date,
    frequency: int,
) -> pd.DatetimeIndex:
    issue = _to_timestamp(issue_date).normalize()
    maturity = _to_timestamp(maturity_date).normalize()
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )

    if issue >= maturity:
        raise ValueError(
            "Bond issue date must be strictly before maturity date."
        )

    reference_grid = _reference_coupon_grid(issue, maturity, resolved_frequency)
    schedule = reference_grid[reference_grid > issue]

    if len(schedule) == 0 or schedule[-1] != maturity:
        raise RuntimeError(
            "Contractual coupon schedule must terminate at maturity."
        )

    return schedule


def _coupon_period_bounds(
    issue_date,
    maturity_date,
    valuation_date,
    frequency: int,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    issue = _to_timestamp(issue_date).normalize()
    valuation = _to_timestamp(valuation_date).normalize()

    schedule = build_contractual_coupon_schedule(
        issue_date=issue_date,
        maturity_date=maturity_date,
        frequency=frequency,
    )

    previous_coupon = issue

    for payment_date in schedule:
        if payment_date <= valuation:
            previous_coupon = payment_date
            continue
        return previous_coupon, payment_date

    raise ValueError(
        "No coupon payment remains after the valuation date."
    )


def calculate_contractual_accrued_interest_per_100(
    coupon_rate: float,
    frequency: int,
    issue_date,
    maturity_date,
    valuation_date,
    day_count_convention: str = "ACT/ACT",
) -> float:
    issue = _to_timestamp(issue_date).normalize()
    valuation = _to_timestamp(valuation_date).normalize()
    maturity = _to_timestamp(maturity_date).normalize()
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )
    convention = _normalize_day_count_convention(
        day_count_convention
    )

    if valuation <= issue:
        return 0.0

    if valuation >= maturity:
        raise ValueError(
            "Accrued interest is undefined at or after maturity."
        )

    previous_coupon, next_coupon = _coupon_period_bounds(
        issue_date=issue,
        maturity_date=maturity,
        valuation_date=valuation,
        frequency=resolved_frequency,
    )

    if valuation == previous_coupon:
        return 0.0

    if convention == "ACT/ACT":
        reference_grid = _reference_coupon_grid(issue, maturity, resolved_frequency)
        next_index = reference_grid.get_loc(next_coupon)
        reference_start = reference_grid[next_index - 1]
        period_days = float(
            (next_coupon - reference_start).days
        )
        elapsed_days = float(
            (valuation - previous_coupon).days
        )

        if period_days <= 0:
            raise ValueError(
                "Coupon period must contain a positive number of days."
            )

        coupon_per_regular_period = (
            100.0
            * float(coupon_rate)
            / resolved_frequency
        )
        return float(
            coupon_per_regular_period
            * elapsed_days
            / period_days
        )

    return float(
        100.0
        * float(coupon_rate)
        * calculate_day_count_year_fraction(
            previous_coupon,
            valuation,
            convention,
        )
    )


def _coupon_cashflow_per_100(
    coupon_rate: float,
    frequency: int,
    issue_date,
    payment_date,
    day_count_convention: str,
    reference_period_start=None,
) -> float:
    issue = _to_timestamp(issue_date).normalize()
    payment = _to_timestamp(payment_date).normalize()
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )
    convention = _normalize_day_count_convention(
        day_count_convention
    )
    months_per_coupon = int(12 / resolved_frequency)

    regular_period_start = _to_timestamp(reference_period_start) if reference_period_start is not None else (
        payment
        - pd.DateOffset(months=months_per_coupon)
    ).normalize()
    accrual_start = max(issue, regular_period_start)

    if convention == "ACT/ACT":
        regular_days = float(
            (payment - regular_period_start).days
        )
        actual_days = float(
            (payment - accrual_start).days
        )

        if regular_days <= 0:
            raise ValueError(
                "Regular coupon period must be positive."
            )

        return float(
            100.0
            * float(coupon_rate)
            / resolved_frequency
            * actual_days
            / regular_days
        )

    return float(
        100.0
        * float(coupon_rate)
        * calculate_day_count_year_fraction(
            accrual_start,
            payment,
            convention,
        )
    )


def build_remaining_contractual_cashflows(
    coupon_rate: float,
    frequency: int,
    issue_date,
    maturity_date,
    valuation_date,
    day_count_convention: str = "ACT/ACT",
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    valuation = _to_timestamp(valuation_date).normalize()
    maturity = _to_timestamp(maturity_date).normalize()
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )
    convention = _normalize_day_count_convention(
        day_count_convention
    )

    schedule = build_contractual_coupon_schedule(
        issue_date=issue_date,
        maturity_date=maturity_date,
        frequency=resolved_frequency,
    )
    remaining_dates = schedule[
        schedule > valuation
    ]

    if len(remaining_dates) == 0:
        raise ValueError(
            "No contractual cashflows remain after valuation date."
        )

    reference_grid = _reference_coupon_grid(
        min(_to_timestamp(issue_date).normalize(), valuation), maturity, resolved_frequency
    )
    cashflows = np.array(
        [
            _coupon_cashflow_per_100(
                coupon_rate=coupon_rate,
                frequency=resolved_frequency,
                issue_date=issue_date,
                payment_date=payment_date,
                day_count_convention=convention,
                reference_period_start=reference_grid[reference_grid.get_loc(payment_date) - 1],
            )
            for payment_date in remaining_dates
        ],
        dtype=float,
    )
    cashflows[-1] += 100.0

    discount_exponents = np.array(
        [
            _coupon_reference_periods(valuation, payment_date, reference_grid)
            if convention == "ACT/ACT" else calculate_day_count_year_fraction(
                valuation,
                payment_date,
                convention,
            )
            * resolved_frequency
            for payment_date in remaining_dates
        ],
        dtype=float,
    )

    if (
        not np.all(np.diff(discount_exponents) > 0)
        or discount_exponents[0] <= 0
    ):
        raise ValueError(
            "Cashflow discount exponents must be strictly increasing."
        )

    if remaining_dates[-1] != maturity:
        raise RuntimeError(
            "Final contractual cashflow must occur at maturity."
        )

    return (
        pd.DatetimeIndex(remaining_dates),
        cashflows,
        discount_exponents,
    )


def calculate_dirty_price_from_ytm(
    cashflows_per_100: np.ndarray,
    discount_exponents: np.ndarray,
    yield_to_maturity: float,
    frequency: int,
) -> float:
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )
    ytm = float(yield_to_maturity)
    discount_base = 1.0 + ytm / resolved_frequency

    if (
        not np.isfinite(discount_base)
        or discount_base <= 0
    ):
        raise ValueError(
            "Yield produces a non-positive discount base."
        )

    return float(
        np.sum(
            np.asarray(cashflows_per_100, dtype=float)
            / np.power(
                discount_base,
                np.asarray(discount_exponents, dtype=float),
            )
        )
    )


def solve_ytm_from_dirty_price(
    target_dirty_price: float,
    cashflows_per_100: np.ndarray,
    discount_exponents: np.ndarray,
    frequency: int,
    tolerance: float = 1e-12,
    max_iterations: int = 250,
) -> float:
    target = float(target_dirty_price)
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )

    if not np.isfinite(target) or target <= 0:
        raise ValueError(
            "Target dirty price must be finite and strictly positive."
        )

    lower = -0.99 * resolved_frequency
    upper = 1.0

    def objective(yield_value: float) -> float:
        return (
            calculate_dirty_price_from_ytm(
                cashflows_per_100=cashflows_per_100,
                discount_exponents=discount_exponents,
                yield_to_maturity=yield_value,
                frequency=resolved_frequency,
            )
            - target
        )

    lower_value = objective(lower)
    upper_value = objective(upper)

    while upper_value > 0 and upper < 100.0:
        upper *= 2.0
        upper_value = objective(upper)

    if lower_value < 0 or upper_value > 0:
        raise ValueError(
            "Could not bracket a YTM solution for the quoted dirty price."
        )

    for _ in range(int(max_iterations)):
        midpoint = 0.5 * (lower + upper)
        midpoint_value = objective(midpoint)

        if abs(midpoint_value) <= tolerance:
            return float(midpoint)

        if midpoint_value > 0:
            lower = midpoint
        else:
            upper = midpoint

    return float(0.5 * (lower + upper))


def calculate_schedule_consistent_risk_metrics(
    cashflows_per_100: np.ndarray,
    discount_exponents: np.ndarray,
    yield_to_maturity: float,
    frequency: int,
    bump_size: float = 1e-4,
) -> tuple[float, float, float]:
    ytm = float(yield_to_maturity)
    resolved_frequency = _validate_coupon_frequency(
        frequency
    )
    bump = float(bump_size)

    if bump <= 0:
        raise ValueError(
            "Yield bump size must be strictly positive."
        )

    base_price = calculate_dirty_price_from_ytm(
        cashflows_per_100,
        discount_exponents,
        ytm,
        resolved_frequency,
    )
    lower_yield = ytm - bump
    upper_yield = ytm + bump

    if 1.0 + lower_yield / resolved_frequency <= 0:
        raise ValueError(
            "Yield is too close to the periodic-compounding floor."
        )

    price_down = calculate_dirty_price_from_ytm(
        cashflows_per_100,
        discount_exponents,
        lower_yield,
        resolved_frequency,
    )
    price_up = calculate_dirty_price_from_ytm(
        cashflows_per_100,
        discount_exponents,
        upper_yield,
        resolved_frequency,
    )

    modified_duration = float(
        (price_down - price_up)
        / (2.0 * base_price * bump)
    )
    convexity = float(
        (price_down + price_up - 2.0 * base_price)
        / (base_price * bump**2)
    )
    macaulay_duration = float(
        modified_duration
        * (1.0 + ytm / resolved_frequency)
    )

    return (
        macaulay_duration,
        modified_duration,
        convexity,
    )


SOVEREIGN_SECTOR_TOKENS = (
    "SOVEREIGN",
    "GOVERNMENT",
    "TREASURY",
    "SUPRANATIONAL",
)


def _parse_explicit_boolean(
    value,
    field_name: str,
) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "y"}:
        return True

    if normalized in {"false", "0", "no", "n"}:
        return False

    raise ValueError(
        f"{field_name} must be a boolean or one of "
        "true/false, yes/no, 1/0."
    )


def classify_credit_spread_exposure(
    sector: str,
    explicit_eligibility=None,
) -> tuple[bool, str, str]:
    """
    Classify whether a bond belongs in the credit-spread sleeve.

    Explicit input takes precedence. Otherwise sovereign, government,
    treasury and supranational sectors are treated as rates-only.
    """
    if explicit_eligibility is not None and not pd.isna(
        explicit_eligibility
    ):
        eligible = _parse_explicit_boolean(
            explicit_eligibility,
            "credit_spread_eligible",
        )
        return (
            eligible,
            (
                "Credit-spread eligible"
                if eligible
                else "Rates-only / excluded from credit stress"
            ),
            "Explicit input",
        )

    normalized_sector = str(sector).strip().upper()
    is_sovereign = any(
        token in normalized_sector
        for token in SOVEREIGN_SECTOR_TOKENS
    )
    eligible = not is_sovereign

    return (
        eligible,
        (
            "Credit-spread eligible"
            if eligible
            else "Sovereign / rates-only"
        ),
        "Sector mapping",
    )


def build_credit_curve_key(
    currency: str,
    sector: str,
    rating: str,
    credit_spread_eligible: bool,
    explicit_curve_key=None,
) -> str:
    if explicit_curve_key is not None and not pd.isna(
        explicit_curve_key
    ):
        key = str(explicit_curve_key).strip()
        if not key:
            raise ValueError(
                "credit_curve_key cannot be blank."
            )
        return key

    normalized_currency = _normalize_currency_code(
        currency
    )

    if not credit_spread_eligible:
        return (
            f"{normalized_currency}|"
            "SOVEREIGN_RATES_ONLY"
        )

    normalized_sector = (
        str(sector).strip().upper()
        or "UNCLASSIFIED"
    )
    normalized_rating = (
        str(rating).strip().upper()
        or "NR"
    )

    return (
        f"{normalized_currency}|"
        f"{normalized_sector}|"
        f"{normalized_rating}"
    )


def calculate_cashflow_repricing_cs01(
    cashflows_per_100: np.ndarray,
    discount_exponents: np.ndarray,
    pricing_yield: float,
    frequency: int,
    notional: float,
    spread_bump_bps: float = 1.0,
) -> float:
    """
    Calculate positive local-currency CS01 by direct cashflow repricing.

    CS01 is the loss for a positive one-basis-point spread widening,
    with the risk-free component held conceptually fixed. This remains
    a parallel-spread proxy, not a full OAS or hazard-rate model.
    """
    bump_bps = float(spread_bump_bps)

    if (
        not np.isfinite(bump_bps)
        or bump_bps <= 0
    ):
        raise ValueError(
            "Spread bump must be finite and strictly positive."
        )

    base_price = calculate_dirty_price_from_ytm(
        cashflows_per_100=cashflows_per_100,
        discount_exponents=discount_exponents,
        yield_to_maturity=float(pricing_yield),
        frequency=int(frequency),
    )
    widened_price = calculate_dirty_price_from_ytm(
        cashflows_per_100=cashflows_per_100,
        discount_exponents=discount_exponents,
        yield_to_maturity=(
            float(pricing_yield)
            + bump_bps / 10_000.0
        ),
        frequency=int(frequency),
    )

    price_loss_per_100 = (
        base_price - widened_price
    )
    cs01 = (
        price_loss_per_100
        / 100.0
        * float(notional)
        / bump_bps
    )

    if not np.isfinite(cs01) or cs01 < 0:
        raise ValueError(
            "CS01 repricing produced an invalid result."
        )

    return float(cs01)


def attach_credit_spread_risk_metrics(
    risk_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add explicit credit eligibility, curve key, spread duration and CS01.

    Sovereign/rates-only bonds receive zero CS01. Credit-eligible bonds
    are repriced under a +1 bp parallel spread widening.
    """
    required = {
        "bond_id",
        "currency",
        "sector",
        "rating",
        "coupon_rate",
        "frequency",
        "issue_date",
        "maturity_date",
        "valuation_date",
        "day_count_convention",
        "pricing_yield_used",
        "notional",
        "full_market_value",
    }
    missing = required - set(risk_df.columns)

    if missing:
        raise ValueError(
            "Credit spread risk requires reconciled bond cashflows. "
            f"Missing columns: {sorted(missing)}"
        )

    output = risk_df.copy()
    eligibility_values: list[bool] = []
    risk_classes: list[str] = []
    mapping_sources: list[str] = []
    curve_keys: list[str] = []
    cs01_values: list[float] = []
    spread_durations: list[float] = []
    methods: list[str] = []

    has_explicit_eligibility = (
        "credit_spread_eligible"
        in output.columns
    )
    has_explicit_curve_key = (
        "credit_curve_key"
        in output.columns
    )

    for _, row in output.iterrows():
        explicit_eligibility = (
            row["credit_spread_eligible"]
            if has_explicit_eligibility
            else None
        )
        (
            eligible,
            risk_class,
            mapping_source,
        ) = classify_credit_spread_exposure(
            sector=row["sector"],
            explicit_eligibility=(
                explicit_eligibility
            ),
        )
        explicit_curve_key = (
            row["credit_curve_key"]
            if has_explicit_curve_key
            else None
        )
        curve_key = build_credit_curve_key(
            currency=row["currency"],
            sector=row["sector"],
            rating=row["rating"],
            credit_spread_eligible=eligible,
            explicit_curve_key=explicit_curve_key,
        )

        if eligible:
            (
                _payment_dates,
                cashflows_per_100,
                discount_exponents,
            ) = build_remaining_contractual_cashflows(
                coupon_rate=float(
                    row["coupon_rate"]
                ),
                frequency=int(
                    row["frequency"]
                ),
                issue_date=row["issue_date"],
                maturity_date=row["maturity_date"],
                valuation_date=row["valuation_date"],
                day_count_convention=(
                    row["day_count_convention"]
                ),
            )
            cs01 = calculate_cashflow_repricing_cs01(
                cashflows_per_100=(
                    cashflows_per_100
                ),
                discount_exponents=(
                    discount_exponents
                ),
                pricing_yield=float(
                    row["pricing_yield_used"]
                ),
                frequency=int(
                    row["frequency"]
                ),
                notional=float(row["notional"]),
                spread_bump_bps=1.0,
            )
            full_value = float(
                row["full_market_value"]
            )
            spread_duration = (
                cs01
                / (
                    full_value
                    * 0.0001
                )
                if full_value > 0
                else 0.0
            )
            method = (
                "Direct +1 bp contractual-cashflow "
                "repricing proxy"
            )
        else:
            cs01 = 0.0
            spread_duration = 0.0
            method = (
                "Excluded from credit-spread stress; "
                "rates-only exposure"
            )

        eligibility_values.append(eligible)
        risk_classes.append(risk_class)
        mapping_sources.append(mapping_source)
        curve_keys.append(curve_key)
        cs01_values.append(float(cs01))
        spread_durations.append(
            float(spread_duration)
        )
        methods.append(method)

    output["credit_spread_eligible"] = (
        eligibility_values
    )
    output["credit_risk_class"] = risk_classes
    output["credit_mapping_source"] = (
        mapping_sources
    )
    output["credit_curve_key"] = curve_keys
    output["spread_duration"] = (
        spread_durations
    )
    output["cs01"] = cs01_values
    output["spread_risk_method"] = methods

    return output


def calculate_bond_risk_metrics(
    bonds: pd.DataFrame,
    valuation_date: Optional[date] = None,
    pricing_mode: str = "Solve YTM from clean price",
    default_day_count_convention: str = "ACT/ACT",
    when_issued_policy: str = "Flag",
    reconciliation_tolerance_per_100: float = 0.01,
) -> pd.DataFrame:
    if valuation_date is None:
        valuation_date = date.today()

    valuation = pd.Timestamp(
        valuation_date
    ).normalize()
    mode = _normalize_bond_pricing_mode(
        pricing_mode
    )
    default_day_count = _normalize_day_count_convention(
        default_day_count_convention
    )
    when_issued = _normalize_when_issued_policy(
        when_issued_policy
    )
    tolerance = float(
        reconciliation_tolerance_per_100
    )

    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError(
            "Price reconciliation tolerance must be finite "
            "and non-negative."
        )

    df = bonds.copy()
    missing = set(REQUIRED_BOND_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required bond columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Bond data cannot be empty.")
    if df[REQUIRED_BOND_COLUMNS].isna().any().any():
        raise ValueError("Bond data contains missing required values.")
    output_rows: list[dict] = []

    for _, source_row in df.iterrows():
        row = source_row.to_dict()

        issue = _to_timestamp(
            row["issue_date"]
        ).normalize()
        maturity = _to_timestamp(
            row["maturity_date"]
        ).normalize()
        frequency = _validate_coupon_frequency(
            row["frequency"]
        )
        day_count = _normalize_day_count_convention(
            row.get(
                "day_count_convention",
                default_day_count,
            )
        )
        schedule_status = validate_bond_contract_dates(
            issue_date=issue,
            maturity_date=maturity,
            valuation_date=valuation,
            when_issued_policy=when_issued,
        )

        clean_price = float(row["clean_price"])
        provided_ytm = float(row["yield_to_maturity"])
        notional = float(row["notional"])
        coupon_rate = float(row["coupon_rate"])

        if not np.isfinite(clean_price) or clean_price <= 0:
            raise ValueError(
                "Clean price must be finite and strictly positive."
            )

        if (
            not np.isfinite(provided_ytm)
            or 1.0 + provided_ytm / frequency <= 0
        ):
            raise ValueError(
                "Supplied YTM is invalid under periodic compounding."
            )

        if not np.isfinite(coupon_rate) or coupon_rate < 0:
            raise ValueError(
                "Coupon rate must be finite and non-negative."
            )

        if not np.isfinite(notional) or notional < 0:
            raise ValueError(
                "Notional must be finite and non-negative."
            )

        accrued_per_100 = (
            calculate_contractual_accrued_interest_per_100(
                coupon_rate=coupon_rate,
                frequency=frequency,
                issue_date=issue,
                maturity_date=maturity,
                valuation_date=valuation,
                day_count_convention=day_count,
            )
        )
        dirty_price = clean_price + accrued_per_100

        (
            payment_dates,
            cashflows_per_100,
            discount_exponents,
        ) = build_remaining_contractual_cashflows(
            coupon_rate=coupon_rate,
            frequency=frequency,
            issue_date=issue,
            maturity_date=maturity,
            valuation_date=valuation,
            day_count_convention=day_count,
        )

        if mode == "Solve YTM from clean price":
            pricing_yield = solve_ytm_from_dirty_price(
                target_dirty_price=dirty_price,
                cashflows_per_100=cashflows_per_100,
                discount_exponents=discount_exponents,
                frequency=frequency,
            )
        else:
            pricing_yield = provided_ytm

        model_dirty_price = calculate_dirty_price_from_ytm(
            cashflows_per_100=cashflows_per_100,
            discount_exponents=discount_exponents,
            yield_to_maturity=pricing_yield,
            frequency=frequency,
        )
        model_clean_price = (
            model_dirty_price - accrued_per_100
        )
        dirty_price_error = (
            model_dirty_price - dirty_price
        )
        clean_price_error = (
            model_clean_price - clean_price
        )
        price_reconciled = bool(
            abs(dirty_price_error) <= tolerance
        )

        (
            macaulay_duration,
            modified_duration,
            convexity,
        ) = calculate_schedule_consistent_risk_metrics(
            cashflows_per_100=cashflows_per_100,
            discount_exponents=discount_exponents,
            yield_to_maturity=pricing_yield,
            frequency=frequency,
        )

        clean_market_value = (
            calculate_value_from_price_per_100(
                price_per_100=clean_price,
                notional=notional,
            )
        )
        full_market_value = (
            calculate_value_from_price_per_100(
                price_per_100=dirty_price,
                notional=notional,
            )
        )
        accrued_interest_amount = (
            full_market_value - clean_market_value
        )
        dv01 = calculate_dv01(
            modified_duration=modified_duration,
            market_value=full_market_value,
        )

        previous_coupon, next_coupon = _coupon_period_bounds(
            issue_date=issue,
            maturity_date=maturity,
            valuation_date=valuation,
            frequency=frequency,
        )

        years = calculate_day_count_year_fraction(
            valuation,
            maturity,
            "ACT/365F",
        )

        row.update(
            {
                "valuation_date": valuation.date().isoformat(),
                "issue_date": issue.date().isoformat(),
                "maturity_date": maturity.date().isoformat(),
                "schedule_status": schedule_status,
                "pricing_mode": mode,
                "day_count_convention": day_count,
                "provided_yield_to_maturity": provided_ytm,
                "pricing_yield_used": pricing_yield,
                "yield_to_maturity": pricing_yield,
                "previous_coupon_date": previous_coupon.date().isoformat(),
                "next_coupon_date": next_coupon.date().isoformat(),
                "final_cashflow_date": payment_dates[-1].date().isoformat(),
                "cashflow_count": int(len(payment_dates)),
                "years_to_maturity": years,
                "accrued_interest_per_100": accrued_per_100,
                "dirty_price": dirty_price,
                "model_clean_price": model_clean_price,
                "model_dirty_price": model_dirty_price,
                "clean_price_reconciliation_error": clean_price_error,
                "dirty_price_reconciliation_error": dirty_price_error,
                "price_reconciled": price_reconciled,
                "pricing_status": (
                    "Reconciled"
                    if price_reconciled
                    else "Quote/YTM mismatch"
                ),
                "clean_market_value": clean_market_value,
                "full_market_value": full_market_value,
                "accrued_interest_amount": accrued_interest_amount,
                "market_value": full_market_value,
                "macaulay_duration": macaulay_duration,
                "modified_duration": modified_duration,
                "convexity": convexity,
                "dv01": dv01,
            }
        )

        output_rows.append(row)

    result = pd.DataFrame(output_rows)
    return attach_credit_spread_risk_metrics(result)

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
    # Translate clean value, full value, accrued interest, DV01 and CS01
    # into the selected base currency.
    required = {
        "currency",
        "market_value",
        "dv01",
    }
    missing_columns = required - set(
        risk_df.columns
    )

    if missing_columns:
        raise ValueError(
            "Missing columns for FX conversion: "
            f"{sorted(missing_columns)}"
        )

    converted = risk_df.copy()
    converted["currency"] = (
        converted["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if "full_market_value" not in converted.columns:
        converted["full_market_value"] = (
            converted["market_value"].astype(float)
        )

    if "clean_market_value" not in converted.columns:
        converted["clean_market_value"] = (
            converted["full_market_value"].astype(float)
        )

    if "accrued_interest_amount" not in converted.columns:
        converted["accrued_interest_amount"] = (
            converted["full_market_value"].astype(float)
            - converted["clean_market_value"].astype(float)
        )

    converted["market_value"] = (
        converted["full_market_value"].astype(float)
    )

    base = _normalize_currency_code(
        base_currency
    )
    currencies = sorted(
        converted["currency"].unique().tolist()
    )
    validated_rates = validate_fx_rates(
        currencies=currencies,
        base_currency=base,
        fx_rates=fx_rates,
    )

    converted["base_currency"] = base
    converted["fx_to_base"] = (
        converted["currency"].map(
            validated_rates
        )
    )

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
    converted["market_value_base"] = (
        converted["full_market_value_base"]
    )
    converted["dv01_base"] = (
        converted["dv01"].astype(float)
        * converted["fx_to_base"].astype(float)
    )

    # Backward compatibility for synthetic test frames that predate
    # the explicit credit-spread contract.
    if "credit_spread_eligible" not in converted.columns:
        converted["credit_spread_eligible"] = True

    if "credit_risk_class" not in converted.columns:
        converted["credit_risk_class"] = (
            "Unclassified credit proxy"
        )

    if "credit_mapping_source" not in converted.columns:
        converted["credit_mapping_source"] = (
            "Backward-compatible synthetic default"
        )

    if "credit_curve_key" not in converted.columns:
        converted["credit_curve_key"] = (
            converted["currency"].astype(str)
            + "|UNCLASSIFIED|NR"
        )

    if "cs01" not in converted.columns:
        converted["cs01"] = (
            converted["dv01"].astype(float)
        )

    if "spread_duration" not in converted.columns:
        denominator = (
            converted["full_market_value"].astype(float)
            * 0.0001
        )
        converted["spread_duration"] = np.where(
            denominator > 0,
            converted["cs01"].astype(float)
            / denominator,
            0.0,
        )

    if "spread_risk_method" not in converted.columns:
        converted["spread_risk_method"] = (
            "Backward-compatible DV01 proxy"
        )

    converted["cs01_base"] = (
        converted["cs01"].astype(float)
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


def build_credit_spread_exposure_table(
    risk_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate credit-spread exposure by explicit currency/sector/rating key.

    Sovereign/rates-only rows remain visible with zero CS01 so the
    exclusion from credit stress is auditable.
    """
    required = {
        "bond_id",
        "currency",
        "sector",
        "rating",
        "base_currency",
        "credit_spread_eligible",
        "credit_risk_class",
        "credit_mapping_source",
        "credit_curve_key",
        "spread_risk_method",
        "full_market_value_base",
        "cs01_base",
    }
    missing = required - set(risk_df.columns)

    if missing:
        raise ValueError(
            "Credit spread exposure requires explicit mapping "
            "and base-currency CS01. "
            f"Missing columns: {sorted(missing)}"
        )

    base_values = (
        risk_df["base_currency"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(base_values) != 1:
        raise ValueError(
            "Risk data must contain exactly one base currency."
        )

    working = risk_df.copy()
    working["sector"] = (
        working["sector"].astype(str)
    )
    working["rating"] = (
        working["rating"].astype(str)
    )

    exposure = (
        working.groupby(
            [
                "credit_spread_eligible",
                "credit_risk_class",
                "credit_curve_key",
                "currency",
                "sector",
                "rating",
                "credit_mapping_source",
                "spread_risk_method",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            full_market_value_base=(
                "full_market_value_base",
                "sum",
            ),
            cs01_base=("cs01_base", "sum"),
            bond_count=("bond_id", "count"),
        )
        .sort_values(
            [
                "credit_spread_eligible",
                "credit_curve_key",
            ],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    exposure["spread_duration"] = np.where(
        exposure["full_market_value_base"] > 0,
        exposure["cs01_base"]
        / (
            exposure["full_market_value_base"]
            * 0.0001
        ),
        0.0,
    )

    eligible_cs01 = float(
        exposure.loc[
            exposure["credit_spread_eligible"],
            "cs01_base",
        ].sum()
    )
    exposure["pct_total_credit_cs01"] = np.where(
        exposure["credit_spread_eligible"]
        & (eligible_cs01 > 0),
        exposure["cs01_base"] / eligible_cs01,
        0.0,
    )
    exposure["base_currency"] = str(
        base_values[0]
    )

    return exposure


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


def calculate_scenario_pnl(
    risk_df: pd.DataFrame,
    credit_spread_shocks_bps: (
        dict[str, float] | None
    ) = None,
) -> pd.DataFrame:
    """
    Calculate rates and credit scenario P&L in the base currency.

    Rates scenarios use full-value duration/convexity. Credit spread
    stress is restricted to credit-eligible bonds and uses CS01 from
    direct contractual-cashflow repricing. Sovereigns are excluded.
    """
    required = {
        "bond_id",
        "curve_bucket",
        "base_currency",
        "market_value_base",
        "modified_duration",
        "convexity",
        "dv01_base",
        "credit_spread_eligible",
        "credit_curve_key",
        "cs01_base",
    }
    missing = required - set(risk_df.columns)

    if missing:
        raise ValueError(
            "Scenario P&L requires FX-converted rates and "
            "credit-spread risk data. "
            f"Missing columns: {sorted(missing)}"
        )

    base_values = (
        risk_df["base_currency"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(base_values) != 1:
        raise ValueError(
            "Risk data must contain exactly one base currency."
        )

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
            pnl_components = (
                estimate_pnl_with_duration_convexity(
                    modified_duration=float(
                        row["modified_duration"]
                    ),
                    convexity=float(
                        row["convexity"]
                    ),
                    market_value=float(
                        row["market_value_base"]
                    ),
                    yield_move_bps=shock_bps,
                )
            )
            total_duration_pnl += (
                pnl_components["duration_pnl"]
            )
            total_convexity_pnl += (
                pnl_components["convexity_pnl"]
            )
            total_estimated_pnl += (
                pnl_components["estimated_pnl"]
            )

        scenario_rows.append(
            {
                "scenario_name": scenario_name,
                "risk_factor": "rates",
                "shock_description": (
                    _describe_fixed_income_scenario(
                        scenario_name
                    )
                ),
                "duration_pnl": total_duration_pnl,
                "convexity_pnl": total_convexity_pnl,
                "estimated_pnl": total_estimated_pnl,
                "currency": base_currency,
                "main_driver": (
                    "Rates duration / curve exposure"
                ),
                "credit_cs01_base": 0.0,
                "credit_bond_count": 0,
                "sovereign_excluded_count": 0,
                "credit_curve_count": 0,
                "weighted_spread_shock_bps": 0.0,
            }
        )

    eligible = risk_df.loc[
        risk_df["credit_spread_eligible"]
        .astype(bool)
    ].copy()
    excluded_count = int(
        (~risk_df["credit_spread_eligible"]
         .astype(bool)).sum()
    )
    curve_keys = sorted(
        eligible["credit_curve_key"]
        .astype(str)
        .unique()
        .tolist()
    )

    if credit_spread_shocks_bps is None:
        validated_shocks = {
            key: 50.0
            for key in curve_keys
        }
    else:
        validated_shocks = {
            str(key): float(value)
            for key, value
            in credit_spread_shocks_bps.items()
        }
        missing_shocks = [
            key
            for key in curve_keys
            if key not in validated_shocks
        ]

        if missing_shocks:
            raise ValueError(
                "Missing credit spread shock(s) for: "
                + ", ".join(missing_shocks)
            )

    for key in curve_keys:
        shock = float(validated_shocks[key])

        if not np.isfinite(shock):
            raise ValueError(
                f"Credit spread shock for {key} "
                "must be finite."
            )

    if eligible.empty:
        credit_cs01 = 0.0
        spread_pnl = 0.0
        weighted_shock = 0.0
    else:
        eligible["spread_shock_bps"] = (
            eligible["credit_curve_key"]
            .astype(str)
            .map(validated_shocks)
            .astype(float)
        )
        eligible["spread_pnl"] = (
            -eligible["cs01_base"].astype(float)
            * eligible["spread_shock_bps"]
        )
        credit_cs01 = float(
            eligible["cs01_base"].sum()
        )
        spread_pnl = float(
            eligible["spread_pnl"].sum()
        )
        weighted_shock = (
            float(
                (
                    eligible["cs01_base"]
                    * eligible["spread_shock_bps"]
                ).sum()
                / credit_cs01
            )
            if credit_cs01 > 0
            else 0.0
        )

    all_fifty = (
        len(validated_shocks) > 0
        and all(
            np.isclose(value, 50.0)
            for value in validated_shocks.values()
        )
    )
    scenario_name = (
        "Credit spread +50 bps"
        if all_fifty
        else "Credit spread curve stress"
    )

    scenario_rows.append(
        {
            "scenario_name": scenario_name,
            "risk_factor": "credit_spread",
            "shock_description": (
                "Credit-eligible bonds are shocked by their "
                "currency/sector/rating spread curve. Sovereign "
                "and rates-only bonds are excluded. CS01 is a "
                "direct +1 bp contractual-cashflow repricing proxy, "
                "not a full OAS or hazard-rate model."
            ),
            "duration_pnl": spread_pnl,
            "convexity_pnl": 0.0,
            "estimated_pnl": spread_pnl,
            "currency": base_currency,
            "main_driver": (
                "Credit-only CS01 by spread curve"
            ),
            "credit_cs01_base": credit_cs01,
            "credit_bond_count": int(len(eligible)),
            "sovereign_excluded_count": excluded_count,
            "credit_curve_count": int(len(curve_keys)),
            "weighted_spread_shock_bps": (
                weighted_shock
            ),
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
