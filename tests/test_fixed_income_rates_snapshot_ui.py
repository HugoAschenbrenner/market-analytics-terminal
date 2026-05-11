from app_pages.fixed_income import (
    _format_optional_number,
    _parse_bond_proxy_watchlist_text,
)


def test_parse_bond_proxy_watchlist_text_normalizes_and_deduplicates():
    result = _parse_bond_proxy_watchlist_text(" shy, ief, TLT, , lqd, hyg, SHY ")

    assert result == ["SHY", "IEF", "TLT", "LQD", "HYG"]


def test_format_optional_number_handles_valid_number():
    result = _format_optional_number(4.2567, decimals=2, suffix="%")

    assert result == "4.26%"


def test_format_optional_number_handles_missing_value():
    result = _format_optional_number(None, decimals=2, suffix="%")

    assert result == "N/A"
