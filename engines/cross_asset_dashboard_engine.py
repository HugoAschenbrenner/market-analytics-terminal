"""
Cross-Asset Dashboard Engine.

This module creates a synthetic/proxy cross-asset risk dashboard.

Purpose:
- Aggregate key risk indicators across rates, financing, structured products, and portfolio risk.
- Produce a high-level dashboard view useful for sales/trading/risk discussion.
- Translate isolated analytics into a desk-style risk overview.

Important limitation:
This is a simplified proxy dashboard. It is not a production risk aggregation system,
not a live market dashboard, not investment advice, and not a trading signal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CrossAssetRiskInputs:
    """Inputs for cross-asset risk dashboard."""

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


@dataclass(frozen=True)
class CrossAssetRiskSummary:
    """Cross-asset risk summary."""

    rates_score: float
    financing_score: float
    structured_products_score: float
    portfolio_score: float
    composite_score: float
    composite_risk_label: str
    dominant_risk_bucket: str


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a numeric value between lower and upper bounds."""

    return float(max(lower, min(upper, value)))


def classify_risk_score(score: float) -> str:
    """Classify risk score into a dashboard label."""

    if score < 25:
        return "Low"

    if score < 50:
        return "Moderate"

    if score < 75:
        return "High"

    return "Critical"


def calculate_rates_risk_score(
    total_dv01: float,
    long_end_dv01_share: float,
) -> float:
    """Calculate simplified rates risk score.

    Higher score when:
    - total DV01 is high
    - long-end concentration is high
    """

    dv01_component = min(abs(total_dv01) / 50_000, 1.0) * 60
    concentration_component = clamp(long_end_dv01_share, 0.0, 1.0) * 40

    return clamp(dv01_component + concentration_component)


