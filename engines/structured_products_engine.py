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

# ---------------------------------------------------------------------------
# Step 13: Worst-of basket analytics
# ---------------------------------------------------------------------------

def validate_basket_paths(underlying_paths: dict[str, list[float]]) -> int:
    """Validate basket paths and return number of observations."""

    if not underlying_paths:
        raise ValueError("Underlying paths cannot be empty.")

    lengths = set()

    for underlying, path in underlying_paths.items():
        if not underlying:
            raise ValueError("Underlying name cannot be empty.")

        if not path:
            raise ValueError(f"Performance path for {underlying} cannot be empty.")

        for performance in path:
            if performance <= -1.0:
                raise ValueError("Performance cannot be less than or equal to -100%.")

        lengths.add(len(path))

    if len(lengths) != 1:
        raise ValueError("All underlying paths must have the same number of observations.")

    return lengths.pop()


def calculate_worst_of_path(underlying_paths: dict[str, list[float]]) -> list[float]:
    """Calculate worst-of performance path across multiple underlyings.

    At each observation date, worst-of performance is the minimum performance
    among all underlyings.
    """

    number_of_observations = validate_basket_paths(underlying_paths)

    worst_of_path = []

    for obs_idx in range(number_of_observations):
        obs_performances = [
            path[obs_idx] for path in underlying_paths.values()
        ]
        worst_of_path.append(float(min(obs_performances)))

    return worst_of_path


def identify_worst_performer(underlying_performances: dict[str, float]) -> dict:
    """Identify the worst performer from a dictionary of underlying performances."""

    if not underlying_performances:
        raise ValueError("Underlying performances cannot be empty.")

    worst_name = min(underlying_performances, key=underlying_performances.get)

    return {
        "underlying": worst_name,
        "performance": float(underlying_performances[worst_name]),
    }


def identify_worst_performer_at_maturity(underlying_paths: dict[str, list[float]]) -> dict:
    """Identify worst performer at final observation."""

    validate_basket_paths(underlying_paths)

    final_performances = {
        underlying: path[-1]
        for underlying, path in underlying_paths.items()
    }

    return identify_worst_performer(final_performances)


def _constant_path(number_of_observations: int, interim_value: float, final_value: float) -> list[float]:
    """Build a simple path with repeated interim value and explicit final value."""

    if number_of_observations <= 0:
        raise ValueError("Number of observations must be positive.")

    return [interim_value] * max(number_of_observations - 1, 0) + [final_value]


def build_standard_basket_scenario_paths(
    number_of_observations: int,
) -> dict[str, dict[str, list[float]]]:
    """Build deterministic worst-of basket scenario paths.

    Each scenario contains three underlyings. Product payoff is calculated
    on the worst-of path.
    """

    if number_of_observations <= 0:
        raise ValueError("Number of observations must be positive.")

    return {
        "All names above autocall barrier": {
            "Equity A": [0.05] * number_of_observations,
            "Equity B": [0.03] * number_of_observations,
            "Equity C": [0.01] * number_of_observations,
        },
        "Dispersion / late autocall": {
            "Equity A": _constant_path(number_of_observations, 0.10, 0.04),
            "Equity B": _constant_path(number_of_observations, -0.15, 0.02),
            "Equity C": _constant_path(number_of_observations, -0.05, 0.01),
        },
        "No autocall / protected maturity": {
            "Equity A": _constant_path(number_of_observations, -0.10, -0.20),
            "Equity B": _constant_path(number_of_observations, -0.15, -0.25),
            "Equity C": _constant_path(number_of_observations, -0.20, -0.30),
        },
        "Single-name barrier breach": {
            "Equity A": _constant_path(number_of_observations, -0.10, -0.20),
            "Equity B": _constant_path(number_of_observations, -0.20, -0.50),
            "Equity C": _constant_path(number_of_observations, -0.15, -0.25),
        },
        "Correlated downside shock": {
            "Equity A": _constant_path(number_of_observations, -0.25, -0.55),
            "Equity B": _constant_path(number_of_observations, -0.30, -0.60),
            "Equity C": _constant_path(number_of_observations, -0.20, -0.50),
        },
    }


def calculate_worst_of_basket_payoff(
    terms: AutocallableTerms,
    underlying_paths: dict[str, list[float]],
) -> dict:
    """Calculate payoff using the worst-of path of a basket."""

    worst_of_path = calculate_worst_of_path(underlying_paths)
    payoff_result = calculate_autocallable_payoff(terms, worst_of_path)
    worst_performer = identify_worst_performer_at_maturity(underlying_paths)

    return {
        "worst_of_path": worst_of_path,
        "payoff_result": payoff_result,
        "worst_performer_at_maturity": worst_performer["underlying"],
        "worst_performance_at_maturity": worst_performer["performance"],
    }


