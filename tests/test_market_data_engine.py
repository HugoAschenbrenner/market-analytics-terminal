import pandas as pd

from engines.market_data_engine import (
    DATA_MODE,
    DISCLAIMER,
    build_market_snapshot,
    build_quote_from_history,
    default_watchlist,
    fetch_yfinance_quotes,
    normalize_symbols,
)


def test_normalize_symbols_cleans_uppercases_and_deduplicates():
    symbols = [" aapl ", "AAPL", "msft", "", None, "eurusd=x", "brk-b"]

    result = normalize_symbols(symbols)

    assert result == ["AAPL", "MSFT", "EURUSD=X", "BRK-B"]


def test_default_watchlist_returns_independent_copy():
    first = default_watchlist()
    second = default_watchlist()

    first.append("TEST")

    assert "TEST" not in second
    assert "SPY" in second


def test_build_quote_from_history_calculates_last_price_and_change():
    history = pd.DataFrame({"Close": [100.0, 105.0]})

    quote = build_quote_from_history("aapl", history, currency="USD")

    assert quote["symbol"] == "AAPL"
    assert quote["price"] == 105.0
    assert quote["change_pct"] == 5.0
    assert quote["currency"] == "USD"
    assert quote["source"] == "yfinance"
    assert quote["data_mode"] == DATA_MODE
    assert quote["status"] == "ok"
    assert DISCLAIMER in quote["disclaimer"]
    assert quote["timestamp_utc"].endswith("Z")


def test_build_quote_from_history_handles_single_close():
    history = pd.DataFrame({"Close": [101.25]})

    quote = build_quote_from_history("SPY", history)

    assert quote["price"] == 101.25
    assert quote["change_pct"] == 0.0
    assert quote["status"] == "ok"


def test_build_quote_from_history_handles_empty_data():
    quote = build_quote_from_history("MSFT", pd.DataFrame())

    assert quote["symbol"] == "MSFT"
    assert quote["price"] is None
    assert quote["change_pct"] is None
    assert quote["status"] == "no_data"


def test_build_quote_from_history_handles_missing_close_column():
    history = pd.DataFrame({"Price": [100.0, 101.0]})

    quote = build_quote_from_history("SPY", history)

    assert quote["symbol"] == "SPY"
    assert quote["status"] == "no_data"


def test_fetch_yfinance_quotes_handles_empty_symbol_list_without_network():
    payload = fetch_yfinance_quotes([])

    assert payload["source"] == "yfinance"
    assert payload["data_mode"] == DATA_MODE
    assert payload["status"] == "empty_symbol_list"
    assert payload["quotes"] == {}


def test_build_market_snapshot_can_accept_empty_custom_symbols_without_network():
    payload = build_market_snapshot([])

    assert payload["status"] == "empty_symbol_list"
    assert payload["quotes"] == {}
