"""
Securities Lending Engine.

This module implements simplified securities lending analytics.

Financial conventions:
- Borrow fee is an annualized decimal rate, e.g. 2% = 0.02.
- Rebate rate is an annualized decimal rate, e.g. 1% = 0.01.
- Collateralization rate may be above 100%, e.g. 102% = 1.02.
- Collateral required = security market value * collateralization rate.
- Borrow fee amount = security market value * borrow fee rate * loan days / day-count basis.
- Rebate amount = collateral required * rebate rate * loan days / day-count basis.
- Net lending revenue = borrow fee amount - rebate amount.

Important limitation:
This is a simplified securities lending model for analytics and demonstration.
It does not model legal agreements, counterparty risk, dividend manufactured payments,
recall risk, reinvestment risk, settlement, or full securities finance economics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class SecuritiesLendingResult:
    """Simplified securities lending economics result."""

    security_market_value: float
    borrow_fee_rate: float
    rebate_rate: float
    collateralization_rate: float
    loan_days: int
    day_count_basis: int
    utilization_proxy: float
    is_special: bool
    collateral_required: float
    borrow_fee_amount: float
    rebate_amount: float
    net_lending_revenue: float
    specialness_label: str


def validate_sec_lending_inputs(
    security_market_value: float,
    borrow_fee_rate: float,
    rebate_rate: float,
    collateralization_rate: float,
    loan_days: int,
    day_count_basis: int,
    utilization_proxy: float,
) -> None:
    """Validate securities lending inputs."""

    if security_market_value <= 0:
        raise ValueError("Security market value must be positive.")

    if borrow_fee_rate < 0:
        raise ValueError("Borrow fee rate cannot be negative in this simplified model.")

    if collateralization_rate <= 0:
        raise ValueError("Collateralization rate must be positive.")

    if loan_days <= 0:
        raise ValueError("Loan days must be positive.")

    if day_count_basis <= 0:
        raise ValueError("Day-count basis must be positive.")

    if utilization_proxy < 0 or utilization_proxy > 1:
        raise ValueError("Utilization proxy must be between 0 and 1.")


def calculate_collateral_required(
    security_market_value: float,
    collateralization_rate: float,
) -> float:
    """Calculate collateral required.

    Formula:
    collateral_required = security_market_value * collateralization_rate
    """

    return float(security_market_value * collateralization_rate)


def calculate_borrow_fee_amount(
    security_market_value: float,
    borrow_fee_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate borrow fee amount.

    Formula:
    borrow_fee_amount = security_market_value * borrow_fee_rate * loan_days / day_count_basis
    """

    return float(security_market_value * borrow_fee_rate * loan_days / day_count_basis)


