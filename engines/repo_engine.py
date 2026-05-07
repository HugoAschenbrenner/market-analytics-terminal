"""
Repo Engine.

This module implements transparent repo cashflow and collateral margin analytics.

Financial conventions:
- Haircut is stored as a decimal, e.g. 2% = 0.02.
- Repo rate is stored as a decimal annualized rate, e.g. 4% = 0.04.
- Default day-count basis is ACT/360.
- Cash amount = collateral market value * (1 - haircut).
- Repo interest = cash amount * repo rate * repo days / day-count basis.
- Repurchase amount = cash amount + repo interest.
- Adjusted collateral value = collateral market value * (1 + collateral price shock).
- Eligible collateral = adjusted collateral value * (1 - haircut).
- Margin deficit = max(0, cash amount - eligible collateral).
- Margin surplus = max(0, eligible collateral - cash amount).

Important limitation:
This is a simplified repo cashflow and margin analytics model for demonstration.
It is not a legal, settlement, collateral management, counterparty risk, or close-out system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Union

import pandas as pd


DateLike = Union[str, date, pd.Timestamp]


@dataclass(frozen=True)
class RepoTradeResult:
    """Repo trade cashflow result."""

    collateral_market_value: float
    haircut: float
    cash_amount: float
    repo_rate: float
    start_date: date
    end_date: date
    repo_days: int
    day_count_basis: int
    repo_interest: float
    repurchase_amount: float
    currency: str


@dataclass(frozen=True)
class RepoMarginResult:
    """Repo margin and collateral stress result."""

    collateral_market_value: float
    cash_amount: float
    collateral_price_shock: float
    original_haircut: float
    new_haircut: float
    adjusted_collateral_value: float
    original_eligible_collateral: float
    new_eligible_collateral: float
    margin_deficit: float
    margin_surplus: float
    margin_call_required: bool
    deficit_pct_of_original_collateral: float
    driver: str


def _to_date(value: DateLike) -> date:
    """Convert a date-like value to a Python date."""

    if isinstance(value, date):
        return value

    return pd.to_datetime(value).date()


def validate_repo_inputs(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    day_count_basis: int,
) -> None:
    """Validate core repo inputs."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    if haircut < 0 or haircut >= 1:
        raise ValueError("Haircut must be between 0 and 1.")

    if day_count_basis <= 0:
        raise ValueError("Day-count basis must be positive.")

    # Negative repo rates can exist in some markets, so we do not reject them.
    if repo_rate < -0.10:
        raise ValueError("Repo rate is unrealistically negative for this simplified model.")


def validate_margin_inputs(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
    new_haircut: float,
) -> None:
    """Validate margin analytics inputs."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    if cash_amount < 0:
        raise ValueError("Cash amount cannot be negative.")

    if original_haircut < 0 or original_haircut >= 1:
        raise ValueError("Original haircut must be between 0 and 1.")

    if new_haircut < 0 or new_haircut >= 1:
        raise ValueError("New haircut must be between 0 and 1.")


def calculate_repo_days(start_date: DateLike, end_date: DateLike) -> int:
    """Calculate repo term in calendar days."""

    start = _to_date(start_date)
    end = _to_date(end_date)

    days = (end - start).days

    if days <= 0:
        raise ValueError("End date must be after start date.")

    return days


def calculate_cash_amount(
    collateral_market_value: float,
    haircut: float,
) -> float:
    """Calculate cash amount lent/borrowed against collateral.

    Formula:
    cash_amount = collateral_market_value * (1 - haircut)
    """

    return float(collateral_market_value * (1.0 - haircut))


def calculate_repo_interest(
    cash_amount: float,
    repo_rate: float,
    repo_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate repo interest.

    Formula:
    repo_interest = cash_amount * repo_rate * repo_days / day_count_basis
    """

    return float(cash_amount * repo_rate * repo_days / day_count_basis)


def calculate_repurchase_amount(
    cash_amount: float,
    repo_interest: float,
) -> float:
    """Calculate repurchase amount at repo maturity."""

    return float(cash_amount + repo_interest)


