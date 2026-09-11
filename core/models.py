"""Shared contracts. Financial values are independent of display language/theme."""
from dataclasses import dataclass, field
from datetime import date
import pandas as pd

ASSET_CLASSES = ("Equity", "Bond", "FX", "Option", "Structured", "Cash")
CURRENCIES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD")

@dataclass
class MarketState:
    as_of: str = "2026-09-09"
    source: str = "SYNTHETIC"
    spots: dict = field(default_factory=lambda: {"SPY": 550., "QQQ": 475., "SX5E": 5000., "EURUSD": 1.10, "VIX": 20.})
    fx: dict = field(default_factory=lambda: {"USD": 1., "EUR": 1.10, "GBP": 1.28, "JPY": .0068, "CHF": 1.15, "CAD": .74, "AUD": .67})
    rates: dict = field(default_factory=lambda: {"USD": .04, "EUR": .025, "GBP": .045, "JPY": .01, "CHF": .01, "CAD": .03, "AUD": .035})
    curves: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    revision: int = 0

@dataclass
class PositionBook:
    positions: pd.DataFrame
    name: str = "balanced"
    base_currency: str = "USD"
    source: str = "SYNTHETIC"
    revision: int = 0
    repo_cash: float = 0.
    repo_rate: float = .04
    repo_haircut: float = .10
    repo_days: int = 30
    collateral_id: str = ""
    structured_terms: dict = field(default_factory=dict)
    financing_terms: dict = field(default_factory=dict)
    lending_terms: dict = field(default_factory=dict)

@dataclass
class RiskState:
    confidence: float = .975
    estimator: str = "sample"
    horizon: int = 1
    results: dict = field(default_factory=dict)

@dataclass
class ScenarioState:
    name: str = "risk_off"
    shocks: dict = field(default_factory=dict)

@dataclass
class UIState:
    language: str = "en"
    theme: str = "dark"
    page: str = "overview"

@dataclass
class TerminalState:
    book: PositionBook
    market: MarketState = field(default_factory=MarketState)
    risk: RiskState = field(default_factory=RiskState)
    scenario: ScenarioState = field(default_factory=ScenarioState)
    ui: UIState = field(default_factory=UIState)
    valuation_date: date = field(default_factory=date.today)
