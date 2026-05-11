"""
Options payoff engine for the Market Analytics Terminal.

This module provides transparent vanilla option and option-strategy payoff logic
for educational/demo use. It is not an options pricing library, volatility model,
execution system, or bank-grade risk engine.

Scope:
- payoff and P&L at maturity
- simple vanilla strategies
- breakeven detection on a price grid
- scenario table
- desk-style interpretation for sales/structuring discussion
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


DISCLAIMER = (
    "Options payoff analytics are maturity payoff/P&L proxies for educational and demo use only. "
    "They do not model implied volatility, early exercise, funding, dividends, transaction costs, "
    "margin, liquidity, or executable market pricing."
)

SUPPORTED_STRATEGIES = [
    "Long Call",
    "Long Put",
    "Short Call",
    "Short Put",
    "Bull Call Spread",
    "Bear Put Spread",
    "Long Straddle",
    "Long Strangle",
    "Covered Call",
    "Protective Put",
    "Collar",
]


@dataclass(frozen=True)
class OptionLeg:
    """Single option or underlying leg used to build strategy payoff."""

    instrument: str
    position: str
    strike: Optional[float] = None
    premium: float = 0.0
    quantity: float = 1.0
    initial_spot: Optional[float] = None


def normalize_strategy_name(strategy_name: str) -> str:
    """Normalize strategy labels while preserving display names."""
    if not strategy_name:
        raise ValueError("Strategy name cannot be empty.")

    cleaned = " ".join(str(strategy_name).strip().split()).lower()
    mapping = {name.lower(): name for name in SUPPORTED_STRATEGIES}

    if cleaned not in mapping:
        raise ValueError(
            f"Unsupported strategy: {strategy_name}. "
            f"Supported strategies: {', '.join(SUPPORTED_STRATEGIES)}"
        )

    return mapping[cleaned]


def validate_positive(value: float, field_name: str) -> float:
    """Validate strictly positive numeric inputs."""
    numeric_value = float(value)

    if numeric_value <= 0:
        raise ValueError(f"{field_name} must be strictly positive.")

    return numeric_value


def option_leg_intrinsic_value(underlying_prices: Iterable[float], leg: OptionLeg) -> np.ndarray:
    """Calculate intrinsic payoff before premium for one option or underlying leg."""
    prices = np.asarray(list(underlying_prices), dtype=float)
    position_sign = 1.0 if leg.position.lower() == "long" else -1.0
    quantity = float(leg.quantity)

    if leg.instrument == "call":
        if leg.strike is None:
            raise ValueError("Call option leg requires a strike.")
        intrinsic = np.maximum(prices - float(leg.strike), 0.0)

    elif leg.instrument == "put":
        if leg.strike is None:
            raise ValueError("Put option leg requires a strike.")
        intrinsic = np.maximum(float(leg.strike) - prices, 0.0)

    elif leg.instrument == "underlying":
        if leg.initial_spot is None:
            raise ValueError("Underlying leg requires initial_spot.")
        intrinsic = prices - float(leg.initial_spot)

    else:
        raise ValueError(f"Unsupported instrument: {leg.instrument}")

    return position_sign * quantity * intrinsic


def option_leg_pnl(underlying_prices: Iterable[float], leg: OptionLeg) -> np.ndarray:
    """Calculate maturity P&L for one option or underlying leg."""
    intrinsic = option_leg_intrinsic_value(underlying_prices, leg)
    position_sign = 1.0 if leg.position.lower() == "long" else -1.0

    if leg.instrument in {"call", "put"}:
        premium_cashflow = -position_sign * float(leg.premium) * float(leg.quantity)
    else:
        premium_cashflow = 0.0

    return intrinsic + premium_cashflow


def build_price_grid(
    spot: float,
    lower_pct: float = 0.5,
    upper_pct: float = 1.5,
    points: int = 101,
) -> np.ndarray:
    """Build an underlying price grid around spot."""
    spot = validate_positive(spot, "spot")
    lower_pct = validate_positive(lower_pct, "lower_pct")
    upper_pct = validate_positive(upper_pct, "upper_pct")

    if upper_pct <= lower_pct:
        raise ValueError("upper_pct must be greater than lower_pct.")

    if int(points) < 5:
        raise ValueError("points must be at least 5.")

    return np.linspace(spot * lower_pct, spot * upper_pct, int(points))


def build_strategy_legs(
    strategy_name: str,
    spot: float,
    strike: float,
    premium: float,
    strike_2: Optional[float] = None,
    premium_2: Optional[float] = None,
    quantity: float = 1.0,
) -> List[OptionLeg]:
    """
    Build standard option strategy legs.

    strike_2 and premium_2 are used by spreads, strangles, and collars.
    """
    strategy = normalize_strategy_name(strategy_name)
    spot = validate_positive(spot, "spot")
    strike = validate_positive(strike, "strike")
    premium = float(premium)
    quantity = validate_positive(quantity, "quantity")

    if premium < 0:
        raise ValueError("premium cannot be negative.")

    second_strike = float(strike_2) if strike_2 is not None else None
    second_premium = float(premium_2) if premium_2 is not None else None

    if second_strike is not None:
        validate_positive(second_strike, "strike_2")

    if second_premium is not None and second_premium < 0:
        raise ValueError("premium_2 cannot be negative.")

    if strategy == "Long Call":
        return [OptionLeg("call", "long", strike, premium, quantity)]

    if strategy == "Long Put":
        return [OptionLeg("put", "long", strike, premium, quantity)]

    if strategy == "Short Call":
        return [OptionLeg("call", "short", strike, premium, quantity)]

    if strategy == "Short Put":
        return [OptionLeg("put", "short", strike, premium, quantity)]

    if strategy == "Bull Call Spread":
        if second_strike is None or second_premium is None:
            raise ValueError("Bull Call Spread requires strike_2 and premium_2.")
        if second_strike <= strike:
            raise ValueError("Bull Call Spread requires strike_2 above strike.")
        return [
            OptionLeg("call", "long", strike, premium, quantity),
            OptionLeg("call", "short", second_strike, second_premium, quantity),
        ]

    if strategy == "Bear Put Spread":
        if second_strike is None or second_premium is None:
            raise ValueError("Bear Put Spread requires strike_2 and premium_2.")
        if second_strike >= strike:
            raise ValueError("Bear Put Spread requires strike_2 below strike.")
        return [
            OptionLeg("put", "long", strike, premium, quantity),
            OptionLeg("put", "short", second_strike, second_premium, quantity),
        ]

    if strategy == "Long Straddle":
        return [
            OptionLeg("call", "long", strike, premium, quantity),
            OptionLeg("put", "long", strike, premium, quantity),
        ]

    if strategy == "Long Strangle":
        if second_strike is None or second_premium is None:
            raise ValueError("Long Strangle requires strike_2 and premium_2.")
        if second_strike <= strike:
            raise ValueError("Long Strangle requires strike_2 above strike.")
        return [
            OptionLeg("put", "long", strike, premium, quantity),
            OptionLeg("call", "long", second_strike, second_premium, quantity),
        ]

    if strategy == "Covered Call":
        return [
            OptionLeg("underlying", "long", initial_spot=spot, quantity=quantity),
            OptionLeg("call", "short", strike, premium, quantity),
        ]

    if strategy == "Protective Put":
        return [
            OptionLeg("underlying", "long", initial_spot=spot, quantity=quantity),
            OptionLeg("put", "long", strike, premium, quantity),
        ]

    if strategy == "Collar":
        if second_strike is None or second_premium is None:
            raise ValueError("Collar requires strike_2 and premium_2.")
        if second_strike <= strike:
            raise ValueError("Collar requires strike_2 above strike.")
        return [
            OptionLeg("underlying", "long", initial_spot=spot, quantity=quantity),
            OptionLeg("put", "long", strike, premium, quantity),
            OptionLeg("call", "short", second_strike, second_premium, quantity),
        ]

    raise ValueError(f"Unsupported strategy: {strategy_name}")


def calculate_strategy_payoff_table(
    legs: List[OptionLeg],
    price_grid: Iterable[float],
) -> pd.DataFrame:
    """Calculate payoff and P&L across the underlying price grid."""
    prices = np.asarray(list(price_grid), dtype=float)

    total_payoff = np.zeros_like(prices)
    total_pnl = np.zeros_like(prices)

    for leg in legs:
        total_payoff += option_leg_intrinsic_value(prices, leg)
        total_pnl += option_leg_pnl(prices, leg)

    return pd.DataFrame(
        {
            "underlying_price": prices,
            "payoff": total_payoff,
            "pnl": total_pnl,
        }
    )


def estimate_breakevens(payoff_table: pd.DataFrame) -> List[float]:
    """Estimate breakevens through linear interpolation on the P&L grid."""
    prices = payoff_table["underlying_price"].to_numpy(dtype=float)
    pnl = payoff_table["pnl"].to_numpy(dtype=float)

    breakevens: List[float] = []

    for i in range(1, len(prices)):
        previous_pnl = pnl[i - 1]
        current_pnl = pnl[i]

        if previous_pnl == 0:
            breakevens.append(round(float(prices[i - 1]), 6))

        if previous_pnl * current_pnl < 0:
            weight = abs(previous_pnl) / (abs(previous_pnl) + abs(current_pnl))
            breakeven = prices[i - 1] + weight * (prices[i] - prices[i - 1])
            breakevens.append(round(float(breakeven), 6))

    if pnl[-1] == 0:
        breakevens.append(round(float(prices[-1]), 6))

    deduplicated = []

    for value in breakevens:
        if value not in deduplicated:
            deduplicated.append(value)

    return deduplicated


def strategy_risk_profile(
    strategy_name: str,
    spot: float,
    strike: float,
    premium: float,
    strike_2: Optional[float] = None,
    premium_2: Optional[float] = None,
    quantity: float = 1.0,
) -> Dict[str, Any]:
    """Return transparent total risk profile where simple formulas apply."""
    strategy = normalize_strategy_name(strategy_name)
    spot = float(spot)
    strike = float(strike)
    premium = float(premium)
    quantity = validate_positive(quantity, "quantity")
    strike_2_value = float(strike_2) if strike_2 is not None else None
    premium_2_value = float(premium_2) if premium_2 is not None else None

    if strategy == "Long Call":
        return {"max_gain": "Unlimited", "max_loss": round(premium * quantity, 6), "primary_view": "bullish / long convexity"}

    if strategy == "Long Put":
        return {"max_gain": round(max(strike - premium, 0) * quantity, 6), "max_loss": round(premium * quantity, 6), "primary_view": "bearish / downside hedge"}

    if strategy == "Short Call":
        return {"max_gain": round(premium * quantity, 6), "max_loss": "Unlimited", "primary_view": "neutral-to-bearish / short upside convexity"}

    if strategy == "Short Put":
        return {"max_gain": round(premium * quantity, 6), "max_loss": round(max(strike - premium, 0) * quantity, 6), "primary_view": "neutral-to-bullish / short downside convexity"}

    if strategy == "Bull Call Spread" and strike_2_value is not None and premium_2_value is not None:
        net_premium = premium - premium_2_value
        width = strike_2_value - strike
        return {"max_gain": round((width - net_premium) * quantity, 6), "max_loss": round(net_premium * quantity, 6), "primary_view": "moderately bullish / capped upside"}

    if strategy == "Bear Put Spread" and strike_2_value is not None and premium_2_value is not None:
        net_premium = premium - premium_2_value
        width = strike - strike_2_value
        return {"max_gain": round((width - net_premium) * quantity, 6), "max_loss": round(net_premium * quantity, 6), "primary_view": "moderately bearish / capped downside hedge"}

    if strategy == "Long Straddle":
        total_premium = premium * 2
        return {"max_gain": "Unlimited", "max_loss": round(total_premium * quantity, 6), "primary_view": "long volatility / large move expected"}

    if strategy == "Long Strangle" and premium_2_value is not None:
        total_premium = premium + premium_2_value
        return {"max_gain": "Unlimited", "max_loss": round(total_premium * quantity, 6), "primary_view": "long volatility / cheaper convexity"}

    if strategy == "Covered Call":
        return {
            "max_gain": round(max(strike - spot + premium, 0) * quantity, 6),
            "max_loss": round(max(spot - premium, 0) * quantity, 6),
            "primary_view": "income / moderately bullish with capped upside",
        }

    if strategy == "Protective Put":
        return {
            "max_gain": "Unlimited",
            "max_loss": round(max(spot + premium - strike, 0) * quantity, 6),
            "primary_view": "long underlying with downside protection",
        }

    if strategy == "Collar" and strike_2_value is not None and premium_2_value is not None:
        net_premium = premium - premium_2_value
        return {
            "max_gain": round((strike_2_value - spot - net_premium) * quantity, 6),
            "max_loss": round(max(spot + net_premium - strike, 0) * quantity, 6),
            "primary_view": "protected equity exposure with capped upside",
        }

    return {"max_gain": "Grid-dependent", "max_loss": "Grid-dependent", "primary_view": "strategy-dependent"}


def generate_strategy_desk_interpretation(strategy_name: str, risk_profile: Dict[str, Any]) -> List[str]:
    """Generate desk-style interpretation bullets for the selected strategy."""
    strategy = normalize_strategy_name(strategy_name)
    view = risk_profile.get("primary_view", "strategy-dependent")

    bullets = [
        f"Strategy expresses a {view} view.",
        "Payoff is shown at maturity and does not model volatility path, funding, margin, or liquidity.",
    ]

    if strategy in {"Long Call", "Bull Call Spread"}:
        bullets.append("Investor rationale: upside participation with defined premium at risk.")
        bullets.append("Key risk: option premium can be lost if the underlying fails to move enough.")

    elif strategy in {"Long Put", "Bear Put Spread", "Protective Put"}:
        bullets.append("Investor rationale: downside protection or bearish expression with defined premium cost.")
        bullets.append("Key risk: protection cost reduces returns if the underlying is stable or rallies.")

    elif strategy in {"Short Call", "Short Put", "Covered Call"}:
        bullets.append("Investor rationale: premium income / yield enhancement.")
        bullets.append("Key risk: short optionality can create asymmetric losses or capped upside.")

    elif strategy in {"Long Straddle", "Long Strangle"}:
        bullets.append("Investor rationale: monetize a large move in either direction.")
        bullets.append("Key risk: theta bleed / premium loss if realized move is insufficient.")

    elif strategy == "Collar":
        bullets.append("Investor rationale: reduce downside risk while financing protection through capped upside.")
        bullets.append("Key risk: upside is limited above the short call strike.")

    return bullets


def build_scenario_table(
    spot: float,
    payoff_table: pd.DataFrame,
    scenario_moves: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Build simple scenario table by interpolating strategy P&L."""
    spot = float(spot)
    moves = scenario_moves or [-0.2, -0.1, 0.0, 0.1, 0.2]

    prices = payoff_table["underlying_price"].to_numpy(dtype=float)
    pnl = payoff_table["pnl"].to_numpy(dtype=float)
    payoff = payoff_table["payoff"].to_numpy(dtype=float)

    rows = []

    for move in moves:
        scenario_price = spot * (1 + move)
        interpolated_pnl = float(np.interp(scenario_price, prices, pnl))
        interpolated_payoff = float(np.interp(scenario_price, prices, payoff))

        rows.append(
            {
                "scenario": f"{move:+.0%}",
                "underlying_price": round(scenario_price, 6),
                "payoff": round(interpolated_payoff, 6),
                "pnl": round(interpolated_pnl, 6),
            }
        )

    return pd.DataFrame(rows)


