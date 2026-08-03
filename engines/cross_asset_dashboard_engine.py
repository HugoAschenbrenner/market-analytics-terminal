"""
Cross-Asset Dashboard Engine.

This module provides a transparent manual/demo cross-asset aggregation layer.

Core contract:
- Every economic stress contribution is first expressed as an amount in one
  explicit base currency.
- Economic P&L is aggregated once and divided by a common portfolio NAV.
- Repo margin and collateral calls are liquidity requirements, not economic
  P&L, and are reported separately.
- Sleeve notionals are non-overlapping allocations of the common NAV.

Important limitation:
The risk scores remain illustrative heuristics. This is not a production risk
aggregation system, a live market dashboard, investment advice, or a trading
signal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CrossAssetRiskInputs:
    """Inputs for the cross-asset manual/demo dashboard."""

    total_dv01: float
    long_end_dv01_share: float
    repo_margin_deficit: float
    collateral_market_value: float
    structured_autocall_probability: float
    structured_barrier_breach_probability: float
    portfolio_var_95: float
    portfolio_cvar_95: float
    max_drawdown: float
    equity_weight: float
    credit_weight: float
    rates_weight: float
    alternatives_weight: float
    base_currency: str = "EUR"
    portfolio_nav: float = 100_000_000.0
    rates_sleeve_notional: float = 30_000_000.0
    structured_products_notional: float = 20_000_000.0
    residual_portfolio_notional: float = 50_000_000.0


@dataclass(frozen=True)
class CrossAssetRiskSummary:
    """Cross-asset summary with explicit NAV and currency context."""

    rates_score: float
    financing_score: float
    structured_products_score: float
    portfolio_score: float
    composite_score: float
    composite_risk_label: str
    dominant_risk_bucket: str
    base_currency: str
    portfolio_nav: float
    allocated_sleeve_notional: float
    unallocated_nav: float
    current_financing_liquidity_requirement: float


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a numeric value between lower and upper bounds."""

    return float(max(lower, min(upper, value)))


def classify_risk_score(score: float) -> str:
    """Classify an illustrative heuristic score."""

    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Critical"


def validate_cross_asset_inputs(inputs: CrossAssetRiskInputs) -> None:
    """Validate the common-NAV and non-overlapping-sleeve contract."""

    if not inputs.base_currency or not inputs.base_currency.strip():
        raise ValueError("Base currency must be provided.")

    if inputs.portfolio_nav <= 0:
        raise ValueError("Portfolio NAV must be strictly positive.")

    non_negative_fields = {
        "repo_margin_deficit": inputs.repo_margin_deficit,
        "collateral_market_value": inputs.collateral_market_value,
        "rates_sleeve_notional": inputs.rates_sleeve_notional,
        "structured_products_notional": inputs.structured_products_notional,
        "residual_portfolio_notional": inputs.residual_portfolio_notional,
    }

    for name, value in non_negative_fields.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative.")

    if inputs.collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    probability_fields = {
        "structured_autocall_probability": inputs.structured_autocall_probability,
        "structured_barrier_breach_probability": inputs.structured_barrier_breach_probability,
        "portfolio_var_95": inputs.portfolio_var_95,
        "portfolio_cvar_95": inputs.portfolio_cvar_95,
        "long_end_dv01_share": inputs.long_end_dv01_share,
    }

    for name, value in probability_fields.items():
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1.")

    if not -1 <= inputs.max_drawdown <= 0:
        raise ValueError("max_drawdown must be between -1 and 0.")

    weights = [
        inputs.equity_weight,
        inputs.credit_weight,
        inputs.rates_weight,
        inputs.alternatives_weight,
    ]

    if any(weight < 0 for weight in weights):
        raise ValueError("Exposure weights cannot be negative.")

    if abs(sum(weights) - 1.0) > 1e-8:
        raise ValueError("Exposure weights must sum to 1.0.")

    allocated_notional = (
        inputs.rates_sleeve_notional
        + inputs.structured_products_notional
        + inputs.residual_portfolio_notional
    )

    tolerance = max(1.0, inputs.portfolio_nav * 1e-10)
    if allocated_notional > inputs.portfolio_nav + tolerance:
        raise ValueError(
            "Non-overlapping sleeve notionals cannot exceed portfolio NAV."
        )


def calculate_rates_risk_score(
    total_dv01: float,
    long_end_dv01_share: float,
) -> float:
    """Calculate the existing illustrative rates heuristic score."""

    dv01_component = min(abs(total_dv01) / 50_000, 1.0) * 60
    concentration_component = clamp(long_end_dv01_share, 0.0, 1.0) * 40
    return clamp(dv01_component + concentration_component)


