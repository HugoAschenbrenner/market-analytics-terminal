import pandas as pd

from app_pages.cross_asset_dashboard import (
    _market_snapshot_to_dataframe,
    _parse_watchlist_text,
)


def test_parse_watchlist_text_normalizes_symbols():
    result = _parse_watchlist_text(" spy, qqq, , eurusd=x, SPY ")

    assert result == ["SPY", "QQQ", "EURUSD=X"]


def test_market_snapshot_to_dataframe_returns_expected_table():
    payload = {
        "source": "yfinance",
        "data_mode": "near-live / delayed public data",
        "timestamp_utc": "2026-05-10T20:00:00Z",
        "quotes": {
            "SPY": {
                "symbol": "SPY",
                "price": 500.123456,
                "change_pct": 0.45,
                "currency": "USD",
                "status": "ok",
                "source": "yfinance",
                "data_mode": "near-live / delayed public data",
                "timestamp_utc": "2026-05-10T20:00:00Z",
            },
            "TLT": {
                "symbol": "TLT",
                "price": None,
                "change_pct": None,
                "currency": None,
                "status": "no_data",
                "source": "yfinance",
                "data_mode": "near-live / delayed public data",
                "timestamp_utc": "2026-05-10T20:00:00Z",
            },
        },
    }

    df = _market_snapshot_to_dataframe(payload)

    assert isinstance(df, pd.DataFrame)
    assert list(df["symbol"]) == ["SPY", "TLT"]
    assert list(df["status"]) == ["ok", "no_data"]
    assert "price" in df.columns
    assert "change_pct" in df.columns
    assert "timestamp_utc" in df.columns
