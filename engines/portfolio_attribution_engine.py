"""V2 Gaussian attribution adapter; the stable V1 portfolio engine stays frozen."""
import pandas as pd
from engines.portfolio_risk_engine import validate_weights


def calculate_portfolio_attribution(returns_df: pd.DataFrame, weights: dict[str, float],
                                    confidence: float = .95, horizon: int = 1,
                                    correlation_blend: float = .0) -> dict:
    """Extend the existing long-only return model with Gaussian Euler risk and PCA.

    Output risk is a portfolio return per observation/horizon, never currency P&L.
    Historical VaR remains in summarize_portfolio_risk and is not overwritten.
    """
    from engines.risk_factor_engine import covariance_estimate, covariance_attribution, correlation_stress
    validated=validate_weights(returns_df,weights)
    data=returns_df[list(validated)]
    covariance,_=covariance_estimate(data)
    base=covariance_attribution(covariance,list(validated.values()),data.columns,confidence,horizon)
    stressed=covariance_attribution(correlation_stress(covariance,correlation_blend),list(validated.values()),data.columns,confidence,horizon)
    return dict(base=base,stressed=stressed,correlation_blend=correlation_blend)