def calculate_financing_risk_score(
    repo_margin_deficit: float,
    collateral_market_value: float,
) -> float:
    """Calculate financing risk score from margin deficit ratio."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    deficit_ratio = max(0.0, repo_margin_deficit / collateral_market_value)

    return clamp(deficit_ratio / 0.10 * 100)


def calculate_structured_products_risk_score(
    autocall_probability: float,
    barrier_breach_probability: float,
) -> float:
    """Calculate structured products risk score.

    Higher barrier breach probability increases risk.
    Higher autocall probability reduces risk.
    """

    if not 0 <= autocall_probability <= 1:
        raise ValueError("Autocall probability must be between 0 and 1.")

    if not 0 <= barrier_breach_probability <= 1:
        raise ValueError("Barrier breach probability must be between 0 and 1.")

    breach_component = barrier_breach_probability * 80
    low_autocall_component = (1.0 - autocall_probability) * 20

    return clamp(breach_component + low_autocall_component)


def calculate_portfolio_risk_score(
    portfolio_var_95: float,
    portfolio_cvar_95: float,
    max_drawdown: float,
) -> float:
    """Calculate portfolio risk score from VaR, CVaR, and drawdown."""

    var_component = min(max(portfolio_var_95, 0.0) / 0.03, 1.0) * 30
    cvar_component = min(max(portfolio_cvar_95, 0.0) / 0.05, 1.0) * 30
    drawdown_component = min(abs(min(max_drawdown, 0.0)) / 0.25, 1.0) * 40

    return clamp(var_component + cvar_component + drawdown_component)


def identify_dominant_risk_bucket(scores: dict[str, float]) -> str:
    """Identify the highest risk bucket."""

    if not scores:
        raise ValueError("Scores dictionary cannot be empty.")

    return max(scores, key=scores.get)


def calculate_cross_asset_summary(
    inputs: CrossAssetRiskInputs,
) -> CrossAssetRiskSummary:
    """Calculate cross-asset risk summary."""

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
        "Financing": financing_score,
        "Structured Products": structured_score,
        "Portfolio Risk": portfolio_score,
    }

    composite_score = (
        0.25 * rates_score
        + 0.20 * financing_score
        + 0.25 * structured_score
        + 0.30 * portfolio_score
    )

    dominant_bucket = identify_dominant_risk_bucket(scores)

    return CrossAssetRiskSummary(
        rates_score=float(rates_score),
        financing_score=float(financing_score),
        structured_products_score=float(structured_score),
        portfolio_score=float(portfolio_score),
        composite_score=float(composite_score),
        composite_risk_label=classify_risk_score(composite_score),
        dominant_risk_bucket=dominant_bucket,
    )


def cross_asset_summary_to_dict(summary: CrossAssetRiskSummary) -> dict[str, Any]:
    """Convert summary to dictionary."""

    return asdict(summary)


def build_default_cross_asset_inputs() -> CrossAssetRiskInputs:
    """Build default dashboard inputs based on realistic proxy values."""

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
    )


def calculate_cross_asset_stress_table(
    inputs: CrossAssetRiskInputs,
) -> pd.DataFrame:
    """Calculate simplified cross-asset stress scenario table."""

    scenarios = [
        {
            "scenario": "Rates +100bp / curve bear steepening",
            "rates_impact": -inputs.total_dv01 * 100,
            "financing_impact": -0.01 * inputs.collateral_market_value,
            "structured_products_impact": -0.03,
            "portfolio_impact": -0.05 * inputs.rates_weight - 0.03 * inputs.credit_weight,
        },
        {
            "scenario": "Risk-off equity drawdown",
            "rates_impact": 0.35 * inputs.total_dv01 * 100,
            "financing_impact": -0.025 * inputs.collateral_market_value,
            "structured_products_impact": -0.08,
            "portfolio_impact": -0.12 * inputs.equity_weight - 0.04 * inputs.credit_weight + 0.02 * inputs.rates_weight,
        },
        {
            "scenario": "Credit widening / funding stress",
            "rates_impact": 0.10 * inputs.total_dv01 * 100,
            "financing_impact": -0.04 * inputs.collateral_market_value,
            "structured_products_impact": -0.05,
            "portfolio_impact": -0.08 * inputs.credit_weight - 0.05 * inputs.equity_weight,
        },
        {
            "scenario": "Volatility spike / barrier pressure",
            "rates_impact": 0.00,
            "financing_impact": -0.015 * inputs.collateral_market_value,
            "structured_products_impact": -0.12,
            "portfolio_impact": -0.07 * inputs.equity_weight - 0.03 * inputs.credit_weight,
        },
        {
            "scenario": "Soft landing / risk rally",
            "rates_impact": 0.10 * inputs.total_dv01 * 100,
            "financing_impact": 0.005 * inputs.collateral_market_value,
            "structured_products_impact": 0.04,
            "portfolio_impact": 0.08 * inputs.equity_weight + 0.03 * inputs.credit_weight,
        },
    ]

    rows = []

    for scenario in scenarios:
        total_proxy_impact = (
            scenario["rates_impact"] / max(inputs.collateral_market_value, 1)
            + scenario["financing_impact"] / max(inputs.collateral_market_value, 1)
            + scenario["structured_products_impact"]
            + scenario["portfolio_impact"]
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "rates_impact_amount": float(scenario["rates_impact"]),
                "financing_impact_amount": float(scenario["financing_impact"]),
                "structured_products_impact_pct": float(scenario["structured_products_impact"]),
                "portfolio_impact_pct": float(scenario["portfolio_impact"]),
                "total_proxy_impact_pct": float(total_proxy_impact),
            }
        )

    return pd.DataFrame(rows)


def build_risk_heatmap_table(
    summary: CrossAssetRiskSummary,
) -> pd.DataFrame:
    """Build risk heatmap table."""

    rows = [
        {
            "risk_bucket": "Rates",
            "risk_score": summary.rates_score,
            "risk_label": classify_risk_score(summary.rates_score),
        },
        {
            "risk_bucket": "Financing",
            "risk_score": summary.financing_score,
            "risk_label": classify_risk_score(summary.financing_score),
        },
        {
            "risk_bucket": "Structured Products",
            "risk_score": summary.structured_products_score,
            "risk_label": classify_risk_score(summary.structured_products_score),
        },
        {
            "risk_bucket": "Portfolio Risk",
            "risk_score": summary.portfolio_score,
            "risk_label": classify_risk_score(summary.portfolio_score),
        },
    ]

    return pd.DataFrame(rows)


def generate_cross_asset_commentary(
    inputs: CrossAssetRiskInputs,
    summary: CrossAssetRiskSummary,
    stress_df: pd.DataFrame,
) -> list[str]:
    """Generate desk-style cross-asset dashboard commentary."""

    worst_stress = stress_df.loc[stress_df["total_proxy_impact_pct"].idxmin()]

    comments = [
        (
            f"Composite cross-asset risk is {summary.composite_risk_label} "
            f"with a score of {summary.composite_score:.1f}/100."
        ),
        (
            f"The dominant dashboard risk bucket is {summary.dominant_risk_bucket}; "
            "this is the area that should be checked first before discussing trade ideas or client positioning."
        ),
        (
            f"Rates exposure is represented by total DV01 of {inputs.total_dv01:,.0f}, "
            f"with {inputs.long_end_dv01_share:.1%} concentrated in the long end."
        ),
        (
            f"Structured products risk is driven by estimated barrier breach probability of "
            f"{inputs.structured_barrier_breach_probability:.1%} versus autocall probability of "
            f"{inputs.structured_autocall_probability:.1%}."
        ),
        (
            f"The worst predefined cross-asset stress is '{worst_stress['scenario']}' "
            f"with total proxy impact of {worst_stress['total_proxy_impact_pct']:.2%}."
        ),
        (
            "This dashboard is a cross-asset proxy layer: useful for synthesis and discussion, not for production risk aggregation or trading decisions."
        ),
    ]

    return comments
