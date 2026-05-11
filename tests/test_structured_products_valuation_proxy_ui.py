import pandas as pd
import pytest

from app_pages.structured_products import (
    _event_breakdown_to_dataframe,
    _format_money_value,
    _format_probability,
    _parse_float_list,
)


def test_parse_float_list_validates_length_and_positive_values():
    assert _parse_float_list("100, 95, 110", 3, "spots") == [100.0, 95.0, 110.0]

    with pytest.raises(ValueError):
        _parse_float_list("100, 95", 3, "spots")

    with pytest.raises(ValueError):
        _parse_float_list("100, -95, 110", 3, "spots")


def test_format_probability():
    assert _format_probability(0.1234) == "12.3%"
    assert _format_probability(None) == "N/A"


def test_format_money_value():
    assert _format_money_value(1234.567) == "1,234.57"
    assert _format_money_value(None) == "N/A"


def test_event_breakdown_to_dataframe():
    cashflows = pd.DataFrame(
        {
            "event_type": [
                "autocall",
                "autocall",
                "maturity_coupon_paid",
                "maturity_capital_loss",
            ]
        }
    )

    breakdown = _event_breakdown_to_dataframe(cashflows)

    assert list(breakdown.columns) == ["event_type", "count", "probability"]
    assert breakdown.loc[breakdown["event_type"] == "autocall", "count"].iloc[0] == 2
    assert breakdown.loc[breakdown["event_type"] == "autocall", "probability"].iloc[0] == 0.5
