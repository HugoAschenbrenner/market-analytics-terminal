"""
Structured products Monte Carlo valuation proxy engine.

This module provides a simplified valuation proxy for autocallable structured
products. It is designed for educational/demo use and structuring intuition.

It is not an issuer pricing library, not a bank-grade valuation engine, and not
a replacement for calibrated volatility surfaces, funding curves, dividend
forecasts, credit adjustments, or official term sheets.

Core purpose:
- estimate expected discounted payoff
- estimate autocall probability
- estimate protection barrier breach probability
- estimate expected maturity
- generate desk-style valuation interpretation
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import exp
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


DISCLAIMER = (
    "Autocallable valuation outputs are simplified Monte Carlo proxies for educational "
    "and demo use only. They do not use calibrated volatility surfaces, issuer funding "
    "curves, dividend forecasts, credit adjustments, liquidity costs, or executable "
    "market quotes. Not investment advice or bank-grade pricing."
)


@dataclass(frozen=True)
class AutocallableValuationInputs:
    """Inputs for simplified autocallable Monte Carlo valuation."""

    notional: float = 1000.0
    initial_spots: tuple[float, ...] = (100.0,)
    volatilities: tuple[float, ...] = (0.20,)
    correlation: float = 0.30
    maturity_years: float = 3.0
    observations_per_year: int = 1
    autocall_barrier: float = 1.00
    coupon_barrier: float = 0.70
    protection_barrier: float = 0.60
    coupon_rate: float = 0.08
    risk_free_rate: float = 0.03
    dividend_yield: float = 0.00
    simulations: int = 10000
    seed: Optional[int] = 42


def _as_positive_tuple(values: Iterable[float], field_name: str) -> tuple[float, ...]:
    cleaned = tuple(float(value) for value in values)

    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")

    if any(value <= 0 for value in cleaned):
        raise ValueError(f"All {field_name} values must be strictly positive.")

    return cleaned


def validate_valuation_inputs(
    notional: float = 1000.0,
    initial_spots: Optional[Iterable[float]] = None,
    volatilities: Optional[Iterable[float]] = None,
    correlation: float = 0.30,
    maturity_years: float = 3.0,
    observations_per_year: int = 1,
    autocall_barrier: float = 1.00,
    coupon_barrier: float = 0.70,
    protection_barrier: float = 0.60,
    coupon_rate: float = 0.08,
    risk_free_rate: float = 0.03,
    dividend_yield: float = 0.00,
    simulations: int = 10000,
    seed: Optional[int] = 42,
) -> AutocallableValuationInputs:
    """Validate and normalize autocallable valuation inputs."""
    initial_spots_tuple = _as_positive_tuple(initial_spots or (100.0,), "initial_spots")
    volatilities_tuple = _as_positive_tuple(volatilities or (0.20,), "volatilities")

    if len(initial_spots_tuple) != len(volatilities_tuple):
        raise ValueError("initial_spots and volatilities must have the same length.")

    notional = float(notional)
    correlation = float(correlation)
    maturity_years = float(maturity_years)
    observations_per_year = int(observations_per_year)
    autocall_barrier = float(autocall_barrier)
    coupon_barrier = float(coupon_barrier)
    protection_barrier = float(protection_barrier)
    coupon_rate = float(coupon_rate)
    risk_free_rate = float(risk_free_rate)
    dividend_yield = float(dividend_yield)
    simulations = int(simulations)

    if notional <= 0:
        raise ValueError("notional must be strictly positive.")

    if maturity_years <= 0:
        raise ValueError("maturity_years must be strictly positive.")

    if observations_per_year <= 0:
        raise ValueError("observations_per_year must be strictly positive.")

    if simulations <= 0:
        raise ValueError("simulations must be strictly positive.")

    if not -0.95 <= correlation <= 0.95:
        raise ValueError("correlation must be between -0.95 and 0.95.")

    for name, value in {
        "autocall_barrier": autocall_barrier,
        "coupon_barrier": coupon_barrier,
        "protection_barrier": protection_barrier,
    }.items():
        if value <= 0:
            raise ValueError(f"{name} must be strictly positive.")

    if coupon_rate < 0:
        raise ValueError("coupon_rate cannot be negative.")

    asset_count = len(initial_spots_tuple)

    if asset_count > 1:
        min_constant_corr = -1.0 / (asset_count - 1)
        if correlation <= min_constant_corr:
            raise ValueError(
                "For a constant correlation matrix, correlation must be greater "
                f"than {min_constant_corr:.4f} for {asset_count} assets."
            )

    return AutocallableValuationInputs(
        notional=notional,
        initial_spots=initial_spots_tuple,
        volatilities=volatilities_tuple,
        correlation=correlation,
        maturity_years=maturity_years,
        observations_per_year=observations_per_year,
        autocall_barrier=autocall_barrier,
        coupon_barrier=coupon_barrier,
        protection_barrier=protection_barrier,
        coupon_rate=coupon_rate,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        simulations=simulations,
        seed=seed,
    )


def build_observation_times(inputs: AutocallableValuationInputs) -> np.ndarray:
    """Build contractual observation times in years."""
    observation_count = max(1, int(round(inputs.maturity_years * inputs.observations_per_year)))
    return np.arange(1, observation_count + 1, dtype=float) / inputs.observations_per_year


def build_constant_correlation_matrix(asset_count: int, correlation: float) -> np.ndarray:
    """Build a constant pairwise correlation matrix."""
    asset_count = int(asset_count)
    correlation = float(correlation)

    if asset_count <= 0:
        raise ValueError("asset_count must be strictly positive.")

    if asset_count == 1:
        return np.ones((1, 1))

    matrix = np.full((asset_count, asset_count), correlation, dtype=float)
    np.fill_diagonal(matrix, 1.0)

    eigenvalues = np.linalg.eigvalsh(matrix)

    if np.min(eigenvalues) <= 0:
        raise ValueError("Correlation matrix is not positive definite.")

    return matrix


def simulate_correlated_gbm_performance_paths(
    inputs: AutocallableValuationInputs,
) -> np.ndarray:
    """
    Simulate correlated GBM performance paths.

    Returns an array of shape:
    simulations x observations x assets

    Values are performance ratios S_t / S_0.
    """
    asset_count = len(inputs.initial_spots)
    observation_times = build_observation_times(inputs)
    observation_count = len(observation_times)

    dt = 1.0 / inputs.observations_per_year
    rng = np.random.default_rng(inputs.seed)

    correlation_matrix = build_constant_correlation_matrix(asset_count, inputs.correlation)
    cholesky = np.linalg.cholesky(correlation_matrix)

    performances = np.ones((inputs.simulations, observation_count, asset_count), dtype=float)
    current_log_performance = np.zeros((inputs.simulations, asset_count), dtype=float)

    vol = np.asarray(inputs.volatilities, dtype=float)
    drift = inputs.risk_free_rate - inputs.dividend_yield - 0.5 * vol * vol

    for obs_idx in range(observation_count):
        independent_normals = rng.standard_normal((inputs.simulations, asset_count))
        correlated_normals = independent_normals @ cholesky.T

        current_log_performance = (
            current_log_performance
            + drift * dt
            + vol * np.sqrt(dt) * correlated_normals
        )

        performances[:, obs_idx, :] = np.exp(current_log_performance)

    return performances


def evaluate_autocallable_cashflows(
    performance_paths: np.ndarray,
    inputs: AutocallableValuationInputs,
) -> pd.DataFrame:
    """
    Evaluate autocallable path-level cashflows from simulated performance paths.

    Simplified payoff logic:
    - if worst-of performance >= autocall barrier at an observation date:
      redeem notional plus accrued coupon
    - if not autocalled and final worst-of >= coupon barrier:
      redeem notional plus full maturity coupon
    - if not autocalled and final worst-of >= protection barrier:
      redeem notional only
    - if final worst-of < protection barrier:
      redeem notional multiplied by final worst-of performance
    """
    paths = np.asarray(performance_paths, dtype=float)

    if paths.ndim != 3:
        raise ValueError("performance_paths must have shape simulations x observations x assets.")

    simulation_count, observation_count, _ = paths.shape
    observation_times = build_observation_times(inputs)

    if observation_count != len(observation_times):
        raise ValueError("performance_paths observation count does not match valuation inputs.")

    worst_of_paths = np.min(paths, axis=2)

    rows: List[Dict[str, Any]] = []

    for simulation_index in range(simulation_count):
        worst_path = worst_of_paths[simulation_index]

        autocalled = False
        event_time = float(observation_times[-1])
        event_worst_performance = float(worst_path[-1])
        coupon_paid = 0.0
        payoff = 0.0
        event_type = "maturity"

        for obs_idx, worst_performance in enumerate(worst_path):
            if worst_performance >= inputs.autocall_barrier:
                event_time = float(observation_times[obs_idx])
                event_worst_performance = float(worst_performance)
                coupon_paid = inputs.notional * inputs.coupon_rate * event_time
                payoff = inputs.notional + coupon_paid
                autocalled = True
                event_type = "autocall"
                break

        if not autocalled:
            final_worst = float(worst_path[-1])
            event_worst_performance = final_worst

            if final_worst >= inputs.coupon_barrier:
                coupon_paid = inputs.notional * inputs.coupon_rate * inputs.maturity_years
                payoff = inputs.notional + coupon_paid
                event_type = "maturity_coupon_paid"

            elif final_worst >= inputs.protection_barrier:
                coupon_paid = 0.0
                payoff = inputs.notional
                event_type = "maturity_capital_protected"

            else:
                coupon_paid = 0.0
                payoff = inputs.notional * final_worst
                event_type = "maturity_capital_loss"

        discounted_payoff = payoff * exp(-inputs.risk_free_rate * event_time)

        rows.append(
            {
                "simulation": simulation_index,
                "event_type": event_type,
                "autocalled": autocalled,
                "event_time_years": round(event_time, 6),
                "worst_of_performance": round(event_worst_performance, 8),
                "coupon_paid": round(coupon_paid, 8),
                "payoff": round(payoff, 8),
                "discounted_payoff": round(discounted_payoff, 8),
                "protection_barrier_breached": event_worst_performance < inputs.protection_barrier,
            }
        )

    return pd.DataFrame(rows)


def summarize_autocallable_cashflows(
    cashflows: pd.DataFrame,
    inputs: AutocallableValuationInputs,
) -> Dict[str, Any]:
    """Summarize path-level cashflows into valuation proxy metrics."""
    if cashflows.empty:
        raise ValueError("cashflows cannot be empty.")

    expected_discounted_payoff = float(cashflows["discounted_payoff"].mean())
    expected_payoff = float(cashflows["payoff"].mean())

    summary = {
        "fair_value_proxy": round(expected_discounted_payoff, 6),
        "fair_value_pct_notional": round(expected_discounted_payoff / inputs.notional * 100.0, 4),
        "expected_payoff": round(expected_payoff, 6),
        "expected_payoff_pct_notional": round(expected_payoff / inputs.notional * 100.0, 4),
        "autocall_probability": round(float(cashflows["autocalled"].mean()), 6),
        "protection_barrier_breach_probability": round(
            float(cashflows["protection_barrier_breached"].mean()), 6
        ),
        "expected_maturity_years": round(float(cashflows["event_time_years"].mean()), 6),
        "average_coupon_paid": round(float(cashflows["coupon_paid"].mean()), 6),
        "p05_payoff": round(float(cashflows["payoff"].quantile(0.05)), 6),
        "p50_payoff": round(float(cashflows["payoff"].quantile(0.50)), 6),
        "p95_payoff": round(float(cashflows["payoff"].quantile(0.95)), 6),
        "simulations": int(inputs.simulations),
        "asset_count": len(inputs.initial_spots),
    }

    return summary


def generate_valuation_desk_interpretation(summary: Dict[str, Any], inputs: AutocallableValuationInputs) -> List[str]:
    """Generate desk-style interpretation bullets for the valuation proxy."""
    bullets = [
        (
            f"Fair value proxy is {summary['fair_value_pct_notional']:.2f}% of notional "
            f"under simplified Monte Carlo assumptions."
        ),
        (
            f"Autocall probability is {summary['autocall_probability']:.1%}; "
            f"expected maturity is {summary['expected_maturity_years']:.2f} years."
        ),
        (
            f"Protection barrier breach probability is "
            f"{summary['protection_barrier_breach_probability']:.1%}, driven by the worst-of path."
        ),
    ]

    if summary["fair_value_pct_notional"] < 95:
        bullets.append(
            "Proxy value is materially below par: coupon/barrier terms may not compensate for downside and autocall risk."
        )
    elif summary["fair_value_pct_notional"] > 105:
        bullets.append(
            "Proxy value is above par under the selected assumptions: terms may look investor-favorable in this simplified setup."
        )
    else:
        bullets.append(
            "Proxy value is close to par under the selected assumptions; sensitivity to volatility and correlation should be checked."
        )

    if len(inputs.initial_spots) > 1:
        bullets.append(
            "Worst-of basket structure adds correlation and dispersion risk: lower correlation can increase worst-of downside risk."
        )

    bullets.append("This is a valuation proxy, not issuer pricing or a tradable quote.")

    return bullets


def build_autocallable_valuation_snapshot(
    notional: float = 1000.0,
    initial_spots: Optional[Iterable[float]] = None,
    volatilities: Optional[Iterable[float]] = None,
    correlation: float = 0.30,
    maturity_years: float = 3.0,
    observations_per_year: int = 1,
    autocall_barrier: float = 1.00,
    coupon_barrier: float = 0.70,
    protection_barrier: float = 0.60,
    coupon_rate: float = 0.08,
    risk_free_rate: float = 0.03,
    dividend_yield: float = 0.00,
    simulations: int = 10000,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Build full autocallable valuation proxy payload."""
    inputs = validate_valuation_inputs(
        notional=notional,
        initial_spots=initial_spots,
        volatilities=volatilities,
        correlation=correlation,
        maturity_years=maturity_years,
        observations_per_year=observations_per_year,
        autocall_barrier=autocall_barrier,
        coupon_barrier=coupon_barrier,
        protection_barrier=protection_barrier,
        coupon_rate=coupon_rate,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        simulations=simulations,
        seed=seed,
    )

    paths = simulate_correlated_gbm_performance_paths(inputs)
    cashflows = evaluate_autocallable_cashflows(paths, inputs)
    summary = summarize_autocallable_cashflows(cashflows, inputs)
    desk_interpretation = generate_valuation_desk_interpretation(summary, inputs)

    return {
        "inputs": asdict(inputs),
        "summary": summary,
        "cashflows": cashflows,
        "desk_interpretation": desk_interpretation,
        "disclaimer": DISCLAIMER,
    }