def calculate_repo_trade(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    start_date: DateLike,
    end_date: DateLike,
    day_count_basis: int = 360,
    currency: str = "EUR",
) -> RepoTradeResult:
    """Calculate simplified repo trade cashflows."""

    validate_repo_inputs(
        collateral_market_value=collateral_market_value,
        haircut=haircut,
        repo_rate=repo_rate,
        day_count_basis=day_count_basis,
    )

    start = _to_date(start_date)
    end = _to_date(end_date)
    repo_days = calculate_repo_days(start, end)

    cash_amount = calculate_cash_amount(
        collateral_market_value=collateral_market_value,
        haircut=haircut,
    )

    repo_interest = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=repo_rate,
        repo_days=repo_days,
        day_count_basis=day_count_basis,
    )

    repurchase_amount = calculate_repurchase_amount(
        cash_amount=cash_amount,
        repo_interest=repo_interest,
    )

    return RepoTradeResult(
        collateral_market_value=float(collateral_market_value),
        haircut=float(haircut),
        cash_amount=float(cash_amount),
        repo_rate=float(repo_rate),
        start_date=start,
        end_date=end,
        repo_days=int(repo_days),
        day_count_basis=int(day_count_basis),
        repo_interest=float(repo_interest),
        repurchase_amount=float(repurchase_amount),
        currency=currency,
    )


def repo_result_to_dict(result: RepoTradeResult) -> dict:
    """Convert RepoTradeResult to dictionary for display/export."""

    output = asdict(result)
    output["start_date"] = result.start_date.isoformat()
    output["end_date"] = result.end_date.isoformat()
    return output


def calculate_repo_sensitivity_table(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    start_date: DateLike,
    end_date: DateLike,
    day_count_basis: int = 360,
    currency: str = "EUR",
) -> pd.DataFrame:
    """Generate a simple repo sensitivity table for haircut and repo rate."""

    scenarios = [
        {
            "scenario": "Base case",
            "haircut": haircut,
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Haircut +2 percentage points",
            "haircut": min(haircut + 0.02, 0.99),
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Haircut +5 percentage points",
            "haircut": min(haircut + 0.05, 0.99),
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Repo rate +50 bps",
            "haircut": haircut,
            "repo_rate": repo_rate + 0.0050,
        },
        {
            "scenario": "Repo rate -50 bps",
            "haircut": haircut,
            "repo_rate": repo_rate - 0.0050,
        },
    ]

    rows = []

    for scenario in scenarios:
        result = calculate_repo_trade(
            collateral_market_value=collateral_market_value,
            haircut=scenario["haircut"],
            repo_rate=scenario["repo_rate"],
            start_date=start_date,
            end_date=end_date,
            day_count_basis=day_count_basis,
            currency=currency,
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "haircut": result.haircut,
                "repo_rate": result.repo_rate,
                "cash_amount": result.cash_amount,
                "repo_interest": result.repo_interest,
                "repurchase_amount": result.repurchase_amount,
            }
        )

    return pd.DataFrame(rows)


def calculate_adjusted_collateral_value(
    collateral_market_value: float,
    collateral_price_shock: float,
) -> float:
    """Calculate collateral value after price shock.

    Formula:
    adjusted_collateral_value = collateral_market_value * (1 + collateral_price_shock)
    """

    return float(collateral_market_value * (1.0 + collateral_price_shock))


def calculate_eligible_collateral(
    collateral_market_value: float,
    haircut: float,
) -> float:
    """Calculate eligible collateral after haircut.

    Formula:
    eligible_collateral = collateral_market_value * (1 - haircut)
    """

    return float(collateral_market_value * (1.0 - haircut))


def identify_margin_driver(
    collateral_price_shock: float,
    original_haircut: float,
    new_haircut: float,
) -> str:
    """Identify the main driver of a margin change."""

    haircut_increase = new_haircut > original_haircut
    collateral_drop = collateral_price_shock < 0

    if collateral_drop and haircut_increase:
        return "Collateral depreciation and haircut increase"

    if collateral_drop:
        return "Collateral depreciation"

    if haircut_increase:
        return "Haircut increase"

    if collateral_price_shock > 0 and new_haircut <= original_haircut:
        return "Collateral appreciation / no adverse haircut change"

    return "No adverse margin driver"


