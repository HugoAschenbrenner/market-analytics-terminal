"""
Structured Products Engine.

This module implements simplified deterministic payoff analytics for
Athena and Phoenix autocallable products.

Financial conventions:
- nominal is the invested notional.
- performance values are decimal total returns versus initial level.
  Example: -20% = -0.20, +5% = 0.05.
- barrier levels are expressed as decimal performance thresholds versus initial.
  Example: autocall barrier at 100% of initial = 0.00 performance threshold.
  Example: protection barrier at 60% of initial = -0.40 performance threshold.
- coupon_rate_per_period is decimal, e.g. 2% = 0.02.
- Worst-of performance is the minimum performance across basket underlyings.

Simplified product logic:
Athena:
- If performance >= autocall barrier on an observation date, product redeems early.
- Autocall payoff = nominal + nominal * coupon_rate_per_period * observation_number.
- If never autocalled and final performance >= protection barrier, nominal is repaid.
- If final performance < protection barrier, capital loss follows final performance.

Phoenix:
- Coupon is paid on each observation date if performance >= coupon barrier.
- With memory coupon enabled, missed coupons accrue and are paid when coupon condition is later met.
- If performance >= autocall barrier, product redeems early after coupon logic.
- If never autocalled and final performance >= protection barrier, nominal is repaid.
- If final performance < protection barrier, capital loss follows final performance.

Important limitation:
This is deterministic payoff logic, not a bank-grade pricing model.
It does not model stochastic volatility, dividends, rates, issuer credit risk,
secondary market liquidity, funding, or full Monte Carlo pricing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd


ProductType = Literal["Athena", "Phoenix"]


@dataclass(frozen=True)
class AutocallableTerms:
    """Autocallable product terms."""

    product_type: ProductType
    nominal: float
    coupon_rate_per_period: float
    autocall_barrier: float
    coupon_barrier: float
    protection_barrier: float
    memory_coupon: bool


@dataclass(frozen=True)
class PayoffResult:
    """Autocallable payoff result."""

    product_type: str
    autocalled: bool
    autocall_observation: int | None
    final_performance: float
    total_coupons_paid: float
    redemption_amount: float
    capital_pnl: float
    total_payoff: float
    total_pnl: float
    payoff_return: float
    protection_barrier_breached: bool
    explanation: str


def validate_terms(terms: AutocallableTerms) -> None:
    """Validate product terms."""

    if terms.product_type not in ["Athena", "Phoenix"]:
        raise ValueError("Product type must be 'Athena' or 'Phoenix'.")

    if terms.nominal <= 0:
        raise ValueError("Nominal must be positive.")

    if terms.coupon_rate_per_period < 0:
        raise ValueError("Coupon rate cannot be negative.")

    if terms.autocall_barrier < terms.protection_barrier:
        raise ValueError("Autocall barrier should be above protection barrier.")

    if terms.coupon_barrier < terms.protection_barrier:
        raise ValueError("Coupon barrier should be above protection barrier.")


def validate_performance_path(performance_path: list[float]) -> None:
    """Validate deterministic performance path."""

    if not performance_path:
        raise ValueError("Performance path cannot be empty.")

    for performance in performance_path:
        if performance <= -1.0:
            raise ValueError("Performance cannot be less than or equal to -100%.")


def calculate_worst_of_performance(underlying_performances: list[float]) -> float:
    """Calculate worst-of performance for a basket."""

    if not underlying_performances:
        raise ValueError("Underlying performances cannot be empty.")

    return float(min(underlying_performances))


def is_autocall_triggered(performance: float, autocall_barrier: float) -> bool:
    """Check whether autocall condition is triggered."""

    return performance >= autocall_barrier


def is_coupon_paid(performance: float, coupon_barrier: float) -> bool:
    """Check whether coupon condition is met."""

    return performance >= coupon_barrier


def is_protection_breached(final_performance: float, protection_barrier: float) -> bool:
    """Check whether capital protection barrier is breached at maturity."""

    return final_performance < protection_barrier


def calculate_capital_redemption(
    nominal: float,
    final_performance: float,
    protection_barrier: float,
) -> float:
    """Calculate maturity capital redemption.

    If final performance is below protection barrier, the investor participates
    directly in the final underlying loss.

    Example:
    nominal = 1,000,000
    final performance = -50%
    redemption = 500,000
    """

    if is_protection_breached(final_performance, protection_barrier):
        return float(nominal * (1.0 + final_performance))

    return float(nominal)


def calculate_athena_payoff(
    terms: AutocallableTerms,
    performance_path: list[float],
) -> PayoffResult:
    """Calculate simplified Athena payoff."""

    validate_terms(terms)
    validate_performance_path(performance_path)

    if terms.product_type != "Athena":
        raise ValueError("Terms product_type must be Athena.")

    for idx, performance in enumerate(performance_path, start=1):
        if is_autocall_triggered(performance, terms.autocall_barrier):
            total_coupons = terms.nominal * terms.coupon_rate_per_period * idx
            redemption_amount = terms.nominal
            total_payoff = redemption_amount + total_coupons
            total_pnl = total_payoff - terms.nominal

            return PayoffResult(
                product_type=terms.product_type,
                autocalled=True,
                autocall_observation=idx,
                final_performance=float(performance),
                total_coupons_paid=float(total_coupons),
                redemption_amount=float(redemption_amount),
                capital_pnl=0.0,
                total_payoff=float(total_payoff),
                total_pnl=float(total_pnl),
                payoff_return=float(total_pnl / terms.nominal),
                protection_barrier_breached=False,
                explanation=(
                    f"Athena autocalled at observation {idx}. Investor receives nominal plus accumulated coupon."
                ),
            )

    final_performance = performance_path[-1]
    redemption_amount = calculate_capital_redemption(
        nominal=terms.nominal,
        final_performance=final_performance,
        protection_barrier=terms.protection_barrier,
    )

    protection_breached = is_protection_breached(
        final_performance=final_performance,
        protection_barrier=terms.protection_barrier,
    )

    total_coupons = 0.0
    total_payoff = redemption_amount + total_coupons
    total_pnl = total_payoff - terms.nominal

    if protection_breached:
        explanation = "Athena did not autocall and final performance breached the protection barrier. Capital loss applies."
    else:
        explanation = "Athena did not autocall but final performance stayed above protection barrier. Nominal is repaid."

    return PayoffResult(
        product_type=terms.product_type,
        autocalled=False,
        autocall_observation=None,
        final_performance=float(final_performance),
        total_coupons_paid=float(total_coupons),
        redemption_amount=float(redemption_amount),
        capital_pnl=float(redemption_amount - terms.nominal),
        total_payoff=float(total_payoff),
        total_pnl=float(total_pnl),
        payoff_return=float(total_pnl / terms.nominal),
        protection_barrier_breached=bool(protection_breached),
        explanation=explanation,
    )


def calculate_phoenix_payoff(
    terms: AutocallableTerms,
    performance_path: list[float],
) -> PayoffResult:
    """Calculate simplified Phoenix payoff."""

    validate_terms(terms)
    validate_performance_path(performance_path)

    if terms.product_type != "Phoenix":
        raise ValueError("Terms product_type must be Phoenix.")

    total_coupons = 0.0
    missed_coupons = 0

    for idx, performance in enumerate(performance_path, start=1):
        if is_coupon_paid(performance, terms.coupon_barrier):
            if terms.memory_coupon:
                coupons_paid_now = terms.nominal * terms.coupon_rate_per_period * (1 + missed_coupons)
                missed_coupons = 0
            else:
                coupons_paid_now = terms.nominal * terms.coupon_rate_per_period

            total_coupons += coupons_paid_now
        else:
            if terms.memory_coupon:
                missed_coupons += 1

        if is_autocall_triggered(performance, terms.autocall_barrier):
            redemption_amount = terms.nominal
            total_payoff = redemption_amount + total_coupons
            total_pnl = total_payoff - terms.nominal

            return PayoffResult(
                product_type=terms.product_type,
                autocalled=True,
                autocall_observation=idx,
                final_performance=float(performance),
                total_coupons_paid=float(total_coupons),
                redemption_amount=float(redemption_amount),
                capital_pnl=0.0,
                total_payoff=float(total_payoff),
                total_pnl=float(total_pnl),
                payoff_return=float(total_pnl / terms.nominal),
                protection_barrier_breached=False,
                explanation=(
                    f"Phoenix autocalled at observation {idx}. Investor receives nominal plus coupons paid before or at autocall."
                ),
            )

    final_performance = performance_path[-1]
    redemption_amount = calculate_capital_redemption(
        nominal=terms.nominal,
        final_performance=final_performance,
        protection_barrier=terms.protection_barrier,
    )

    protection_breached = is_protection_breached(
        final_performance=final_performance,
        protection_barrier=terms.protection_barrier,
    )

    total_payoff = redemption_amount + total_coupons
    total_pnl = total_payoff - terms.nominal

    if protection_breached:
        explanation = "Phoenix did not autocall and final performance breached the protection barrier. Capital loss applies."
    else:
        explanation = "Phoenix did not autocall but final performance stayed above protection barrier. Nominal is repaid."

    return PayoffResult(
        product_type=terms.product_type,
        autocalled=False,
        autocall_observation=None,
        final_performance=float(final_performance),
        total_coupons_paid=float(total_coupons),
        redemption_amount=float(redemption_amount),
        capital_pnl=float(redemption_amount - terms.nominal),
        total_payoff=float(total_payoff),
        total_pnl=float(total_pnl),
        payoff_return=float(total_pnl / terms.nominal),
        protection_barrier_breached=bool(protection_breached),
        explanation=explanation,
    )


def calculate_autocallable_payoff(
    terms: AutocallableTerms,
    performance_path: list[float],
) -> PayoffResult:
    """Route payoff calculation by product type."""

    if terms.product_type == "Athena":
        return calculate_athena_payoff(terms, performance_path)

    if terms.product_type == "Phoenix":
        return calculate_phoenix_payoff(terms, performance_path)

    raise ValueError("Unknown product type.")


def payoff_result_to_dict(result: PayoffResult) -> dict:
    """Convert PayoffResult to dictionary."""

    return asdict(result)


def build_standard_scenario_paths(number_of_observations: int) -> dict[str, list[float]]:
    """Build deterministic scenario paths for display and testing."""

    if number_of_observations <= 0:
        raise ValueError("Number of observations must be positive.")

    return {
        "Early autocall": [0.05] + [0.00] * (number_of_observations - 1),
        "Late autocall": [-0.10] * max(number_of_observations - 1, 0) + [0.02],
        "No autocall / capital protected": [-0.10] * max(number_of_observations - 1, 0) + [-0.20],
        "Barrier breach / capital loss": [-0.20] * max(number_of_observations - 1, 0) + [-0.50],
        "Deep downside": [-0.25] * max(number_of_observations - 1, 0) + [-0.70],
    }


def calculate_scenario_table(
    terms: AutocallableTerms,
    scenario_paths: dict[str, list[float]],
) -> pd.DataFrame:
    """Calculate payoff table for deterministic scenarios."""

    rows = []

    for scenario_name, path in scenario_paths.items():
        result = calculate_autocallable_payoff(terms, path)

        rows.append(
            {
                "scenario": scenario_name,
                "path": ", ".join([f"{x:.0%}" for x in path]),
                "autocalled": result.autocalled,
                "autocall_observation": result.autocall_observation,
                "final_performance": result.final_performance,
                "total_coupons_paid": result.total_coupons_paid,
                "redemption_amount": result.redemption_amount,
                "capital_pnl": result.capital_pnl,
                "total_payoff": result.total_payoff,
                "total_pnl": result.total_pnl,
                "payoff_return": result.payoff_return,
                "protection_barrier_breached": result.protection_barrier_breached,
                "explanation": result.explanation,
            }
        )

    return pd.DataFrame(rows)


def generate_structured_product_commentary(
    terms: AutocallableTerms,
    result: PayoffResult,
) -> list[str]:
    """Generate concise structured product commentary."""

    comments = []

    if result.autocalled:
        comments.append(
            f"{terms.product_type} autocalled at observation {result.autocall_observation}; investor receives nominal plus coupons."
        )
    else:
        comments.append(f"{terms.product_type} did not autocall over the selected performance path.")

    if result.protection_barrier_breached:
        comments.append(
            "Protection barrier was breached at maturity; capital loss is linked to final underlying performance."
        )
    else:
        comments.append("Protection barrier was not breached at maturity or product autocalled before maturity.")

    comments.append(
        f"Total payoff is {result.total_payoff:,.0f}, implying total P&L of {result.total_pnl:,.0f} "
        f"and payoff return of {result.payoff_return:.2%}."
    )

    if terms.product_type == "Phoenix":
        if terms.memory_coupon:
            comments.append("Memory coupon is enabled: missed coupons can be recovered if the coupon condition is later met.")
        else:
            comments.append("Memory coupon is disabled: missed coupons are not recovered.")

    comments.append(
        "This is deterministic payoff logic only, not a pricing model or investment recommendation."
    )

    return comments
