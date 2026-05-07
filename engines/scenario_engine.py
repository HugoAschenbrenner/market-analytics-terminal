"""
Shared scenario engine for the Multi-Asset Desk Utility Platform.

This module defines standardized market stress scenarios used across:
- Fixed Income Risk
- Repo & Securities Lending
- Structured Products
- Portfolio Risk
- Cross-Asset Dashboard

Financial conventions:
- Rate shocks are stored as decimal rate changes.
  Example: +25 bps = 0.0025.
- Credit spread shocks are stored as decimal spread changes.
  Example: +50 bps = 0.0050.
- Equity, FX, and collateral shocks are stored as decimal returns.
  Example: -10% = -0.10.
- Volatility shocks are stored as absolute volatility point changes in decimal.
  Example: +5 volatility points = 0.05.
- Haircut shocks are stored as absolute percentage point changes in decimal.
  Example: +2 percentage points = 0.02.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Union

ShockValue = Union[float, Dict[str, float]]


@dataclass(frozen=True)
class Scenario:
    """Standardized market stress scenario."""

    name: str
    risk_factor: str
    shock_type: str
    shock_value: ShockValue
    unit: str
    description: str

    def to_dict(self) -> dict:
        """Return scenario as dictionary for tables, exports, or UI display."""
        return asdict(self)


def get_rates_scenarios() -> List[Scenario]:
    """Return standardized rates scenarios."""

    return [
        Scenario(
            name="+25 bps parallel rates shock",
            risk_factor="rates",
            shock_type="parallel_shift",
            shock_value=0.0025,
            unit="decimal_rate_change",
            description="All points of the yield curve increase by 25 bps.",
        ),
        Scenario(
            name="+50 bps parallel rates shock",
            risk_factor="rates",
            shock_type="parallel_shift",
            shock_value=0.0050,
            unit="decimal_rate_change",
            description="All points of the yield curve increase by 50 bps.",
        ),
        Scenario(
            name="-25 bps parallel rates shock",
            risk_factor="rates",
            shock_type="parallel_shift",
            shock_value=-0.0025,
            unit="decimal_rate_change",
            description="All points of the yield curve decrease by 25 bps.",
        ),
        Scenario(
            name="2s10s steepener",
            risk_factor="rates",
            shock_type="curve_steepener",
            shock_value={"2Y": 0.0010, "10Y": 0.0030},
            unit="decimal_rate_change_by_bucket",
            description="Long-end rates rise more than front-end rates.",
        ),
        Scenario(
            name="2s10s flattener",
            risk_factor="rates",
            shock_type="curve_flattener",
            shock_value={"2Y": 0.0030, "10Y": 0.0010},
            unit="decimal_rate_change_by_bucket",
            description="Front-end rates rise more than long-end rates.",
        ),
    ]


def get_credit_scenarios() -> List[Scenario]:
    """Return standardized credit spread scenarios."""

    return [
        Scenario(
            name="Credit spread +25 bps",
            risk_factor="credit",
            shock_type="spread_widening",
            shock_value=0.0025,
            unit="decimal_spread_change",
            description="Credit spreads widen by 25 bps.",
        ),
        Scenario(
            name="Credit spread +50 bps",
            risk_factor="credit",
            shock_type="spread_widening",
            shock_value=0.0050,
            unit="decimal_spread_change",
            description="Credit spreads widen by 50 bps.",
        ),
        Scenario(
            name="Credit spread +100 bps",
            risk_factor="credit",
            shock_type="spread_widening",
            shock_value=0.0100,
            unit="decimal_spread_change",
            description="Credit spreads widen by 100 bps.",
        ),
    ]


def get_equity_scenarios() -> List[Scenario]:
    """Return standardized equity spot scenarios."""

    return [
        Scenario(
            name="Equity spot -5%",
            risk_factor="equity",
            shock_type="spot_return",
            shock_value=-0.05,
            unit="decimal_return",
            description="Equity spot decreases by 5%.",
        ),
        Scenario(
            name="Equity spot -10%",
            risk_factor="equity",
            shock_type="spot_return",
            shock_value=-0.10,
            unit="decimal_return",
            description="Equity spot decreases by 10%.",
        ),
        Scenario(
            name="Equity spot -20%",
            risk_factor="equity",
            shock_type="spot_return",
            shock_value=-0.20,
            unit="decimal_return",
            description="Equity spot decreases by 20%.",
        ),
        Scenario(
            name="Equity spot +5%",
            risk_factor="equity",
            shock_type="spot_return",
            shock_value=0.05,
            unit="decimal_return",
            description="Equity spot increases by 5%.",
        ),
    ]


def get_volatility_scenarios() -> List[Scenario]:
    """Return standardized volatility scenarios."""

    return [
        Scenario(
            name="Volatility +5 points",
            risk_factor="volatility",
            shock_type="vol_points",
            shock_value=0.05,
            unit="absolute_vol_change",
            description="Implied or assumed volatility increases by 5 volatility points.",
        ),
        Scenario(
            name="Volatility +10 points",
            risk_factor="volatility",
            shock_type="vol_points",
            shock_value=0.10,
            unit="absolute_vol_change",
            description="Implied or assumed volatility increases by 10 volatility points.",
        ),
        Scenario(
            name="Volatility -5 points",
            risk_factor="volatility",
            shock_type="vol_points",
            shock_value=-0.05,
            unit="absolute_vol_change",
            description="Implied or assumed volatility decreases by 5 volatility points.",
        ),
    ]


def get_fx_scenarios() -> List[Scenario]:
    """Return standardized FX scenarios."""

    return [
        Scenario(
            name="USD +2%",
            risk_factor="fx",
            shock_type="usd_return",
            shock_value=0.02,
            unit="decimal_return",
            description="USD appreciates by 2% against the relevant currency basket or pair.",
        ),
        Scenario(
            name="USD -2%",
            risk_factor="fx",
            shock_type="usd_return",
            shock_value=-0.02,
            unit="decimal_return",
            description="USD depreciates by 2% against the relevant currency basket or pair.",
        ),
    ]


def get_repo_collateral_scenarios() -> List[Scenario]:
    """Return standardized repo and collateral scenarios."""

    return [
        Scenario(
            name="Collateral -3%",
            risk_factor="collateral",
            shock_type="collateral_return",
            shock_value=-0.03,
            unit="decimal_return",
            description="Collateral market value falls by 3%.",
        ),
        Scenario(
            name="Collateral -5%",
            risk_factor="collateral",
            shock_type="collateral_return",
            shock_value=-0.05,
            unit="decimal_return",
            description="Collateral market value falls by 5%.",
        ),
        Scenario(
            name="Haircut +2 percentage points",
            risk_factor="repo_haircut",
            shock_type="haircut_absolute_change",
            shock_value=0.02,
            unit="absolute_decimal_change",
            description="Repo haircut increases by 2 percentage points.",
        ),
        Scenario(
            name="Haircut +5 percentage points",
            risk_factor="repo_haircut",
            shock_type="haircut_absolute_change",
            shock_value=0.05,
            unit="absolute_decimal_change",
            description="Repo haircut increases by 5 percentage points.",
        ),
    ]


def get_all_scenarios() -> List[Scenario]:
    """Return all predefined scenarios."""

    return (
        get_rates_scenarios()
        + get_credit_scenarios()
        + get_equity_scenarios()
        + get_volatility_scenarios()
        + get_fx_scenarios()
        + get_repo_collateral_scenarios()
    )


def describe_scenario(scenario: Scenario) -> str:
    """Return a compact human-readable scenario description."""

    return (
        f"{scenario.name} | "
        f"Risk factor: {scenario.risk_factor} | "
        f"Shock type: {scenario.shock_type} | "
        f"Unit: {scenario.unit} | "
        f"{scenario.description}"
    )


def scenarios_to_records(scenarios: List[Scenario]) -> List[dict]:
    """Convert a list of scenarios to dictionaries for pandas/UI display."""

    return [scenario.to_dict() for scenario in scenarios]
