"""
Portfolio Risk Engine.

This module implements transparent portfolio risk analytics.

Financial conventions:
- Price data is converted into simple returns.
- Portfolio return = weighted sum of asset returns.
- Arithmetic annualized return = average periodic return x explicitly selected periods per year.
- Annualized volatility = periodic volatility x sqrt(periods per year).
- Sharpe ratio = (annualized return - risk-free rate) / annualized volatility.
- Historical VaR is reported as a positive loss number at an explicitly selected horizon.
- Historical CVaR is the average loss beyond VaR over the same selected horizon.
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
class FrequencyAnalysis:
    """Observed date-frequency and data-quality diagnostics."""

    inferred_frequency: str
    inferred_periods_per_year: int
    observation_count: int
    median_spacing_days: float
    maximum_gap_days: float
    irregularity_ratio: float
    calendar_span_years: float
    data_quality_status: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioRiskSummary:
    """Portfolio risk summary with explicit frequency and horizon."""

    number_of_assets: int
    number_of_observations: int
    periods_per_year: int
    frequency_label: str
    sample_years: float
    annualized_return: float
    cagr: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    historical_var_95: float
    historical_cvar_95: float
    var_horizon_periods: int
    best_period_return: float
    worst_period_return: float
    confidence_level: float = 0.95


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


def _parse_and_validate_dates(
    price_df: pd.DataFrame,
) -> pd.Series:
    """Parse dates and reject invalid or duplicated observations."""
    if "date" not in price_df.columns:
        raise ValueError(
            "Price data must include a 'date' column."
        )

    parsed_dates = pd.to_datetime(
        price_df["date"],
        errors="coerce",
    )

    invalid_count = int(parsed_dates.isna().sum())

    if invalid_count:
        raise ValueError(
            f"Price data contains {invalid_count} invalid date value(s)."
        )

    duplicate_count = int(
        parsed_dates.duplicated(keep=False).sum()
    )

    if duplicate_count:
        raise ValueError(
            "Price data contains duplicated dates. "
            "Each observation date must be unique."
        )

    return parsed_dates


def _classify_frequency(
    median_spacing_days: float,
) -> tuple[str, int, float, float, float]:
    """
    Map median calendar spacing to a market-frequency convention.

    Returns:
    frequency label, periods per year, regular lower bound,
    regular upper bound and material-gap threshold.
    """
    if median_spacing_days <= 3.0:
        return "Daily", 252, 0.5, 4.0, 10.0

    if median_spacing_days <= 10.0:
        return "Weekly", 52, 4.0, 10.0, 21.0

    if median_spacing_days <= 45.0:
        return "Monthly", 12, 20.0, 40.0, 65.0

    if median_spacing_days <= 120.0:
        return "Quarterly", 4, 70.0, 110.0, 180.0

    return "Annual", 1, 300.0, 430.0, 550.0


def analyze_price_frequency(
    price_df: pd.DataFrame,
) -> FrequencyAnalysis:
    """
    Infer observation frequency and diagnose date regularity.

    Frequency is inferred from median calendar-day spacing.
    The result is an explicit analytics convention, not an
    exchange-calendar reconstruction.
    """
    parsed_dates = _parse_and_validate_dates(
        price_df
    )

    sorted_dates = (
        parsed_dates
        .sort_values()
        .reset_index(drop=True)
    )

    if len(sorted_dates) < 3:
        raise ValueError(
            "At least three dated price observations are required."
        )

    spacing_days = (
        sorted_dates
        .diff()
        .dropna()
        .dt.total_seconds()
        .div(86400.0)
    )

    if (spacing_days <= 0).any():
        raise ValueError(
            "Price observation dates must be strictly increasing."
        )

    median_spacing_days = float(
        spacing_days.median()
    )

    (
        frequency_label,
        periods_per_year,
        regular_lower,
        regular_upper,
        material_gap_threshold,
    ) = _classify_frequency(
        median_spacing_days
    )

    regular_mask = spacing_days.between(
        regular_lower,
        regular_upper,
        inclusive="both",
    )

    irregularity_ratio = float(
        1.0 - regular_mask.mean()
    )

    maximum_gap_days = float(
        spacing_days.max()
    )

    calendar_span_years = float(
        (
            sorted_dates.iloc[-1]
            - sorted_dates.iloc[0]
        ).days
        / 365.25
    )

    warnings: list[str] = []

    if len(sorted_dates) < 20:
        warnings.append(
            "The dataset contains fewer than 20 price observations; "
            "risk estimates may be unstable."
        )

    if irregularity_ratio > 0.20:
        warnings.append(
            f"{irregularity_ratio:.0%} of date intervals are "
            f"inconsistent with the inferred {frequency_label.lower()} "
            "frequency."
        )

    if maximum_gap_days > material_gap_threshold:
        warnings.append(
            f"Maximum date gap is {maximum_gap_days:.1f} days, "
            "which may indicate missing observations."
        )

    return FrequencyAnalysis(
        inferred_frequency=frequency_label,
        inferred_periods_per_year=periods_per_year,
        observation_count=len(sorted_dates),
        median_spacing_days=median_spacing_days,
        maximum_gap_days=maximum_gap_days,
        irregularity_ratio=irregularity_ratio,
        calendar_span_years=calendar_span_years,
        data_quality_status=(
            "Review" if warnings else "OK"
        ),
        warnings=tuple(warnings),
    )


def resolve_periods_per_year(
    frequency_mode: str,
    inferred_periods_per_year: int,
    custom_periods_per_year: int | None = None,
) -> int:
    """Resolve the user-selected annualization factor."""
    mapping = {
        "Daily": 252,
        "Weekly": 52,
        "Monthly": 12,
        "Quarterly": 4,
        "Annual": 1,
    }

    if frequency_mode == "Auto-detect":
        resolved = int(inferred_periods_per_year)
    elif frequency_mode == "Custom":
        if custom_periods_per_year is None:
            raise ValueError(
                "Custom periods per year must be supplied."
            )
        resolved = int(custom_periods_per_year)
    elif frequency_mode in mapping:
        resolved = mapping[frequency_mode]
    else:
        raise ValueError(
            f"Unsupported frequency mode: {frequency_mode}"
        )

    if resolved <= 0:
        raise ValueError(
            "Periods per year must be strictly positive."
        )

    return resolved


def frequency_label_from_periods(
    periods_per_year: int,
) -> str:
    """Map an annualization factor to a readable label."""
    mapping = {
        252: "Daily",
        52: "Weekly",
        12: "Monthly",
        4: "Quarterly",
        1: "Annual",
    }

    return mapping.get(
        int(periods_per_year),
        "Custom",
    )


def period_label_from_frequency(
    frequency_label: str,
    period_count: int = 1,
) -> str:
    """Return day/week/month-style wording for VaR horizon."""
    singular_mapping = {
        "Daily": "day",
        "Weekly": "week",
        "Monthly": "month",
        "Quarterly": "quarter",
        "Annual": "year",
        "Custom": "period",
    }

    singular = singular_mapping.get(
        frequency_label,
        "period",
    )

    if int(period_count) == 1:
        return singular

    if singular == "day":
        return "days"

    return singular + "s"


def prepare_price_data(
    price_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare strictly validated price data.

    Dates must be valid and unique. Asset values must be numeric,
    complete and strictly positive.
    """
    parsed_dates = _parse_and_validate_dates(
        price_df
    )

    asset_columns = [
        column
        for column in price_df.columns
        if column != "date"
    ]

    if len(asset_columns) < 2:
        raise ValueError(
            "At least two asset columns are required."
        )

    numeric_assets = (
        price_df[asset_columns]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
    )

    missing_rows = int(
        numeric_assets.isna().any(axis=1).sum()
    )

    if missing_rows:
        raise ValueError(
            f"Price data contains {missing_rows} row(s) "
            "with missing or non-numeric asset prices."
        )

    if not np.isfinite(numeric_assets.to_numpy()).all():
        raise ValueError("Asset prices must be finite.")

    non_positive_count = int(
        (numeric_assets <= 0).sum().sum()
    )

    if non_positive_count:
        raise ValueError(
            "Asset prices must be strictly positive. "
            f"Found {non_positive_count} non-positive value(s)."
        )

    prepared = numeric_assets.copy()
    prepared.insert(0, "date", parsed_dates)

    prepared = (
        prepared
        .sort_values("date")
        .set_index("date")
    )

    if prepared.empty:
        raise ValueError(
            "Price data is empty after preparation."
        )

    return prepared


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

    if any(not np.isfinite(float(weight)) or float(weight) < 0 for weight in weights.values()):
        raise ValueError("Long-only weights must be finite and non-negative.")
    total_weight = float(sum(weights.values()))

    if not np.isfinite(total_weight) or total_weight <= 0:
        raise ValueError("Total weight must be positive.")

    return {asset: float(weight) / total_weight for asset, weight in weights.items()}