def calculate_basket_scenario_table(
    terms: AutocallableTerms,
    basket_scenario_paths: dict[str, dict[str, list[float]]],
) -> pd.DataFrame:
    """Calculate deterministic scenario table for worst-of basket autocallables."""

    rows = []

    for scenario_name, underlying_paths in basket_scenario_paths.items():
        basket_result = calculate_worst_of_basket_payoff(
            terms=terms,
            underlying_paths=underlying_paths,
        )

        payoff = basket_result["payoff_result"]
        worst_of_path = basket_result["worst_of_path"]

        rows.append(
            {
                "scenario": scenario_name,
                "worst_of_path": ", ".join([f"{x:.0%}" for x in worst_of_path]),
                "worst_performer_at_maturity": basket_result["worst_performer_at_maturity"],
                "worst_performance_at_maturity": basket_result["worst_performance_at_maturity"],
                "autocalled": payoff.autocalled,
                "autocall_observation": payoff.autocall_observation,
                "total_coupons_paid": payoff.total_coupons_paid,
                "redemption_amount": payoff.redemption_amount,
                "capital_pnl": payoff.capital_pnl,
                "total_payoff": payoff.total_payoff,
                "total_pnl": payoff.total_pnl,
                "payoff_return": payoff.payoff_return,
                "protection_barrier_breached": payoff.protection_barrier_breached,
                "explanation": payoff.explanation,
            }
        )

    return pd.DataFrame(rows)


def generate_worst_of_basket_commentary(
    terms: AutocallableTerms,
    underlying_paths: dict[str, list[float]],
) -> list[str]:
    """Generate desk-style commentary for worst-of basket autocallables."""

    basket_result = calculate_worst_of_basket_payoff(
        terms=terms,
        underlying_paths=underlying_paths,
    )

    payoff = basket_result["payoff_result"]
    worst_name = basket_result["worst_performer_at_maturity"]
    worst_perf = basket_result["worst_performance_at_maturity"]

    comments = [
        (
            f"Payoff is driven by the worst-of path, not the average basket performance. "
            f"The final worst performer is {worst_name} at {worst_perf:.2%}."
        )
    ]

    if payoff.autocalled:
        comments.append(
            f"The product autocalled at observation {payoff.autocall_observation} because the worst-of performance met the autocall condition."
        )
    else:
        comments.append(
            "The product did not autocall because the worst-of performance did not meet the autocall condition on any observation date."
        )

    if payoff.protection_barrier_breached:
        comments.append(
            "The protection barrier was breached by the worst performer at maturity, so capital loss applies."
        )
    else:
        comments.append(
            "The protection barrier was not breached at maturity, or the product autocalled before maturity."
        )

    comments.append(
        "Worst-of structures are highly sensitive to dispersion: one weak underlying can dominate the payoff even if the rest of the basket performs well."
    )

    comments.append(
        "This is deterministic payoff analytics only, not stochastic pricing or a recommendation."
    )

    return comments

# ---------------------------------------------------------------------------
# Step 14: Monte Carlo simulation layer
# ---------------------------------------------------------------------------

def simulate_single_underlying_paths(
    number_of_observations: int,
    n_simulations: int = 5000,
    initial_level: float = 100.0,
    drift: float = 0.00,
    volatility: float = 0.20,
    maturity_years: float = 1.0,
    seed: int | None = None,
):
    """Simulate single-underlying performance paths using GBM.

    Returns:
    numpy array with shape:
    - rows = simulations
    - columns = observation dates
    - values = performance versus initial level

    This is a simplified risk-neutral/proxy simulation layer. It is not
    calibrated pricing.
    """

    import numpy as np

    if number_of_observations <= 0:
        raise ValueError("Number of observations must be positive.")

    if n_simulations <= 0:
        raise ValueError("Number of simulations must be positive.")

    if initial_level <= 0:
        raise ValueError("Initial level must be positive.")

    if volatility < 0:
        raise ValueError("Volatility cannot be negative.")

    if maturity_years <= 0:
        raise ValueError("Maturity must be positive.")

    rng = np.random.default_rng(seed)

    dt = maturity_years / number_of_observations

    shocks = rng.normal(
        loc=0.0,
        scale=1.0,
        size=(n_simulations, number_of_observations),
    )

    increments = (
        (drift - 0.5 * volatility**2) * dt
        + volatility * (dt**0.5) * shocks
    )

    log_levels = np.log(initial_level) + np.cumsum(increments, axis=1)
    levels = np.exp(log_levels)

    performances = levels / initial_level - 1.0

    return performances


def build_constant_correlation_matrix(
    n_underlyings: int,
    correlation: float,
):
    """Build a constant-correlation matrix."""

    import numpy as np

    if n_underlyings <= 1:
        raise ValueError("Number of underlyings must be greater than 1.")

    lower_bound = -1.0 / (n_underlyings - 1)

    if correlation <= lower_bound or correlation >= 1.0:
        raise ValueError(
            f"Correlation must be greater than {lower_bound:.4f} and lower than 1."
        )

    matrix = np.full((n_underlyings, n_underlyings), correlation)
    np.fill_diagonal(matrix, 1.0)

    return matrix


