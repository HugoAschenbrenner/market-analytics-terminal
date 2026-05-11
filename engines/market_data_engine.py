"""
Free/public market data adapter for the Market Analytics Terminal.

This engine is intentionally optional and lightweight. It supports a desk-style
market snapshot for educational/demo use while keeping the project clear about
its limits: it is not an execution feed, trading signal engine, or bank-grade
market data infrastructure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


DEFAULT_SOURCE = "yfinance"
DATA_MODE = "near-live / delayed public data"
DEFAULT_CACHE_TTL_SECONDS = 60
DISCLAIMER = (
    "Free/public market data adapter for educational and portfolio-demo use only. "
    "Not suitable for trading, execution, commercial redistribution, or bank-grade pricing."
)

_DEFAULT_WATCHLIST = ["SPY", "QQQ", "TLT", "GLD", "AAPL", "MSFT", "NVDA"]
_quote_cache: Dict[Tuple[Tuple[str, ...], str, str], Dict[str, Any]] = {}


@dataclass(frozen=True)
class MarketQuote:
    """Normalized quote payload used by Streamlit and tests."""

    symbol: str
    price: Optional[float]
    change_pct: Optional[float]
    currency: Optional[str]
    source: str
    data_mode: str
    timestamp_utc: str
    status: str
    disclaimer: str
    error: Optional[str] = None


def utc_timestamp() -> str:
    """Return a compact UTC timestamp for transparent data-freshness display."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_symbols(symbols: Iterable[str]) -> List[str]:
    """Clean user-provided tickers while preserving provider-specific suffixes."""
    cleaned: List[str] = []

    for symbol in symbols:
        if symbol is None:
            continue

        value = str(symbol).strip().upper()

        if value:
            cleaned.append(value)

    return list(dict.fromkeys(cleaned))


def default_watchlist() -> List[str]:
    """Return the default cross-asset market snapshot universe."""
    return list(_DEFAULT_WATCHLIST)


def _read_fast_info_currency(fast_info: Any) -> Optional[str]:
    """Read currency defensively from yfinance fast_info object or dict."""
    if fast_info is None:
        return None

    if isinstance(fast_info, dict):
        return fast_info.get("currency")

    return getattr(fast_info, "currency", None)


def build_quote_from_history(
    symbol: str,
    history: pd.DataFrame,
    currency: Optional[str] = None,
    source: str = DEFAULT_SOURCE,
    data_mode: str = DATA_MODE,
) -> Dict[str, Any]:
    """
    Convert a price history DataFrame into a terminal-friendly quote payload.

    The percentage change is calculated from the last two available closes.
    """
    clean_symbol = str(symbol).strip().upper()

    if history is None or history.empty or "Close" not in history.columns:
        return asdict(
            MarketQuote(
                symbol=clean_symbol,
                price=None,
                change_pct=None,
                currency=currency,
                source=source,
                data_mode=data_mode,
                timestamp_utc=utc_timestamp(),
                status="no_data",
                disclaimer=DISCLAIMER,
            )
        )

    closes = pd.to_numeric(history["Close"], errors="coerce").dropna()

    if closes.empty:
        return asdict(
            MarketQuote(
                symbol=clean_symbol,
                price=None,
                change_pct=None,
                currency=currency,
                source=source,
                data_mode=data_mode,
                timestamp_utc=utc_timestamp(),
                status="no_valid_close",
                disclaimer=DISCLAIMER,
            )
        )

    last_price = float(closes.iloc[-1])

    if len(closes) >= 2:
        previous_price = float(closes.iloc[-2])
        change_pct = ((last_price / previous_price) - 1.0) * 100 if previous_price else None
    else:
        change_pct = 0.0

    return asdict(
        MarketQuote(
            symbol=clean_symbol,
            price=round(last_price, 6),
            change_pct=round(change_pct, 4) if change_pct is not None else None,
            currency=currency,
            source=source,
            data_mode=data_mode,
            timestamp_utc=utc_timestamp(),
            status="ok",
            disclaimer=DISCLAIMER,
        )
    )


def _empty_payload(symbols: List[str], status: str, error: Optional[str] = None) -> Dict[str, Any]:
    return {
        "source": DEFAULT_SOURCE,
        "data_mode": DATA_MODE,
        "timestamp_utc": utc_timestamp(),
        "status": status,
        "disclaimer": DISCLAIMER,
        "error": error,
        "quotes": {
            symbol: asdict(
                MarketQuote(
                    symbol=symbol,
                    price=None,
                    change_pct=None,
                    currency=None,
                    source=DEFAULT_SOURCE,
                    data_mode=DATA_MODE,
                    timestamp_utc=utc_timestamp(),
                    status=status,
                    disclaimer=DISCLAIMER,
                    error=error,
                )
            )
            for symbol in symbols
        },
    }


def fetch_yfinance_quotes(
    symbols: Iterable[str],
    period: str = "5d",
    interval: str = "1d",
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Fetch quotes from yfinance with lightweight in-memory caching.

    yfinance is imported lazily so the core app and test suite do not depend on
    internet access unless this optional feature is explicitly used.
    """
    normalized = normalize_symbols(symbols)

    if not normalized:
        return _empty_payload([], "empty_symbol_list")

    cache_key = (tuple(normalized), period, interval)
    now = time.time()
    cached = _quote_cache.get(cache_key)

    if (
        cached is not None
        and not force_refresh
        and now - float(cached["cache_timestamp"]) <= cache_ttl_seconds
    ):
        payload = dict(cached["payload"])
        payload["status"] = "cached"
        return payload

    try:
        import yfinance as yf
    except ImportError:
        return _empty_payload(
            normalized,
            "dependency_missing",
            "yfinance is not installed. Run: python -m pip install -r requirements.txt",
        )

    payload: Dict[str, Any] = {
        "source": DEFAULT_SOURCE,
        "data_mode": DATA_MODE,
        "timestamp_utc": utc_timestamp(),
        "status": "ok",
        "disclaimer": DISCLAIMER,
        "error": None,
        "quotes": {},
    }

    for symbol in normalized:
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period, interval=interval)

            currency = None
            try:
                currency = _read_fast_info_currency(ticker.fast_info)
            except Exception:
                currency = None

            payload["quotes"][symbol] = build_quote_from_history(
                symbol=symbol,
                history=history,
                currency=currency,
            )
        except Exception as exc:
            payload["quotes"][symbol] = asdict(
                MarketQuote(
                    symbol=symbol,
                    price=None,
                    change_pct=None,
                    currency=None,
                    source=DEFAULT_SOURCE,
                    data_mode=DATA_MODE,
                    timestamp_utc=utc_timestamp(),
                    status="error",
                    disclaimer=DISCLAIMER,
                    error=str(exc),
                )
            )

    _quote_cache[cache_key] = {"cache_timestamp": now, "payload": payload}
    return payload


def build_market_snapshot(symbols: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Build the optional market snapshot payload for Streamlit display."""
    watchlist = default_watchlist() if symbols is None else normalize_symbols(symbols)
    return fetch_yfinance_quotes(watchlist)