def calculate_rebate_amount(
    collateral_required: float,
    rebate_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate rebate amount paid on collateral.

    Formula:
    rebate_amount = collateral_required * rebate_rate * loan_days / day_count_basis
    """

    return float(collateral_required * rebate_rate * loan_days / day_count_basis)


def calculate_net_lending_revenue(
    borrow_fee_amount: float,
    rebate_amount: float,
) -> float:
    """Calculate simplified net revenue to lender.

    Formula:
    net_lending_revenue = borrow_fee_amount - rebate_amount

    This convention is intentionally simplified and documented.
    """

    return float(borrow_fee_amount - rebate_amount)


def classify_specialness(
    borrow_fee_rate: float,
    utilization_proxy: float,
    is_special: bool,
) -> str:
    """Classify securities lending specialness.

    Heuristic:
    - Explicit special flag or borrow fee >= 3% or utilization >= 85%: Special / hard-to-borrow
    - Borrow fee >= 1% or utilization >= 60%: Warm / elevated borrow
    - Otherwise: General collateral
    """

    if is_special or borrow_fee_rate >= 0.03 or utilization_proxy >= 0.85:
        return "Special / hard-to-borrow"

    if borrow_fee_rate >= 0.01 or utilization_proxy >= 0.60:
        return "Warm / elevated borrow"

    return "General collateral"


def calculate_securities_lending_trade(
    security_market_value: float,
    borrow_fee_rate: float,
    rebate_rate: float,
    collateralization_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
    utilization_proxy: float = 0.50,
    is_special: bool = False,
) -> SecuritiesLendingResult:
    """Calculate simplified securities lending economics."""

    validate_sec_lending_inputs(
        security_market_value=security_market_value,
        borrow_fee_rate=borrow_fee_rate,
        rebate_rate=rebate_rate,
        collateralization_rate=collateralization_rate,
        loan_days=loan_days,
        day_count_basis=day_count_basis,
        utilization_proxy=utilization_proxy,
    )

    collateral_required = calculate_collateral_required(
        security_market_value=security_market_value,
        collateralization_rate=collateralization_rate,
    )

    borrow_fee_amount = calculate_borrow_fee_amount(
        security_market_value=security_market_value,
        borrow_fee_rate=borrow_fee_rate,
        loan_days=loan_days,
        day_count_basis=day_count_basis,
    )

    rebate_amount = calculate_rebate_amount(
        collateral_required=collateral_required,
        rebate_rate=rebate_rate,
        loan_days=loan_days,
        day_count_basis=day_count_basis,
    )

    net_lending_revenue = calculate_net_lending_revenue(
        borrow_fee_amount=borrow_fee_amount,
        rebate_amount=rebate_amount,
    )

    specialness_label = classify_specialness(
        borrow_fee_rate=borrow_fee_rate,
        utilization_proxy=utilization_proxy,
        is_special=is_special,
    )

    return SecuritiesLendingResult(
        security_market_value=float(security_market_value),
        borrow_fee_rate=float(borrow_fee_rate),
        rebate_rate=float(rebate_rate),
        collateralization_rate=float(collateralization_rate),
        loan_days=int(loan_days),
        day_count_basis=int(day_count_basis),
        utilization_proxy=float(utilization_proxy),
        is_special=bool(is_special),
        collateral_required=float(collateral_required),
        borrow_fee_amount=float(borrow_fee_amount),
        rebate_amount=float(rebate_amount),
        net_lending_revenue=float(net_lending_revenue),
        specialness_label=specialness_label,
    )


def sec_lending_result_to_dict(result: SecuritiesLendingResult) -> dict:
    """Convert SecuritiesLendingResult to dictionary."""

    return asdict(result)


def calculate_borrow_fee_comparison_table(
    security_market_value: float,
    rebate_rate: float,
    collateralization_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> pd.DataFrame:
    """Generate a normal vs special borrow comparison table."""

    scenarios = [
        {
            "scenario": "General collateral",
            "borrow_fee_rate": 0.0025,
            "utilization_proxy": 0.35,
            "is_special": False,
        },
        {
            "scenario": "Warm borrow",
            "borrow_fee_rate": 0.0125,
            "utilization_proxy": 0.65,
            "is_special": False,
        },
        {
            "scenario": "Special borrow",
            "borrow_fee_rate": 0.0400,
            "utilization_proxy": 0.90,
            "is_special": True,
        },
    ]

    rows = []

    for scenario in scenarios:
        result = calculate_securities_lending_trade(
            security_market_value=security_market_value,
            borrow_fee_rate=scenario["borrow_fee_rate"],
            rebate_rate=rebate_rate,
            collateralization_rate=collateralization_rate,
            loan_days=loan_days,
            day_count_basis=day_count_basis,
            utilization_proxy=scenario["utilization_proxy"],
            is_special=scenario["is_special"],
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "borrow_fee_rate": result.borrow_fee_rate,
                "rebate_rate": result.rebate_rate,
                "utilization_proxy": result.utilization_proxy,
                "collateral_required": result.collateral_required,
                "borrow_fee_amount": result.borrow_fee_amount,
                "rebate_amount": result.rebate_amount,
                "net_lending_revenue": result.net_lending_revenue,
                "specialness_label": result.specialness_label,
            }
        )

    return pd.DataFrame(rows)


def generate_sec_lending_commentary(result: SecuritiesLendingResult) -> list[str]:
    """Generate desk-style commentary for securities lending analytics."""

    comments = [
        f"Specialness classification: {result.specialness_label}.",
        (
            f"Collateral required is {result.collateralization_rate:.2%} of security market value, "
            f"equal to {result.collateral_required:,.0f}."
        ),
        (
            f"Borrow fee amount over {result.loan_days} days is {result.borrow_fee_amount:,.0f}; "
            f"rebate amount is {result.rebate_amount:,.0f}."
        ),
        (
            f"Simplified net lending revenue is {result.net_lending_revenue:,.0f} "
            "under the project convention."
        ),
    ]

    if result.specialness_label == "Special / hard-to-borrow":
        comments.append(
            "The security screens as special or hard-to-borrow, usually implying higher borrow cost and stronger demand for the lendable asset."
        )
    elif result.specialness_label == "Warm / elevated borrow":
        comments.append(
            "Borrow conditions are elevated versus general collateral but do not screen as fully special under this heuristic."
        )
    else:
        comments.append(
            "Borrow conditions are consistent with general collateral under this simplified heuristic."
        )

    comments.append(
        "This is a simplified securities lending analytics proxy and does not model recall risk, dividend events, settlement, or counterparty default."
    )

    return comments
