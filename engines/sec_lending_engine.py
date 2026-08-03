"""
Securities Lending Engine.

This module separates mutually exclusive securities-lending revenue paths.

Financial conventions:
- Non-cash collateral: gross lender revenue is the securities loan fee.
- Cash collateral: gross lender revenue is reinvestment income less the cash rebate.
- The two paths are never combined automatically.
- Agent fee share is applied only to positive gross lender revenue.
- Perspective is either the beneficial owner or the lending agent.
- Net revenue is reported for the selected perspective after perspective-specific costs.

This remains a simplified educational proxy. It does not model legal agreements,
manufactured dividends, recall risk, reinvestment losses beyond the entered yield,
settlement, counterparty default, tax, indemnification, or balance-sheet charges.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import pandas as pd


SUPPORTED_COLLATERAL_TYPES = ("Non-cash", "Cash")
SUPPORTED_PERSPECTIVES = ("Beneficial owner", "Lending agent")


@dataclass(frozen=True)
class SecuritiesLendingResult:
    """Simplified but internally coherent securities-lending economics."""

    security_market_value: float
    collateral_type: str
    perspective: str
    borrow_fee_rate: float
    rebate_rate: float
    reinvestment_yield: float
    collateralization_rate: float
    loan_days: int
    day_count_basis: int
    utilization_proxy: float
    is_special: bool
    agent_fee_share: float
    other_costs: float
    collateral_required: float
    borrow_fee_amount: float
    rebate_amount: float
    reinvestment_income: float
    gross_lending_revenue: float
    agent_fee_amount: float
    net_lending_revenue: float
    specialness_label: str
    revenue_convention: str


def _validate_finite(name: str, value: float) -> float:
    """Return a finite float or raise a clear validation error."""
    numeric = float(value)

    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite.")

    return numeric


def validate_sec_lending_inputs(
    security_market_value: float,
    collateral_type: str,
    perspective: str,
    borrow_fee_rate: float,
    rebate_rate: float,
    reinvestment_yield: float,
    collateralization_rate: float,
    loan_days: int,
    day_count_basis: int,
    utilization_proxy: float,
    agent_fee_share: float,
    other_costs: float,
) -> None:
    """Validate path-specific securities-lending inputs."""
    security_market_value = _validate_finite(
        "Security market value",
        security_market_value,
    )
    borrow_fee_rate = _validate_finite(
        "Borrow fee rate",
        borrow_fee_rate,
    )
    rebate_rate = _validate_finite(
        "Rebate rate",
        rebate_rate,
    )
    reinvestment_yield = _validate_finite(
        "Reinvestment yield",
        reinvestment_yield,
    )
    collateralization_rate = _validate_finite(
        "Collateralization rate",
        collateralization_rate,
    )
    utilization_proxy = _validate_finite(
        "Utilization proxy",
        utilization_proxy,
    )
    agent_fee_share = _validate_finite(
        "Agent fee share",
        agent_fee_share,
    )
    other_costs = _validate_finite(
        "Other costs",
        other_costs,
    )

    if security_market_value <= 0:
        raise ValueError("Security market value must be positive.")

    if collateral_type not in SUPPORTED_COLLATERAL_TYPES:
        raise ValueError(
            "Collateral type must be 'Non-cash' or 'Cash'."
        )

    if perspective not in SUPPORTED_PERSPECTIVES:
        raise ValueError(
            "Perspective must be 'Beneficial owner' or "
            "'Lending agent'."
        )

    if borrow_fee_rate < 0:
        raise ValueError("Borrow fee rate cannot be negative.")

    if collateralization_rate <= 0:
        raise ValueError("Collateralization rate must be positive.")

    if int(loan_days) <= 0:
        raise ValueError("Loan days must be positive.")

    if int(day_count_basis) not in {360, 365}:
        raise ValueError("Day-count basis must be 360 or 365.")

    if not 0 <= utilization_proxy <= 1:
        raise ValueError(
            "Utilization proxy must be between 0 and 1."
        )

    if not 0 <= agent_fee_share <= 1:
        raise ValueError(
            "Agent fee share must be between 0 and 1."
        )

    if other_costs < 0:
        raise ValueError("Other costs cannot be negative.")

    tolerance = 1e-15

    if collateral_type == "Non-cash":
        if abs(rebate_rate) > tolerance:
            raise ValueError(
                "Rebate rate must be zero for non-cash collateral."
            )
        if abs(reinvestment_yield) > tolerance:
            raise ValueError(
                "Reinvestment yield must be zero for non-cash "
                "collateral."
            )

    if collateral_type == "Cash" and abs(borrow_fee_rate) > tolerance:
        raise ValueError(
            "Borrow fee rate must be zero for cash collateral. "
            "Cash economics use reinvestment yield less rebate."
        )


def calculate_collateral_required(
    security_market_value: float,
    collateralization_rate: float,
) -> float:
    """Calculate required collateral market value."""
    return float(
        security_market_value
        * collateralization_rate
    )


def calculate_borrow_fee_amount(
    security_market_value: float,
    borrow_fee_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate non-cash securities loan fee income."""
    return float(
        security_market_value
        * borrow_fee_rate
        * loan_days
        / day_count_basis
    )