def simulate_worst_of_basket_paths(
    number_of_observations: int,
    n_underlyings: int = 3,
    n_simulations: int = 5000,
    initial_level: float = 100.0,
    drift: float = 0.00,
    volatility: float = 0.25,
    correlation: float = 0.50,
    maturity_years: float = 1.0,
    seed: int | None = None,
) -> dict:
    """Simulate worst-of basket performance paths with correlated GBM.

    Returns:
    {
        "underlying_performance_paths": array with shape
            (n_simulations, number_of_observations, n_underlyings),
        "worst_of_performance_paths": array with shape
            (n_simulations, number_of_observations)
    }
    """

    import numpy as np

    if number_of_observations <= 0:
        raise ValueError("Number of observations must be positive.")

    if n_underlyings <= 1:
        raise ValueError("Number of underlyings must be greater than 1.")

    if n_simulations <= 0:
        raise ValueError("Number of simulations must be positive.")

    if initial_level <= 0:
        raise ValueError("Initial level must be positive.")

    if volatility < 0:
        raise ValueError("Volatility cannot be negative.")

    if maturity_years <= 0:
        raise ValueError("Maturity must be positive.")

    rng = np.random.default_rng(seed)

    corr_matrix = build_constant_correlation_matrix(
        n_underlyings=n_underlyings,
        correlation=correlation,
    )

    cholesky = np.linalg.cholesky(corr_matrix)

    dt = maturity_years / number_of_observations

    independent_shocks = rng.normal(
        loc=0.0,
        scale=1.0,
        size=(n_simulations, number_of_observations, n_underlyings),
    )

    correlated_shocks = independent_shocks @ cholesky.T

    increments = (
        (drift - 0.5 * volatility**2) * dt
        + volatility * (dt**0.5) * correlated_shocks
    )

    log_levels = np.log(initial_level) + np.cumsum(increments, axis=1)
    levels = np.exp(log_levels)

    underlying_performance_paths = levels / initial_level - 1.0
    worst_of_performance_paths = underlying_performance_paths.min(axis=2)

    return {
        "underlying_performance_paths": underlying_performance_paths,
        "worst_of_performance_paths": worst_of_performance_paths,
    }


def calculate_monte_carlo_results_table(
    terms: AutocallableTerms,
    performance_paths,
) -> pd.DataFrame:
    """Calculate payoff results for simulated performance paths."""

    import numpy as np

    paths = np.asarray(performance_paths)

    if paths.ndim != 2:
        raise ValueError("Performance paths must be a 2D array.")

    rows = []

    for path in paths:
        result = calculate_autocallable_payoff(
            terms=terms,
            performance_path=[float(x) for x in path],
        )

        rows.append(
            {
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
            }
        )

    return pd.DataFrame(rows)


def summarize_monte_carlo_results(results_df: pd.DataFrame) -> dict:
    """Summarize Monte Carlo payoff results."""

    required_columns = {
        "autocalled",
        "protection_barrier_breached",
        "total_payoff",
        "total_pnl",
        "payoff_return",
        "total_coupons_paid",
        "redemption_amount",
    }

    missing = required_columns - set(results_df.columns)
    if missing:
        raise ValueError(f"Missing Monte Carlo result columns: {missing}")

    n = len(results_df)

    if n == 0:
        raise ValueError("Monte Carlo results cannot be empty.")

    return {
        "number_of_simulations": int(n),
        "autocall_probability": float(results_df["autocalled"].mean()),
        "barrier_breach_probability": float(results_df["protection_barrier_breached"].mean()),
        "expected_payoff": float(results_df["total_payoff"].mean()),
        "expected_pnl": float(results_df["total_pnl"].mean()),
        "expected_return": float(results_df["payoff_return"].mean()),
        "payoff_volatility": float(results_df["payoff_return"].std()),
        "expected_coupons": float(results_df["total_coupons_paid"].mean()),
        "expected_redemption": float(results_df["redemption_amount"].mean()),
        "p5_payoff": float(results_df["total_payoff"].quantile(0.05)),
        "p50_payoff": float(results_df["total_payoff"].quantile(0.50)),
        "p95_payoff": float(results_df["total_payoff"].quantile(0.95)),
    }


def generate_monte_carlo_commentary(summary: dict, is_worst_of: bool) -> list[str]:
    """Generate desk-style commentary for Monte Carlo output."""

    structure_label = "worst-of basket" if is_worst_of else "single-underlying"

    comments = [
        (
            f"Monte Carlo proxy ran {summary['number_of_simulations']:,} simulations "
            f"for a {structure_label} autocallable."
        ),
        (
            f"Estimated autocall probability is {summary['autocall_probability']:.2%}; "
            f"estimated barrier breach probability is {summary['barrier_breach_probability']:.2%}."
        ),
        (
            f"Expected payoff is {summary['expected_payoff']:,.0f}, implying expected P&L "
            f"of {summary['expected_pnl']:,.0f} and expected return of {summary['expected_return']:.2%}."
        ),
    ]

    if is_worst_of:
        comments.append(
            "Worst-of simulation is sensitive to both volatility and correlation. Lower correlation can increase dispersion risk because one name may underperform the basket."
        )
    else:
        comments.append(
            "Single-underlying simulation isolates direction, volatility, and barrier risk without basket dispersion."
        )

    comments.append(
        "This is a simplified Monte Carlo proxy, not calibrated pricing, not a fair value, and not investment advice."
    )

    return comments
