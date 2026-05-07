"""
Portfolio Risk Engine.

This module implements transparent portfolio risk analytics.

Financial conventions:
- Price data is converted into simple returns.
- Portfolio return = weighted sum of asset returns.
- Annualized return = average periodic return x periods per year.
- Annualized volatility = periodic volatility x sqrt(periods per year).
- Sharpe ratio = (annualized return - risk-free rate) / annualized volatility.
- Historical VaR is reported as a positive loss number.
- Historical CVaR is the average loss beyond VaR.
- Risk contribution uses covariance-based volatility contribution.

Important limitation:
This is a simplified portfolio analytics engine for desk/risk education and demonstration.
It is not a production risk system and does not model liquidity, transaction costs,
slippage, factor models, or full risk decomposition.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioRiskSummary:
    """Portfolio risk summary."""

    number_of_assets: int
    number_of_observations: int
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    historical_var_95: float
    historical_cvar_95: float
    best_period_return: float
    worst_period_return: float


def build_sample_price_data(
    n_days: int = 504,
    seed: int = 42,
) -> pd.DataFrame:
    """Build deterministic synthetic multi-asset price data.

    Assets:
    - US_EQUITY
    - EUROPE_EQUITY
    - US_TREASURY
    - IG_CREDIT
    - GOLD

    Prices are generated from simplified GBM-like returns.
    """

    if n_days <= 10:
        raise ValueError("n_days must be greater than 10.")

    rng = np.random.default_rng(seed)

    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)

    asset_params = {
        "US_EQUITY": {"drift": 0.08, "vol": 0.18},
        "EUROPE_EQUITY": {"drift": 0.06, "vol": 0.20},
        "US_TREASURY": {"drift": 0.025, "vol": 0.06},
        "IG_CREDIT": {"drift": 0.04, "vol": 0.08},
        "GOLD": {"drift": 0.035, "vol": 0.16},
    }

    periods_per_year = 252
    data = {"date": dates}

    for asset, params in asset_params.items():
        daily_drift = params["drift"] / periods_per_year
        daily_vol = params["vol"] / np.sqrt(periods_per_year)

        returns = rng.normal(
            loc=daily_drift,
            scale=daily_vol,
            size=n_days,
        )

        prices = 100.0 * np.cumprod(1.0 + returns)
        data[asset] = prices

    return pd.DataFrame(data)


def load_price_data(path: str) -> pd.DataFrame:
    """Load price data from CSV."""

    df = pd.read_csv(path)

    if "date" not in df.columns:
        raise ValueError("Price data must include a 'date' column.")

    return df


def prepare_price_data(price_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare price data with date index and numeric asset columns."""

    if "date" not in price_df.columns:
        raise ValueError("Price data must include a 'date' column.")

    df = price_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    for column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(axis=0, how="any")

    if df.empty:
        raise ValueError("Price data is empty after cleaning.")

    if len(df.columns) < 2:
        raise ValueError("At least two asset columns are required.")

    return df


def calculate_asset_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate simple asset returns from prices."""

    prepared_prices = prepare_price_data(price_df)
    returns = prepared_prices.pct_change().dropna(how="any")

    if returns.empty:
        raise ValueError("Not enough price observations to calculate returns.")

    return returns


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Normalize weights so they sum to 1."""

    if not weights:
        raise ValueError("Weights cannot be empty.")

    total_weight = float(sum(weights.values()))

    if total_weight <= 0:
        raise ValueError("Total weight must be positive.")

    return {asset: float(weight) / total_weight for asset, weight in weights.items()}


def validate_weights(returns_df: pd.DataFrame, weights: dict[str, float]) -> dict[str, float]:
    """Validate and normalize portfolio weights."""

    missing_assets = set(weights) - set(returns_df.columns)

    if missing_assets:
        raise ValueError(f"Weights include assets not in returns data: {missing_assets}")

    normalized_weights = normalize_weights(weights)

    return normalized_weights