def calculate_rebate_amount(
    collateral_required: float,
    rebate_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate cash rebate paid to the borrower."""
    return float(
        collateral_required
        * rebate_rate
        * loan_days
        / day_count_basis
    )


def calculate_reinvestment_income(
    collateral_required: float,
    reinvestment_yield: float,
    loan_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate income earned from reinvesting cash collateral."""
    return float(
        collateral_required
        * reinvestment_yield
        * loan_days
        / day_count_basis
    )


def calculate_revenue_waterfall(
    collateral_type: str,
    perspective: str,
    borrow_fee_amount: float = 0.0,
    rebate_amount: float = 0.0,
    reinvestment_income: float = 0.0,
    agent_fee_share: float = 0.0,
    other_costs: float = 0.0,
) -> tuple[float, float, float]:
    """
    Calculate gross revenue, agent fee and net selected-perspective revenue.

    Non-cash:
        gross lender revenue = securities loan fee.

    Cash:
        gross lender revenue = reinvestment income - rebate.

    Beneficial owner:
        net = gross lender revenue - agent fee - other costs.

    Lending agent:
        net = agent fee - other costs.
    """
    if collateral_type not in SUPPORTED_COLLATERAL_TYPES:
        raise ValueError(
            "Collateral type must be 'Non-cash' or 'Cash'."
        )

    if perspective not in SUPPORTED_PERSPECTIVES:
        raise ValueError(
            "Unsupported securities-lending perspective."
        )

    if not 0 <= float(agent_fee_share) <= 1:
        raise ValueError(
            "Agent fee share must be between 0 and 1."
        )

    if float(other_costs) < 0:
        raise ValueError("Other costs cannot be negative.")

    tolerance = 1e-12

    if collateral_type == "Non-cash":
        if (
            abs(float(rebate_amount)) > tolerance
            or abs(float(reinvestment_income)) > tolerance
        ):
            raise ValueError(
                "Non-cash economics cannot include rebate or "
                "cash reinvestment income."
            )
        gross_revenue = float(borrow_fee_amount)
    else:
        if abs(float(borrow_fee_amount)) > tolerance:
            raise ValueError(
                "Cash-collateral economics cannot include a "
                "securities loan fee."
            )
        gross_revenue = float(
            reinvestment_income
            - rebate_amount
        )

    agent_fee_amount = float(
        max(gross_revenue, 0.0)
        * agent_fee_share
    )

    if perspective == "Beneficial owner":
        net_revenue = float(
            gross_revenue
            - agent_fee_amount
            - other_costs
        )
    else:
        net_revenue = float(
            agent_fee_amount
            - other_costs
        )

    return (
        gross_revenue,
        agent_fee_amount,
        net_revenue,
    )


def calculate_net_lending_revenue(
    collateral_type: str,
    perspective: str,
    borrow_fee_amount: float = 0.0,
    rebate_amount: float = 0.0,
    reinvestment_income: float = 0.0,
    agent_fee_share: float = 0.0,
    other_costs: float = 0.0,
) -> float:
    """Return net revenue under an explicit collateral path."""
    _, _, net_revenue = calculate_revenue_waterfall(
        collateral_type=collateral_type,
        perspective=perspective,
        borrow_fee_amount=borrow_fee_amount,
        rebate_amount=rebate_amount,
        reinvestment_income=reinvestment_income,
        agent_fee_share=agent_fee_share,
        other_costs=other_costs,
    )

    return net_revenue


def classify_specialness(
    borrow_fee_rate: float,
    utilization_proxy: float,
    is_special: bool,
) -> str:
    """
    Apply an explicitly heuristic specialness classification.

    This label is illustrative and is not calibrated to live inventory,
    availability, concentration, term, or recall probability.
    """
    if (
        is_special
        or borrow_fee_rate >= 0.03
        or utilization_proxy >= 0.85
    ):
        return "Special / hard-to-borrow"

    if (
        borrow_fee_rate >= 0.01
        or utilization_proxy >= 0.60
    ):
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
    collateral_type: str = "Non-cash",
    reinvestment_yield: float = 0.0,
    perspective: str = "Beneficial owner",
    agent_fee_share: float = 0.0,
    other_costs: float = 0.0,
) -> SecuritiesLendingResult:
    """Calculate one coherent securities-lending revenue path."""
    validate_sec_lending_inputs(
        security_market_value=security_market_value,
        collateral_type=collateral_type,
        perspective=perspective,
        borrow_fee_rate=borrow_fee_rate,
        rebate_rate=rebate_rate,
        reinvestment_yield=reinvestment_yield,
        collateralization_rate=collateralization_rate,
        loan_days=loan_days,
        day_count_basis=day_count_basis,
        utilization_proxy=utilization_proxy,
        agent_fee_share=agent_fee_share,
        other_costs=other_costs,
    )

    collateral_required = calculate_collateral_required(
        security_market_value=security_market_value,
        collateralization_rate=collateralization_rate,
    )

    if collateral_type == "Non-cash":
        borrow_fee_amount = calculate_borrow_fee_amount(
            security_market_value=security_market_value,
            borrow_fee_rate=borrow_fee_rate,
            loan_days=loan_days,
            day_count_basis=day_count_basis,
        )
        rebate_amount = 0.0
        reinvestment_income = 0.0
        revenue_convention = (
            "Non-cash collateral: loan value × fee × "
            "days / day-count basis."
        )
    else:
        borrow_fee_amount = 0.0
        rebate_amount = calculate_rebate_amount(
            collateral_required=collateral_required,
            rebate_rate=rebate_rate,
            loan_days=loan_days,
            day_count_basis=day_count_basis,
        )
        reinvestment_income = calculate_reinvestment_income(
            collateral_required=collateral_required,
            reinvestment_yield=reinvestment_yield,
            loan_days=loan_days,
            day_count_basis=day_count_basis,
        )
        revenue_convention = (
            "Cash collateral: collateral × "
            "(reinvestment yield - rebate) × "
            "days / day-count basis."
        )

    (
        gross_lending_revenue,
        agent_fee_amount,
        net_lending_revenue,
    ) = calculate_revenue_waterfall(
        collateral_type=collateral_type,
        perspective=perspective,
        borrow_fee_amount=borrow_fee_amount,
        rebate_amount=rebate_amount,
        reinvestment_income=reinvestment_income,
        agent_fee_share=agent_fee_share,
        other_costs=other_costs,
    )

    specialness_label = classify_specialness(
        borrow_fee_rate=borrow_fee_rate,
        utilization_proxy=utilization_proxy,
        is_special=is_special,
    )

    return SecuritiesLendingResult(
        security_market_value=float(security_market_value),
        collateral_type=collateral_type,
        perspective=perspective,
        borrow_fee_rate=float(borrow_fee_rate),
        rebate_rate=float(rebate_rate),
        reinvestment_yield=float(reinvestment_yield),
        collateralization_rate=float(collateralization_rate),
        loan_days=int(loan_days),
        day_count_basis=int(day_count_basis),
        utilization_proxy=float(utilization_proxy),
        is_special=bool(is_special),
        agent_fee_share=float(agent_fee_share),
        other_costs=float(other_costs),
        collateral_required=float(collateral_required),
        borrow_fee_amount=float(borrow_fee_amount),
        rebate_amount=float(rebate_amount),
        reinvestment_income=float(reinvestment_income),
        gross_lending_revenue=float(gross_lending_revenue),
        agent_fee_amount=float(agent_fee_amount),
        net_lending_revenue=float(net_lending_revenue),
        specialness_label=specialness_label,
        revenue_convention=revenue_convention,
    )