def calculate_financing_risk_score(
    repo_margin_deficit: float,
    collateral_market_value: float,
) -> float:
    """Calculate an illustrative liquidity-pressure score."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    deficit_ratio = max(0.0, repo_margin_deficit / collateral_market_value)
    return clamp(deficit_ratio / 0.10 * 100)


def calculate_structured_products_risk_score(
    autocall_probability: float,
    barrier_breach_probability: float,
) -> float:
    """Calculate the existing illustrative structured-products score."""

    if not 0 <= autocall_probability <= 1:
        raise ValueError("Autocall probability must be between 0 and 1.")
    if not 0 <= barrier_breach_probability <= 1:
        raise ValueError("Final protection loss probability must be between 0 and 1.")

    breach_component = barrier_breach_probability * 80
    low_autocall_component = (1.0 - autocall_probability) * 20
    return clamp(breach_component + low_autocall_component)


def calculate_portfolio_risk_score(
    portfolio_var_95: float,
    portfolio_cvar_95: float,
    max_drawdown: float,
) -> float:
    """Calculate the existing illustrative portfolio-risk score."""

    var_component = min(max(portfolio_var_95, 0.0) / 0.03, 1.0) * 30
    cvar_component = min(max(portfolio_cvar_95, 0.0) / 0.05, 1.0) * 30
    drawdown_component = min(abs(min(max_drawdown, 0.0)) / 0.25, 1.0) * 40
    return clamp(var_component + cvar_component + drawdown_component)


def identify_dominant_risk_bucket(scores: dict[str, float]) -> str:
    """Identify the highest illustrative score bucket."""

    if not scores:
        raise ValueError("Scores dictionary cannot be empty.")
    return max(scores, key=scores.get)


def calculate_cross_asset_summary(
    inputs: CrossAssetRiskInputs,
) -> CrossAssetRiskSummary:
    """Calculate the dashboard heuristic summary under validated inputs."""

    validate_cross_asset_inputs(inputs)

    rates_score = calculate_rates_risk_score(
        total_dv01=inputs.total_dv01,
        long_end_dv01_share=inputs.long_end_dv01_share,
    )
    financing_score = calculate_financing_risk_score(
        repo_margin_deficit=inputs.repo_margin_deficit,
        collateral_market_value=inputs.collateral_market_value,
    )
    structured_score = calculate_structured_products_risk_score(
        autocall_probability=inputs.structured_autocall_probability,
        barrier_breach_probability=inputs.structured_barrier_breach_probability,
    )
    portfolio_score = calculate_portfolio_risk_score(
        portfolio_var_95=inputs.portfolio_var_95,
        portfolio_cvar_95=inputs.portfolio_cvar_95,
        max_drawdown=inputs.max_drawdown,
    )

    scores = {
        "Rates": rates_score,
        "Financing Liquidity": financing_score,
        "Structured Products": structured_score,
        "Residual Portfolio": portfolio_score,
    }

    composite_score = (
        0.25 * rates_score
        + 0.20 * financing_score
        + 0.25 * structured_score
        + 0.30 * portfolio_score
    )

    allocated_notional = (
        inputs.rates_sleeve_notional
        + inputs.structured_products_notional
        + inputs.residual_portfolio_notional
    )

    return CrossAssetRiskSummary(
        rates_score=float(rates_score),
        financing_score=float(financing_score),
        structured_products_score=float(structured_score),
        portfolio_score=float(portfolio_score),
        composite_score=float(composite_score),
        composite_risk_label=classify_risk_score(composite_score),
        dominant_risk_bucket=identify_dominant_risk_bucket(scores),
        base_currency=inputs.base_currency.strip().upper(),
        portfolio_nav=float(inputs.portfolio_nav),
        allocated_sleeve_notional=float(allocated_notional),
        unallocated_nav=float(inputs.portfolio_nav - allocated_notional),
        current_financing_liquidity_requirement=float(inputs.repo_margin_deficit),
    )


def cross_asset_summary_to_dict(summary: CrossAssetRiskSummary) -> dict[str, Any]:
    """Convert summary to dictionary."""

    return asdict(summary)


def cross_asset_inputs_to_dict(inputs: CrossAssetRiskInputs) -> dict[str, Any]:
    """Convert inputs to a reconstructable dictionary."""

    return asdict(inputs)


def build_default_cross_asset_inputs() -> CrossAssetRiskInputs:
    """Build explicit manual/sample inputs with a reconciled common NAV."""

    return CrossAssetRiskInputs(
        total_dv01=24_403,
        long_end_dv01_share=0.58,
        repo_margin_deficit=325_000,
        collateral_market_value=10_000_000,
        structured_autocall_probability=0.42,
        structured_barrier_breach_probability=0.18,
        portfolio_var_95=0.018,
        portfolio_cvar_95=0.028,
        max_drawdown=-0.115,
        equity_weight=0.55,
        credit_weight=0.15,
        rates_weight=0.20,
        alternatives_weight=0.10,
        base_currency="EUR",
        portfolio_nav=100_000_000,
        rates_sleeve_notional=30_000_000,
        structured_products_notional=20_000_000,
        residual_portfolio_notional=50_000_000,
    )


def build_sleeve_reconciliation_table(
    inputs: CrossAssetRiskInputs,
) -> pd.DataFrame:
    """Build a NAV reconciliation for non-overlapping economic sleeves."""

    validate_cross_asset_inputs(inputs)

    allocated = (
        inputs.rates_sleeve_notional
        + inputs.structured_products_notional
        + inputs.residual_portfolio_notional
    )
    unallocated = inputs.portfolio_nav - allocated

    rows = [
        {
            "sleeve": "Dedicated rates sleeve",
            "notional_base": inputs.rates_sleeve_notional,
            "share_of_nav": inputs.rates_sleeve_notional / inputs.portfolio_nav,
            "economic_stress_driver": "DV01 amount in base currency",
        },
        {
            "sleeve": "Structured-products sleeve",
            "notional_base": inputs.structured_products_notional,
            "share_of_nav": inputs.structured_products_notional / inputs.portfolio_nav,
            "economic_stress_driver": "Scenario return × sleeve notional",
        },
        {
            "sleeve": "Residual multi-asset sleeve",
            "notional_base": inputs.residual_portfolio_notional,
            "share_of_nav": inputs.residual_portfolio_notional / inputs.portfolio_nav,
            "economic_stress_driver": "Weighted scenario return × sleeve notional",
        },
        {
            "sleeve": "Unallocated NAV / cash",
            "notional_base": unallocated,
            "share_of_nav": unallocated / inputs.portfolio_nav,
            "economic_stress_driver": "No stress in this simplified table",
        },
    ]

    return pd.DataFrame(rows)


def calculate_cross_asset_stress_table(
    inputs: CrossAssetRiskInputs,
) -> pd.DataFrame:
    """Calculate dimensionally coherent economic P&L and liquidity stresses."""

    validate_cross_asset_inputs(inputs)

    scenarios = [
        {
            "scenario": "Parallel rates +100bp / funding pressure",
            "rates_pnl_amount": -inputs.total_dv01 * 100,
            "financing_liquidity_change_rate": 0.01,
            "structured_products_shock_pct": -0.03,
            "residual_portfolio_shock_pct": (
                -0.05 * inputs.rates_weight
                - 0.03 * inputs.credit_weight
            ),
        },
        {
            "scenario": "Risk-off equity drawdown",
            "rates_pnl_amount": 0.35 * inputs.total_dv01 * 100,
            "financing_liquidity_change_rate": 0.025,
            "structured_products_shock_pct": -0.08,
            "residual_portfolio_shock_pct": (
                -0.12 * inputs.equity_weight
                - 0.04 * inputs.credit_weight
                + 0.02 * inputs.rates_weight
            ),
        },
        {
            "scenario": "Credit widening / funding stress",
            "rates_pnl_amount": 0.10 * inputs.total_dv01 * 100,
            "financing_liquidity_change_rate": 0.04,
            "structured_products_shock_pct": -0.05,
            "residual_portfolio_shock_pct": (
                -0.08 * inputs.credit_weight
                - 0.05 * inputs.equity_weight
            ),
        },
        {
            "scenario": "Volatility spike / barrier pressure",
            "rates_pnl_amount": 0.0,
            "financing_liquidity_change_rate": 0.015,
            "structured_products_shock_pct": -0.12,
            "residual_portfolio_shock_pct": (
                -0.07 * inputs.equity_weight
                - 0.03 * inputs.credit_weight
            ),
        },
        {
            "scenario": "Soft landing / risk rally",
            "rates_pnl_amount": 0.10 * inputs.total_dv01 * 100,
            "financing_liquidity_change_rate": -0.005,
            "structured_products_shock_pct": 0.04,
            "residual_portfolio_shock_pct": (
                0.08 * inputs.equity_weight
                + 0.03 * inputs.credit_weight
            ),
        },
    ]

    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        structured_pnl = (
            scenario["structured_products_shock_pct"]
            * inputs.structured_products_notional
        )
        residual_pnl = (
            scenario["residual_portfolio_shock_pct"]
            * inputs.residual_portfolio_notional
        )
        economic_pnl = (
            scenario["rates_pnl_amount"]
            + structured_pnl
            + residual_pnl
        )
        liquidity_change = (
            scenario["financing_liquidity_change_rate"]
            * inputs.collateral_market_value
        )
        stressed_liquidity_requirement = max(
            0.0,
            inputs.repo_margin_deficit + liquidity_change,
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "base_currency": inputs.base_currency.strip().upper(),
                "rates_pnl_amount": float(scenario["rates_pnl_amount"]),
                "structured_products_shock_pct": float(
                    scenario["structured_products_shock_pct"]
                ),
                "structured_products_pnl_amount": float(structured_pnl),
                "residual_portfolio_shock_pct": float(
                    scenario["residual_portfolio_shock_pct"]
                ),
                "residual_portfolio_pnl_amount": float(residual_pnl),
                "economic_pnl_amount": float(economic_pnl),
                "economic_pnl_pct_nav": float(economic_pnl / inputs.portfolio_nav),
                "incremental_financing_liquidity_change_amount": float(
                    liquidity_change
                ),
                "stressed_financing_liquidity_requirement_amount": float(
                    stressed_liquidity_requirement
                ),
            }
        )

    return pd.DataFrame(rows)


def build_risk_heatmap_table(
    summary: CrossAssetRiskSummary,
) -> pd.DataFrame:
    """Build the illustrative heuristic risk-score table."""

    rows = [
        {
            "risk_bucket": "Rates",
            "heuristic_score": summary.rates_score,
            "heuristic_label": classify_risk_score(summary.rates_score),
        },
        {
            "risk_bucket": "Financing Liquidity",
            "heuristic_score": summary.financing_score,
            "heuristic_label": classify_risk_score(summary.financing_score),
        },
        {
            "risk_bucket": "Structured Products",
            "heuristic_score": summary.structured_products_score,
            "heuristic_label": classify_risk_score(
                summary.structured_products_score
            ),
        },
        {
            "risk_bucket": "Residual Portfolio",
            "heuristic_score": summary.portfolio_score,
            "heuristic_label": classify_risk_score(summary.portfolio_score),
        },
    ]
    return pd.DataFrame(rows)


def generate_cross_asset_commentary(
    inputs: CrossAssetRiskInputs,
    summary: CrossAssetRiskSummary,
    stress_df: pd.DataFrame,
) -> list[str]:
    """Generate precise commentary for economic P&L and liquidity outputs."""

    worst_stress = stress_df.loc[
        stress_df["economic_pnl_pct_nav"].idxmin()
    ]
    peak_liquidity = stress_df.loc[
        stress_df[
            "stressed_financing_liquidity_requirement_amount"
        ].idxmax()
    ]

    return [
        (
            f"The worst predefined economic stress is '{worst_stress['scenario']}' "
            f"at {worst_stress['economic_pnl_amount']:,.0f} "
            f"{summary.base_currency}, or "
            f"{worst_stress['economic_pnl_pct_nav']:.2%} of common NAV."
        ),
        (
            "Rates, structured-products and residual-portfolio impacts are first "
            f"translated into {summary.base_currency} amounts, aggregated once, "
            "and then divided by the common portfolio NAV."
        ),
        (
            f"The peak stressed financing liquidity requirement is "
            f"{peak_liquidity['stressed_financing_liquidity_requirement_amount']:,.0f} "
            f"{summary.base_currency} under '{peak_liquidity['scenario']}'. "
            "It is not included in economic P&L."
        ),
        (
            f"The sleeve reconciliation allocates "
            f"{summary.allocated_sleeve_notional:,.0f} {summary.base_currency} "
            f"of {summary.portfolio_nav:,.0f} {summary.base_currency} NAV, leaving "
            f"{summary.unallocated_nav:,.0f} unallocated."
        ),
        (
            f"The composite heuristic demo score is "
            f"{summary.composite_score:.1f}/100 and the highest heuristic bucket "
            f"is {summary.dominant_risk_bucket}. These scores are not calibrated "
            "risk measures or limit metrics."
        ),
        (
            "Inputs are manual/sample values and are not automatically linked to "
            "the current runs of the underlying modules."
        ),
    ]