def validate_weights(returns_df: pd.DataFrame, weights: dict[str, float]) -> dict[str, float]:
    """Validate and normalize portfolio weights."""

    missing_assets = set(weights) - set(returns_df.columns)

    if missing_assets:
        raise ValueError(f"Weights include assets not in returns data: {missing_assets}")

    normalized_weights = normalize_weights(weights)

    values = returns_df[list(normalized_weights)].to_numpy(dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("Asset returns must be non-empty, complete and finite.")
    if (values < -1.0).any():
        raise ValueError("Simple asset returns cannot be below -100%.")

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
    running_max = cumulative.cummax().clip(lower=1.0)
    drawdown = cumulative / running_max - 1.0
    drawdown.name = "drawdown"

    return drawdown


def calculate_horizon_return_series(
    portfolio_returns: pd.Series,
    horizon_periods: int = 1,
) -> pd.Series:
    """
    Calculate overlapping compounded returns for a risk horizon.

    A horizon of one returns the original periodic return series.
    A horizon above one uses overlapping historical windows.
    """
    horizon = int(horizon_periods)

    if horizon <= 0:
        raise ValueError(
            "Risk horizon must be at least one period."
        )

    clean_returns = (
        portfolio_returns
        .astype(float)
        .dropna()
    )

    if len(clean_returns) < horizon:
        raise ValueError(
            "Not enough return observations for the selected "
            "VaR/CVaR horizon."
        )

    if horizon == 1:
        result = clean_returns.copy()
    else:
        result = (
            (1.0 + clean_returns)
            .rolling(horizon)
            .apply(np.prod, raw=True)
            .dropna()
            - 1.0
        )

    result.name = (
        f"portfolio_return_{horizon}_period"
    )

    return result


def calculate_historical_var(
    portfolio_returns: pd.Series,
    confidence_level: float = 0.95,
    horizon_periods: int = 1,
) -> float:
    """
    Calculate historical VaR as a positive loss number.

    Returns are compounded over the selected horizon using
    overlapping historical windows.
    """
    if not 0 < confidence_level < 1:
        raise ValueError(
            "Confidence level must be between 0 and 1."
        )

    horizon_returns = (
        calculate_horizon_return_series(
            portfolio_returns,
            horizon_periods=horizon_periods,
        )
    )

    quantile = horizon_returns.quantile(
        1.0 - confidence_level
    )

    return float(
        max(0.0, -quantile)
    )


def calculate_historical_cvar(
    portfolio_returns: pd.Series,
    confidence_level: float = 0.95,
    horizon_periods: int = 1,
) -> float:
    """
    Calculate historical CVaR over the selected risk horizon.

    CVaR is the average loss in the historical tail beyond VaR.
    """
    horizon_returns = (
        calculate_horizon_return_series(
            portfolio_returns,
            horizon_periods=horizon_periods,
        )
    )

    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    # Select the return tail before flooring the reported loss at zero.
    # Using the floored VaR would drop tail gains and overstate expected loss.
    quantile = horizon_returns.quantile(1.0 - confidence_level)

    tail_returns = horizon_returns[
        horizon_returns <= quantile
    ]

    if tail_returns.empty:
        return float(max(0.0, -quantile))

    return float(
        max(0.0, -tail_returns.mean())
    )


def calculate_annualized_return(
    portfolio_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate arithmetic annualized return.

    This is mean periodic return multiplied by periods per year.
    It is not the geometric compounded annual growth rate.
    """
    if int(periods_per_year) <= 0:
        raise ValueError(
            "Periods per year must be strictly positive."
        )

    return float(
        portfolio_returns.mean()
        * int(periods_per_year)
    )


def calculate_cagr(
    portfolio_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Calculate geometric compounded annual growth rate."""
    periods = int(portfolio_returns.count())
    annualization_factor = int(periods_per_year)

    if annualization_factor <= 0:
        raise ValueError(
            "Periods per year must be strictly positive."
        )

    if periods <= 0:
        raise ValueError(
            "At least one return observation is required."
        )

    ending_wealth = float(
        np.prod(
            1.0
            + portfolio_returns.astype(float)
        )
    )

    if ending_wealth < 0:
        raise ValueError(
            "CAGR is undefined when compounded wealth is negative."
        )

    if ending_wealth == 0:
        return -1.0

    sample_years = (
        periods
        / annualization_factor
    )

    return float(
        ending_wealth ** (1.0 / sample_years)
        - 1.0
    )


def calculate_annualized_volatility(
    portfolio_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Calculate annualized volatility."""

    if periods_per_year <= 0 or len(portfolio_returns) < 2:
        raise ValueError("Volatility requires positive periods per year and at least two returns.")
    return float(portfolio_returns.std(ddof=1) * np.sqrt(periods_per_year))


def calculate_sharpe_ratio(
    annualized_return: float,
    annualized_volatility: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Calculate Sharpe ratio."""

    if annualized_volatility == 0:
        return float("nan")

    return float((annualized_return - risk_free_rate) / annualized_volatility)


def summarize_portfolio_risk(
    returns_df: pd.DataFrame,
    weights: dict[str, float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    confidence_level: float = 0.95,
    var_horizon_periods: int = 1,
    frequency_label: str | None = None,
) -> PortfolioRiskSummary:
    """Summarize portfolio risk under explicit frequency assumptions."""
    annualization_factor = int(
        periods_per_year
    )
    risk_horizon = int(
        var_horizon_periods
    )

    if annualization_factor <= 0:
        raise ValueError(
            "Periods per year must be strictly positive."
        )

    if risk_horizon <= 0:
        raise ValueError(
            "VaR/CVaR horizon must be at least one period."
        )

    resolved_frequency_label = (
        frequency_label
        or frequency_label_from_periods(
            annualization_factor
        )
    )

    portfolio_returns = calculate_portfolio_returns(
        returns_df,
        weights,
    )

    annualized_return = (
        calculate_annualized_return(
            portfolio_returns=portfolio_returns,
            periods_per_year=annualization_factor,
        )
    )

    cagr = calculate_cagr(
        portfolio_returns=portfolio_returns,
        periods_per_year=annualization_factor,
    )

    annualized_volatility = (
        calculate_annualized_volatility(
            portfolio_returns=portfolio_returns,
            periods_per_year=annualization_factor,
        )
    )

    sharpe_ratio = calculate_sharpe_ratio(
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        risk_free_rate=risk_free_rate,
    )

    drawdown = calculate_drawdown_series(
        portfolio_returns
    )

    return PortfolioRiskSummary(
        number_of_assets=len(weights),
        number_of_observations=len(portfolio_returns),
        periods_per_year=annualization_factor,
        frequency_label=resolved_frequency_label,
        sample_years=float(
            len(portfolio_returns)
            / annualization_factor
        ),
        annualized_return=float(
            annualized_return
        ),
        cagr=float(cagr),
        annualized_volatility=float(
            annualized_volatility
        ),
        sharpe_ratio=float(sharpe_ratio),
        max_drawdown=float(drawdown.min()),
        historical_var_95=float(
            calculate_historical_var(
                portfolio_returns=portfolio_returns,
                confidence_level=confidence_level,
                horizon_periods=risk_horizon,
            )
        ),
        historical_cvar_95=float(
            calculate_historical_cvar(
                portfolio_returns=portfolio_returns,
                confidence_level=confidence_level,
                horizon_periods=risk_horizon,
            )
        ),
        var_horizon_periods=risk_horizon,
        best_period_return=float(
            portfolio_returns.max()
        ),
        worst_period_return=float(
            portfolio_returns.min()
        ),
        confidence_level=float(confidence_level),
    )


def portfolio_risk_summary_to_dict(summary: PortfolioRiskSummary) -> dict[str, Any]:
    """Convert risk summary to dictionary."""

    result = asdict(summary)
    result["historical_var"] = result["historical_var_95"]
    result["historical_cvar"] = result["historical_cvar_95"]
    if not np.isclose(summary.confidence_level, 0.95):
        # Keep the legacy dataclass attributes for callers, but never export
        # an alternative confidence under a falsely labelled 95% column.
        result.pop("historical_var_95")
        result.pop("historical_cvar_95")
    return result


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

    if periods_per_year <= 0 or len(returns_df) < 2:
        raise ValueError("Risk contribution requires positive periods per year and at least two returns.")

    assets = list(normalized_weights.keys())
    aligned_returns = returns_df[assets]
    weight_vector = np.array([normalized_weights[asset] for asset in assets])

    covariance_matrix = aligned_returns.cov().to_numpy() * periods_per_year
    portfolio_variance = float(weight_vector.T @ covariance_matrix @ weight_vector)

    if portfolio_variance <= 0:
        return pd.DataFrame({
            "asset": assets,
            "weight": weight_vector,
            "marginal_contribution_to_risk": np.nan,
            "contribution_to_volatility": 0.0,
            "pct_contribution_to_volatility": np.nan,
        })

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

    if is_cash:
        return 0.0

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
    valid_contributors = risk_contribution_df.dropna(subset=["pct_contribution_to_volatility"])
    if valid_contributors.empty:
        contribution_comment = "Volatility contribution percentages are undefined for a zero-volatility portfolio."
    else:
        largest_contributor = valid_contributors.loc[valid_contributors["pct_contribution_to_volatility"].idxmax()]
        contribution_comment = (
            f"Largest volatility contribution comes from {largest_contributor['asset']} at "
            f"{largest_contributor['pct_contribution_to_volatility']:.2%} of total portfolio volatility."
        )

    worst_stress = stress_df.loc[
        stress_df[
            "estimated_portfolio_return"
        ].idxmin()
    ]

    horizon_unit = period_label_from_frequency(
        summary.frequency_label,
        summary.var_horizon_periods,
    )
    sharpe_text = f"{summary.sharpe_ratio:.2f}" if np.isfinite(summary.sharpe_ratio) else "undefined (zero volatility)"

    comments = [
        (
            f"Annualization uses {summary.periods_per_year} "
            f"{summary.frequency_label.lower()} periods per year "
            f"over approximately {summary.sample_years:.2f} years "
            "of return observations."
        ),
        (
            f"Arithmetic annualized return is "
            f"{summary.annualized_return:.2%}, versus geometric "
            f"CAGR of {summary.cagr:.2%}. Annualized volatility is "
            f"{summary.annualized_volatility:.2%} and the arithmetic "
            f"Sharpe ratio is {sharpe_text}."
        ),
        (
            f"Maximum historical drawdown is "
            f"{summary.max_drawdown:.2%}. Historical {summary.confidence_level:.0%} VaR is "
            f"{summary.historical_var_95:.2%} and CVaR is "
            f"{summary.historical_cvar_95:.2%} over a "
            f"{summary.var_horizon_periods}-{horizon_unit} horizon."
        ),
        contribution_comment,
        (
            f"Worst predefined stress is "
            f"'{worst_stress['scenario']}' with estimated portfolio "
            f"return of "
            f"{worst_stress['estimated_portfolio_return']:.2%}."
        ),
        (
            "Historical VaR/CVaR uses overlapping compounded "
            "returns at the selected horizon. This remains a "
            "simplified historical risk proxy and does not model "
            "liquidity, transaction costs, factor exposures, "
            "non-synchronous prices or intraday risk."
        ),
    ]

    return comments
