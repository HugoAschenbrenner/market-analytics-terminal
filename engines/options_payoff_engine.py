"""
Options payoff engine for the Market Analytics Terminal.

This module provides transparent vanilla option and option-strategy payoff logic
for educational/demo use. It is not an options pricing library, volatility model,
execution system, or bank-grade risk engine.

Scope:
- payoff and P&L at maturity
- simple vanilla strategies
- exact piecewise-linear breakeven detection
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

    if not np.isfinite(numeric_value) or numeric_value <= 0:
        raise ValueError(f"{field_name} must be strictly positive.")

    return numeric_value


def option_leg_intrinsic_value(underlying_prices: Iterable[float], leg: OptionLeg) -> np.ndarray:
    """Calculate intrinsic payoff before premium for one option or underlying leg."""
    prices = np.asarray(list(underlying_prices), dtype=float)
    if not np.isfinite(prices).all() or (prices < 0).any():
        raise ValueError("Underlying prices must be finite and non-negative.")
    if leg.position.lower() not in {"long", "short"}:
        raise ValueError("Option position must be long or short.")
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

    if not np.isfinite(premium) or premium < 0:
        raise ValueError("premium cannot be negative.")

    second_strike = float(strike_2) if strike_2 is not None else None
    second_premium = float(premium_2) if premium_2 is not None else None

    if second_strike is not None:
        validate_positive(second_strike, "strike_2")

    if second_premium is not None and (not np.isfinite(second_premium) or second_premium < 0):
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
        put_premium = premium if second_premium is None else second_premium

        return [
            OptionLeg("call", "long", strike, premium, quantity),
            OptionLeg("put", "long", strike, put_premium, quantity),
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



def calculate_exact_breakevens(
    legs: List[OptionLeg],
    tolerance: float = 1e-10,
) -> List[float]:
    """
    Calculate exact maturity breakevens independently of the display grid.

    Vanilla option-strategy P&L is continuous and piecewise linear in the
    underlying price. Its slope can change only at option strikes. We therefore
    solve for roots on each strike interval and on the final linear tail.

    Underlying prices are constrained to be non-negative.
    """
    if not legs:
        raise ValueError("At least one strategy leg is required.")

    breakpoints = {0.0}

    for leg in legs:
        if leg.strike is not None:
            strike = float(leg.strike)

            if strike < 0:
                raise ValueError("Option strikes cannot be negative.")

            breakpoints.add(strike)

    ordered_points = sorted(breakpoints)

    def pnl_at(price: float) -> float:
        values = calculate_strategy_payoff_table(legs, [price])
        return float(values["pnl"].iloc[0])

    roots: List[float] = []

    def append_root(value: float) -> None:
        if value < -tolerance:
            return

        normalized = max(float(value), 0.0)

        if not any(abs(existing - normalized) <= 1e-6 for existing in roots):
            roots.append(round(normalized, 6))

    # Exact zeros at kinks.
    for point in ordered_points:
        if abs(pnl_at(point)) <= tolerance:
            append_root(point)

    # Roots on bounded linear intervals.
    for left, right in zip(ordered_points[:-1], ordered_points[1:]):
        left_pnl = pnl_at(left)
        right_pnl = pnl_at(right)

        if left_pnl * right_pnl < 0:
            slope = (right_pnl - left_pnl) / (right - left)

            if abs(slope) > tolerance:
                root = left - left_pnl / slope
                append_root(root)

    # Root on the final linear tail above the largest strike.
    tail_start = ordered_points[-1]

    scale_candidates = [1.0, tail_start]

    for leg in legs:
        if leg.initial_spot is not None:
            scale_candidates.append(float(leg.initial_spot))

    tail_step = max(scale_candidates)
    tail_end = tail_start + tail_step

    tail_start_pnl = pnl_at(tail_start)
    tail_end_pnl = pnl_at(tail_end)
    tail_slope = (tail_end_pnl - tail_start_pnl) / tail_step

    if abs(tail_slope) > tolerance:
        tail_root = tail_start - tail_start_pnl / tail_slope

        if tail_root > tail_start + tolerance:
            append_root(tail_root)

    return sorted(roots)


def _strategy_primary_view(strategy: str) -> str:
    """Return concise desk-style positioning for a standard strategy."""
    mapping = {
        "Long Call": "bullish / long convexity",
        "Long Put": "bearish / downside hedge",
        "Short Call": "neutral-to-bearish / short upside convexity",
        "Short Put": "neutral-to-bullish / short downside convexity",
        "Bull Call Spread": "moderately bullish / capped upside",
        "Bear Put Spread": "moderately bearish / capped downside hedge",
        "Long Straddle": "long volatility / large move expected",
        "Long Strangle": "long volatility / cheaper convexity",
        "Covered Call": "income / moderately bullish with capped upside",
        "Protective Put": "long underlying with downside protection",
        "Collar": "protected equity exposure with capped upside",
    }

    return mapping.get(strategy, "strategy-dependent")


def strategy_risk_profile(
    strategy_name: str,
    spot: float,
    strike: float,
    premium: float,
    strike_2: Optional[float] = None,
    premium_2: Optional[float] = None,
    quantity: float = 1.0,
) -> Dict[str, Any]:
    """
    Calculate max gain/loss from the actual piecewise-linear maturity P&L.

    This avoids negative 'max loss' outputs when user-entered premiums imply
    a net-credit or theoretical arbitrage configuration.
    """
    strategy = normalize_strategy_name(strategy_name)
    spot = validate_positive(spot, "spot")
    quantity = validate_positive(quantity, "quantity")

    legs = build_strategy_legs(
        strategy_name=strategy,
        spot=spot,
        strike=strike,
        premium=premium,
        strike_2=strike_2,
        premium_2=premium_2,
        quantity=quantity,
    )

    breakpoints = {0.0}

    for leg in legs:
        if leg.strike is not None:
            breakpoints.add(float(leg.strike))

    ordered_points = sorted(breakpoints)

    scale_candidates = [1.0, spot, ordered_points[-1]]

    for leg in legs:
        if leg.initial_spot is not None:
            scale_candidates.append(float(leg.initial_spot))

    tail_step = max(scale_candidates)
    tail_start = ordered_points[-1]
    tail_end = tail_start + tail_step

    evaluation_prices = ordered_points + [tail_end]
    profile_table = calculate_strategy_payoff_table(legs, evaluation_prices)
    pnl_values = profile_table["pnl"].to_numpy(dtype=float)

    finite_max_pnl = float(np.max(pnl_values))
    finite_min_pnl = float(np.min(pnl_values))

    tail_start_pnl = float(
        calculate_strategy_payoff_table(legs, [tail_start])["pnl"].iloc[0]
    )
    tail_end_pnl = float(
        calculate_strategy_payoff_table(legs, [tail_end])["pnl"].iloc[0]
    )
    tail_slope = (tail_end_pnl - tail_start_pnl) / tail_step

    tolerance = 1e-10

    if tail_slope > tolerance:
        max_pnl: Any = "Unlimited"
        max_gain: Any = "Unlimited"
    else:
        max_pnl = round(finite_max_pnl, 6)
        max_gain = round(max(finite_max_pnl, 0.0), 6)

    if tail_slope < -tolerance:
        min_pnl: Any = "Unbounded below"
        max_loss: Any = "Unlimited"
    else:
        min_pnl = round(finite_min_pnl, 6)
        max_loss = round(max(-finite_min_pnl, 0.0), 6)

    input_warning: Optional[str] = None

    if tail_slope >= -tolerance and finite_min_pnl > tolerance:
        input_warning = (
            "Entered premiums imply a strictly positive maturity P&L across "
            "the full non-negative price domain. Check leg premiums and "
            "no-arbitrage consistency."
        )
    elif tail_slope <= tolerance and finite_max_pnl < -tolerance:
        input_warning = (
            "Entered premiums imply a strictly negative maturity P&L across "
            "the full non-negative price domain. Check leg premiums and "
            "no-arbitrage consistency."
        )

    return {
        "max_gain": max_gain,
        "max_loss": max_loss,
        "max_pnl": max_pnl,
        "min_pnl": min_pnl,
        "tail_slope": round(float(tail_slope), 8),
        "primary_view": _strategy_primary_view(strategy),
        "input_warning": input_warning,
    }


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

    input_warning = risk_profile.get("input_warning")

    if input_warning:
        bullets.append(f"Input consistency warning: {input_warning}")

    return bullets


def build_scenario_table(
    spot: float,
    payoff_table: Optional[pd.DataFrame] = None,
    scenario_moves: Optional[List[float]] = None,
    legs: Optional[List[OptionLeg]] = None,
) -> pd.DataFrame:
    """
    Build maturity scenarios for a strategy.

    Preferred usage passes ``legs`` so each scenario is calculated directly
    from the contractual option legs and remains independent of the chart
    range. ``payoff_table`` is retained only for backward compatibility with
    older internal callers.
    """
    spot = validate_positive(spot, "spot")
    moves = (
        list(scenario_moves)
        if scenario_moves is not None
        else [-0.2, -0.1, 0.0, 0.1, 0.2]
    )

    scenario_prices: List[float] = []

    for move in moves:
        numeric_move = float(move)
        scenario_price = spot * (1.0 + numeric_move)

        if scenario_price < 0:
            raise ValueError(
                "Scenario moves cannot imply a negative underlying price."
            )

        scenario_prices.append(scenario_price)

    rows: List[Dict[str, Any]] = []

    if legs is not None:
        scenario_values = calculate_strategy_payoff_table(
            legs=legs,
            price_grid=scenario_prices,
        )

        for idx, move in enumerate(moves):
            rows.append(
                {
                    "scenario": f"{float(move):+.0%}",
                    "underlying_price": round(
                        float(scenario_values.loc[idx, "underlying_price"]),
                        6,
                    ),
                    "payoff": round(
                        float(scenario_values.loc[idx, "payoff"]),
                        6,
                    ),
                    "pnl": round(
                        float(scenario_values.loc[idx, "pnl"]),
                        6,
                    ),
                }
            )

        return pd.DataFrame(rows)

    if payoff_table is None:
        raise ValueError("Either legs or payoff_table must be supplied.")

    required_columns = {"underlying_price", "payoff", "pnl"}

    if not required_columns.issubset(payoff_table.columns):
        raise ValueError(
            "payoff_table must contain underlying_price, payoff and pnl."
        )

    # Legacy compatibility only. New financial calculations must pass legs.
    grid_prices = payoff_table["underlying_price"].to_numpy(dtype=float)
    grid_payoff = payoff_table["payoff"].to_numpy(dtype=float)
    grid_pnl = payoff_table["pnl"].to_numpy(dtype=float)

    for move, scenario_price in zip(moves, scenario_prices):
        rows.append(
            {
                "scenario": f"{float(move):+.0%}",
                "underlying_price": round(float(scenario_price), 6),
                "payoff": round(
                    float(np.interp(scenario_price, grid_prices, grid_payoff)),
                    6,
                ),
                "pnl": round(
                    float(np.interp(scenario_price, grid_prices, grid_pnl)),
                    6,
                ),
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
    breakevens = calculate_exact_breakevens(legs)
    risk_profile = strategy_risk_profile(
        strategy,
        spot,
        strike,
        premium,
        strike_2,
        premium_2,
        quantity=quantity,
    )
    scenario_table = build_scenario_table(spot=spot, legs=legs)
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