def calculate_margin_call(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
    collateral_price_shock: float,
    new_haircut: float,
) -> RepoMarginResult:
    """Calculate margin deficit or surplus after collateral and haircut shocks."""

    validate_margin_inputs(
        collateral_market_value=collateral_market_value,
        cash_amount=cash_amount,
        original_haircut=original_haircut,
        new_haircut=new_haircut,
    )

    adjusted_collateral_value = calculate_adjusted_collateral_value(
        collateral_market_value=collateral_market_value,
        collateral_price_shock=collateral_price_shock,
    )

    original_eligible_collateral = calculate_eligible_collateral(
        collateral_market_value=collateral_market_value,
        haircut=original_haircut,
    )

    new_eligible_collateral = calculate_eligible_collateral(
        collateral_market_value=adjusted_collateral_value,
        haircut=new_haircut,
    )

    margin_deficit = max(0.0, cash_amount - new_eligible_collateral)
    margin_surplus = max(0.0, new_eligible_collateral - cash_amount)
    margin_call_required = margin_deficit > 0.0

    deficit_pct_of_original_collateral = margin_deficit / collateral_market_value

    driver = identify_margin_driver(
        collateral_price_shock=collateral_price_shock,
        original_haircut=original_haircut,
        new_haircut=new_haircut,
    )

    return RepoMarginResult(
        collateral_market_value=float(collateral_market_value),
        cash_amount=float(cash_amount),
        collateral_price_shock=float(collateral_price_shock),
        original_haircut=float(original_haircut),
        new_haircut=float(new_haircut),
        adjusted_collateral_value=float(adjusted_collateral_value),
        original_eligible_collateral=float(original_eligible_collateral),
        new_eligible_collateral=float(new_eligible_collateral),
        margin_deficit=float(margin_deficit),
        margin_surplus=float(margin_surplus),
        margin_call_required=bool(margin_call_required),
        deficit_pct_of_original_collateral=float(deficit_pct_of_original_collateral),
        driver=driver,
    )


def margin_result_to_dict(result: RepoMarginResult) -> dict:
    """Convert RepoMarginResult to dictionary for display/export."""

    return asdict(result)


def calculate_margin_stress_table(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
) -> pd.DataFrame:
    """Generate predefined collateral and haircut stress scenarios."""

    scenarios = [
        {
            "scenario": "Base case",
            "collateral_price_shock": 0.00,
            "new_haircut": original_haircut,
        },
        {
            "scenario": "Collateral -3%, haircut unchanged",
            "collateral_price_shock": -0.03,
            "new_haircut": original_haircut,
        },
        {
            "scenario": "Collateral -5%, haircut +2pp",
            "collateral_price_shock": -0.05,
            "new_haircut": min(original_haircut + 0.02, 0.99),
        },
        {
            "scenario": "Collateral -10%, haircut +5pp",
            "collateral_price_shock": -0.10,
            "new_haircut": min(original_haircut + 0.05, 0.99),
        },
        {
            "scenario": "Collateral +3%, haircut unchanged",
            "collateral_price_shock": 0.03,
            "new_haircut": original_haircut,
        },
    ]

    rows = []

    for scenario in scenarios:
        result = calculate_margin_call(
            collateral_market_value=collateral_market_value,
            cash_amount=cash_amount,
            original_haircut=original_haircut,
            collateral_price_shock=scenario["collateral_price_shock"],
            new_haircut=scenario["new_haircut"],
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "collateral_price_shock": result.collateral_price_shock,
                "original_haircut": result.original_haircut,
                "new_haircut": result.new_haircut,
                "adjusted_collateral_value": result.adjusted_collateral_value,
                "new_eligible_collateral": result.new_eligible_collateral,
                "margin_deficit": result.margin_deficit,
                "margin_surplus": result.margin_surplus,
                "margin_call_required": result.margin_call_required,
                "deficit_pct_of_original_collateral": result.deficit_pct_of_original_collateral,
                "driver": result.driver,
            }
        )

    return pd.DataFrame(rows)


def generate_repo_margin_commentary(result: RepoMarginResult) -> list[str]:
    """Generate desk-style repo margin commentary."""

    comments = []

    if result.margin_call_required:
        comments.append(
            f"Margin call required: deficit of {result.margin_deficit:,.0f}, "
            f"equal to {result.deficit_pct_of_original_collateral:.2%} of original collateral value."
        )
    else:
        comments.append(
            f"No margin call required. Eligible collateral exceeds cash amount by {result.margin_surplus:,.0f}."
        )

    comments.append(f"Main driver: {result.driver}.")

    if result.new_haircut > result.original_haircut:
        comments.append(
            f"Haircut increased from {result.original_haircut:.2%} to {result.new_haircut:.2%}, "
            "reducing eligible collateral."
        )

    if result.collateral_price_shock < 0:
        comments.append(
            f"Collateral value fell by {abs(result.collateral_price_shock):.2%}, directly reducing the collateral base."
        )

    comments.append(
        "This is a simplified collateral analytics proxy and does not model legal close-out, settlement timing, or counterparty default."
    )

    return comments