def sec_lending_result_to_dict(
    result: SecuritiesLendingResult,
) -> dict:
    """Convert SecuritiesLendingResult to a report-ready dictionary."""
    return asdict(result)


def calculate_borrow_fee_comparison_table(
    security_market_value: float,
    rebate_rate: float,
    collateralization_rate: float,
    loan_days: int,
    day_count_basis: int = 360,
    collateral_type: str = "Non-cash",
    reinvestment_yield: float = 0.0,
    perspective: str = "Beneficial owner",
    agent_fee_share: float = 0.0,
    other_costs: float = 0.0,
    utilization_proxy: float = 0.50,
) -> pd.DataFrame:
    """Generate path-specific securities-lending economics scenarios."""
    rows: list[dict] = []

    if collateral_type == "Non-cash":
        scenarios = [
            ("General collateral", 0.0025, 0.35, False),
            ("Warm borrow", 0.0125, 0.65, False),
            ("Special borrow", 0.0400, 0.90, True),
        ]

        for (
            scenario_name,
            scenario_fee,
            scenario_utilization,
            scenario_special,
        ) in scenarios:
            result = calculate_securities_lending_trade(
                security_market_value=security_market_value,
                borrow_fee_rate=scenario_fee,
                rebate_rate=0.0,
                reinvestment_yield=0.0,
                collateralization_rate=collateralization_rate,
                loan_days=loan_days,
                day_count_basis=day_count_basis,
                utilization_proxy=scenario_utilization,
                is_special=scenario_special,
                collateral_type="Non-cash",
                perspective=perspective,
                agent_fee_share=agent_fee_share,
                other_costs=other_costs,
            )

            rows.append(
                {
                    "scenario": scenario_name,
                    **sec_lending_result_to_dict(result),
                }
            )
    elif collateral_type == "Cash":
        scenarios = [
            (
                "Reinvestment yield -50 bp",
                reinvestment_yield - 0.0050,
            ),
            (
                "Base reinvestment yield",
                reinvestment_yield,
            ),
            (
                "Reinvestment yield +50 bp",
                reinvestment_yield + 0.0050,
            ),
        ]

        for scenario_name, scenario_yield in scenarios:
            result = calculate_securities_lending_trade(
                security_market_value=security_market_value,
                borrow_fee_rate=0.0,
                rebate_rate=rebate_rate,
                reinvestment_yield=scenario_yield,
                collateralization_rate=collateralization_rate,
                loan_days=loan_days,
                day_count_basis=day_count_basis,
                utilization_proxy=utilization_proxy,
                is_special=False,
                collateral_type="Cash",
                perspective=perspective,
                agent_fee_share=agent_fee_share,
                other_costs=other_costs,
            )

            rows.append(
                {
                    "scenario": scenario_name,
                    **sec_lending_result_to_dict(result),
                }
            )
    else:
        raise ValueError(
            "Collateral type must be 'Non-cash' or 'Cash'."
        )

    return pd.DataFrame(rows)