def valuation_summary_to_dataframe(summary: Dict[str, Any]) -> pd.DataFrame:
    """Convert valuation summary into display-friendly table."""
    rows = [
        {"metric": "Fair Value Proxy", "value": summary["fair_value_proxy"]},
        {"metric": "Fair Value (% Notional)", "value": summary["fair_value_pct_notional"]},
        {"metric": "Expected Payoff", "value": summary["expected_payoff"]},
        {"metric": "Autocall Probability", "value": summary["autocall_probability"]},
        {"metric": "Barrier Breach Probability", "value": summary["protection_barrier_breach_probability"]},
        {"metric": "Expected Maturity", "value": summary["expected_maturity_years"]},
        {"metric": "Average Coupon Paid", "value": summary["average_coupon_paid"]},
        {"metric": "5th Percentile Payoff", "value": summary["p05_payoff"]},
        {"metric": "Median Payoff", "value": summary["p50_payoff"]},
        {"metric": "95th Percentile Payoff", "value": summary["p95_payoff"]},
    ]

    return pd.DataFrame(rows)


def build_valuation_sensitivity_table(
    base_inputs: AutocallableValuationInputs,
    volatility_shocks: Optional[Iterable[float]] = None,
    correlation_shocks: Optional[Iterable[float]] = None,
) -> pd.DataFrame:
    """
    Build volatility/correlation sensitivity table.

    volatility_shocks are absolute vol moves, e.g. 0.05 = +5 vol points.
    correlation_shocks are absolute correlation moves.
    """
    vol_moves = list(volatility_shocks if volatility_shocks is not None else [-0.05, 0.0, 0.05])
    corr_moves = list(correlation_shocks if correlation_shocks is not None else [-0.20, 0.0, 0.20])

    rows: List[Dict[str, Any]] = []

    for vol_move in vol_moves:
        shocked_vols = tuple(max(vol + float(vol_move), 0.0001) for vol in base_inputs.volatilities)

        for corr_move in corr_moves:
            shocked_corr = min(max(base_inputs.correlation + float(corr_move), -0.95), 0.95)

            shocked_inputs = replace(
                base_inputs,
                volatilities=shocked_vols,
                correlation=shocked_corr,
            )

            paths = simulate_correlated_gbm_performance_paths(shocked_inputs)
            cashflows = evaluate_autocallable_cashflows(paths, shocked_inputs)
            summary = summarize_autocallable_cashflows(cashflows, shocked_inputs)

            rows.append(
                {
                    "scenario": f"Vol {vol_move * 100:+.0f} pts, Corr {corr_move:+.2f}",
                    "avg_volatility": round(float(np.mean(shocked_vols)), 6),
                    "correlation": round(shocked_corr, 6),
                    "fair_value_pct_notional": summary["fair_value_pct_notional"],
                    "autocall_probability": summary["autocall_probability"],
                    "barrier_breach_probability": summary["protection_barrier_breach_probability"],
                    "expected_maturity_years": summary["expected_maturity_years"],
                }
            )

    return pd.DataFrame(rows)
