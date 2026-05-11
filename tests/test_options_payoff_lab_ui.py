import plotly.graph_objects as go

from app_pages.structured_products import (
    _build_options_payoff_figure,
    _first_leg_labels,
    _format_breakevens,
    _format_optional_value,
    _second_leg_labels,
    _strategy_requires_second_leg,
)
from engines.options_payoff_engine import build_options_strategy_snapshot


def test_strategy_requires_second_leg():
    assert _strategy_requires_second_leg("Bull Call Spread") is True
    assert _strategy_requires_second_leg("Bear Put Spread") is True
    assert _strategy_requires_second_leg("Long Strangle") is True
    assert _strategy_requires_second_leg("Collar") is True
    assert _strategy_requires_second_leg("Long Call") is False


def test_first_leg_labels_are_contextual():
    assert _first_leg_labels("Long Strangle") == ("Put strike", "Put premium")
    assert _first_leg_labels("Collar") == ("Protective put strike", "Put premium")
    assert _first_leg_labels("Long Straddle") == ("ATM strike", "Premium per option leg")
    assert _first_leg_labels("Long Call") == ("Strike", "Premium")


def test_second_leg_labels_are_contextual():
    assert _second_leg_labels("Bull Call Spread") == ("Upper call strike", "Short call premium")
    assert _second_leg_labels("Bear Put Spread") == ("Lower put strike", "Short put premium")
    assert _second_leg_labels("Long Strangle") == ("Call strike", "Call premium")
    assert _second_leg_labels("Collar") == ("Short call strike", "Short call premium")


def test_format_breakevens():
    assert _format_breakevens([]) == "N/A"
    assert _format_breakevens([95, 105.1234]) == "95.00, 105.12"


def test_format_optional_value():
    assert _format_optional_value(None) == "N/A"
    assert _format_optional_value("Unlimited") == "Unlimited"
    assert _format_optional_value(12.3456) == "12.35"


def test_build_options_payoff_figure_returns_plotly_figure():
    snapshot = build_options_strategy_snapshot(
        strategy_name="Long Call",
        spot=100,
        strike=100,
        premium=5,
        lower_pct=0.8,
        upper_pct=1.2,
        points=21,
    )

    fig = _build_options_payoff_figure(snapshot)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.layout.title.text == "Long Call Payoff / P&L at Maturity"