def generate_sec_lending_commentary(
    result: SecuritiesLendingResult,
) -> list[str]:
    """Generate desk-style, convention-specific commentary."""
    comments = [
        (
            f"Collateral path: {result.collateral_type}; "
            f"reported perspective: {result.perspective}."
        ),
        (
            f"Collateral required is "
            f"{result.collateralization_rate:.2%} of security "
            f"market value, equal to "
            f"{result.collateral_required:,.0f}."
        ),
    ]

    if result.collateral_type == "Non-cash":
        comments.append(
            (
                f"Non-cash fee income over {result.loan_days} days "
                f"is {result.borrow_fee_amount:,.0f}. Rebate and "
                "cash reinvestment income are excluded."
            )
        )
    else:
        comments.append(
            (
                f"Cash reinvestment income is "
                f"{result.reinvestment_income:,.0f} and rebate paid "
                f"is {result.rebate_amount:,.0f}; gross cash spread "
                f"revenue is {result.gross_lending_revenue:,.0f}."
            )
        )

    comments.extend(
        [
            (
                f"Agent fee is {result.agent_fee_amount:,.0f} at a "
                f"{result.agent_fee_share:.2%} share; entered "
                f"perspective-specific costs are "
                f"{result.other_costs:,.0f}."
            ),
            (
                f"Net revenue to the selected perspective is "
                f"{result.net_lending_revenue:,.0f}."
            ),
            (
                f"Specialness classification: "
                f"{result.specialness_label}. This is an "
                "illustrative heuristic, not a live inventory or "
                "availability model."
            ),
            (
                "This proxy excludes recall risk, manufactured "
                "dividends, settlement, counterparty default, tax, "
                "indemnification and full cash-collateral "
                "reinvestment risk."
            ),
        ]
    )

    return comments
