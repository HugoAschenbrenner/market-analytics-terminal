"""
Repo Engine.

This module implements transparent repo cashflow analytics.

Financial conventions:
- Haircut is stored as a decimal, e.g. 2% = 0.02.
- Repo rate is stored as a decimal annualized rate, e.g. 4% = 0.04.
- Default day-count basis is ACT/360.
- Cash amount = collateral market value * (1 - haircut).
- Repo interest = cash amount * repo rate * repo days / day-count basis.
- Repurchase amount = cash amount + repo interest.

Important limitation:
This is a simplified repo cashflow model for analytics and demonstration.
It is not a legal, settlement, collateral management, or counterparty risk system.
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
    """Generate a simple repo sensitivity table for haircut and repo rate.

    This table is useful for quickly seeing how funding terms affect
    cash amount, interest cost, and maturity repurchase amount.
    """

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