def calculate_portfolio_returns(
    returns_df: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Calculate portfolio returns as weighted sum of asset returns."""

    normalized_weights = validate_weights(returns_df, weights)

    weight_vector = pd.Series(normalized_weights)
    aligned_returns = returns_df[weight_vector.index]

    portfolio_returns = aligned_returns.dot(weight_vector)
    portfolio_returns.name = "portfolio_return"

    return portfolio_returns


def calculate_cumulative_return_series(portfolio_returns: pd.Series) -> pd.Series:
    """Calculate cumulative return index from periodic portfolio returns."""

    return (1.0 + portfolio_returns).cumprod()


def calculate_drawdown_series(portfolio_returns: pd.Series) -> pd.Series:
    """Calculate drawdown series."""

    cumulative = calculate_cumulative_return_series(portfolio_returns)
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1.0
    drawdown.name = "drawdown"

    return drawdown


def calculate_historical_var(
    portfolio_returns: pd.Series,
    confidence_level: float = 0.95,
) -> float:
    """Calculate historical VaR as a positive loss number."""

    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")

    quantile = portfolio_returns.quantile(1.0 - confidence_level)

    return float(max(0.0, -quantile))


def calculate_historical_cvar(
    portfolio_returns: pd.Series,
    confidence_level: float = 0.95,
) -> float:
    """Calculate historical CVaR as a positive loss number."""

    var = calculate_historical_var(portfolio_returns, confidence_level)
    tail_returns = portfolio_returns[portfolio_returns <= -var]

    if tail_returns.empty:
        return float(var)

    return float(max(0.0, -tail_returns.mean()))


def calculate_annualized_return(
    portfolio_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Calculate arithmetic annualized return."""

    return float(portfolio_returns.mean() * periods_per_year)


def calculate_annualized_volatility(
    portfolio_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Calculate annualized volatility."""

    return float(portfolio_returns.std(ddof=1) * np.sqrt(periods_per_year))


def calculate_sharpe_ratio(
    annualized_return: float,
    annualized_volatility: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Calculate Sharpe ratio."""

    if annualized_volatility == 0:
        return 0.0

    return float((annualized_return - risk_free_rate) / annualized_volatility)


def summarize_portfolio_risk(
    returns_df: pd.DataFrame,
    weights: dict[str, float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    confidence_level: float = 0.95,
) -> PortfolioRiskSummary:
    """Summarize portfolio risk metrics."""

    portfolio_returns = calculate_portfolio_returns(returns_df, weights)

    annualized_return = calculate_annualized_return(
        portfolio_returns=portfolio_returns,
        periods_per_year=periods_per_year,
    )

    annualized_volatility = calculate_annualized_volatility(
        portfolio_returns=portfolio_returns,
        periods_per_year=periods_per_year,
    )

    sharpe_ratio = calculate_sharpe_ratio(
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        risk_free_rate=risk_free_rate,
    )

    drawdown = calculate_drawdown_series(portfolio_returns)

    return PortfolioRiskSummary(
        number_of_assets=len(weights),
        number_of_observations=len(portfolio_returns),
        annualized_return=float(annualized_return),
        annualized_volatility=float(annualized_volatility),
        sharpe_ratio=float(sharpe_ratio),
        max_drawdown=float(drawdown.min()),
        historical_var_95=float(
            calculate_historical_var(
                portfolio_returns=portfolio_returns,
                confidence_level=confidence_level,
            )
        ),
        historical_cvar_95=float(
            calculate_historical_cvar(
                portfolio_returns=portfolio_returns,
                confidence_level=confidence_level,
            )
        ),
        best_period_return=float(portfolio_returns.max()),
        worst_period_return=float(portfolio_returns.min()),
    )


def portfolio_risk_summary_to_dict(summary: PortfolioRiskSummary) -> dict[str, Any]:
    """Convert risk summary to dictionary."""

    return asdict(summary)


def calculate_correlation_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate asset return correlation matrix."""

    return returns_df.corr()


def calculate_risk_contribution(
    returns_df: pd.DataFrame,
    weights: dict[str, float],
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Calculate covariance-based contribution to portfolio volatility.

    Marginal contribution to risk:
    MCR = Sigma * w / portfolio_vol

    Contribution to risk:
    CTR = w * MCR

    Percentage contribution:
    pct_CTR = CTR / portfolio_vol
    """

    normalized_weights = validate_weights(returns_df, weights)

    assets = list(normalized_weights.keys())
    aligned_returns = returns_df[assets]
    weight_vector = np.array([normalized_weights[asset] for asset in assets])

    covariance_matrix = aligned_returns.cov().to_numpy() * periods_per_year
    portfolio_variance = float(weight_vector.T @ covariance_matrix @ weight_vector)

    if portfolio_variance <= 0:
        raise ValueError("Portfolio variance must be positive.")

    portfolio_volatility = float(np.sqrt(portfolio_variance))
    marginal_contribution = covariance_matrix @ weight_vector / portfolio_volatility
    contribution_to_vol = weight_vector * marginal_contribution
    pct_contribution = contribution_to_vol / portfolio_volatility

    return pd.DataFrame(
        {
            "asset": assets,
            "weight": weight_vector,
            "marginal_contribution_to_risk": marginal_contribution,
            "contribution_to_volatility": contribution_to_vol,
            "pct_contribution_to_volatility": pct_contribution,
        }
    )


def _asset_stress_shock(asset: str, scenario: str) -> float:
    """Map generic asset names to stress shocks."""

    asset_upper = asset.upper()

    is_equity = "EQUITY" in asset_upper or "SPX" in asset_upper or "NASDAQ" in asset_upper
    is_bond = "TREASURY" in asset_upper or "BOND" in asset_upper or "GOV" in asset_upper
    is_credit = "CREDIT" in asset_upper or "IG" in asset_upper or "HY" in asset_upper
    is_gold = "GOLD" in asset_upper
    is_cash = "CASH" in asset_upper

    if scenario == "Uniform -5%":
        return 0.0 if is_cash else -0.05

    if scenario == "Risk-off shock":
        if is_equity:
            return -0.12
        if is_credit:
            return -0.04
        if is_bond:
            return 0.03
        if is_gold:
            return 0.04
        return -0.05

    if scenario == "Rates selloff":
        if is_bond:
            return -0.06
        if is_credit:
            return -0.04
        if is_equity:
            return -0.05
        if is_gold:
            return -0.02
        return -0.03

    if scenario == "Credit widening":
        if is_credit:
            return -0.08
        if is_equity:
            return -0.06
        if is_bond:
            return 0.01
        if is_gold:
            return 0.02
        return -0.03

    if scenario == "Equity rally / rates stable":
        if is_equity:
            return 0.08
        if is_credit:
            return 0.02
        if is_bond:
            return 0.00
        if is_gold:
            return -0.02
        return 0.03

    raise ValueError(f"Unknown stress scenario: {scenario}")


def calculate_stress_scenario_table(weights: dict[str, float]) -> pd.DataFrame:
    """Calculate portfolio P&L under predefined shock scenarios."""

    normalized_weights = normalize_weights(weights)

    scenarios = [
        "Uniform -5%",
        "Risk-off shock",
        "Rates selloff",
        "Credit widening",
        "Equity rally / rates stable",
    ]

    rows = []

    for scenario in scenarios:
        weighted_shock = 0.0

        for asset, weight in normalized_weights.items():
            shock = _asset_stress_shock(asset=asset, scenario=scenario)
            weighted_shock += weight * shock

        rows.append(
            {
                "scenario": scenario,
                "estimated_portfolio_return": float(weighted_shock),
                "estimated_loss": float(max(0.0, -weighted_shock)),
                "estimated_gain": float(max(0.0, weighted_shock)),
            }
        )

    return pd.DataFrame(rows)


def generate_portfolio_risk_commentary(
    summary: PortfolioRiskSummary,
    risk_contribution_df: pd.DataFrame,
    stress_df: pd.DataFrame,
) -> list[str]:
    """Generate desk-style portfolio risk commentary."""

    largest_contributor = risk_contribution_df.loc[
        risk_contribution_df["pct_contribution_to_volatility"].idxmax()
    ]

    worst_stress = stress_df.loc[
        stress_df["estimated_portfolio_return"].idxmin()
    ]

    comments = [
        (
            f"Annualized volatility is {summary.annualized_volatility:.2%}, "
            f"with Sharpe ratio of {summary.sharpe_ratio:.2f}."
        ),
        (
            f"Maximum historical drawdown is {summary.max_drawdown:.2%}; "
            f"historical 95% VaR is {summary.historical_var_95:.2%} and CVaR is {summary.historical_cvar_95:.2%}."
        ),
        (
            f"Largest volatility contribution comes from {largest_contributor['asset']} "
            f"at {largest_contributor['pct_contribution_to_volatility']:.2%} of total portfolio volatility."
        ),
        (
            f"Worst predefined stress is '{worst_stress['scenario']}' with estimated portfolio return "
            f"of {worst_stress['estimated_portfolio_return']:.2%}."
        ),
        (
            "This is a simplified portfolio risk proxy and does not model liquidity, transaction costs, factor exposures, or intraday risk."
        ),
    ]

    return comments