def build_options_strategy_snapshot(
    strategy_name: str,
    spot: float,
    strike: float,
    premium: float,
    strike_2: Optional[float] = None,
    premium_2: Optional[float] = None,
    quantity: float = 1.0,
    lower_pct: float = 0.5,
    upper_pct: float = 1.5,
    points: int = 101,
) -> Dict[str, Any]:
    """Build full option strategy analytics payload for UI display."""
    strategy = normalize_strategy_name(strategy_name)
    legs = build_strategy_legs(
        strategy_name=strategy,
        spot=spot,
        strike=strike,
        premium=premium,
        strike_2=strike_2,
        premium_2=premium_2,
        quantity=quantity,
    )
    price_grid = build_price_grid(spot, lower_pct=lower_pct, upper_pct=upper_pct, points=points)
    payoff_table = calculate_strategy_payoff_table(legs, price_grid)
    breakevens = estimate_breakevens(payoff_table)
    risk_profile = strategy_risk_profile(
        strategy,
        spot,
        strike,
        premium,
        strike_2,
        premium_2,
        quantity=quantity,
    )
    scenario_table = build_scenario_table(spot, payoff_table)
    desk_interpretation = generate_strategy_desk_interpretation(strategy, risk_profile)

    return {
        "strategy": strategy,
        "spot": float(spot),
        "legs": [asdict(leg) for leg in legs],
        "payoff_table": payoff_table,
        "scenario_table": scenario_table,
        "breakevens": breakevens,
        "risk_profile": risk_profile,
        "desk_interpretation": desk_interpretation,
        "disclaimer": DISCLAIMER,
    }
