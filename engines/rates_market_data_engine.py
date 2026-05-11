"""
Free/public rates and bond-market snapshot engine.

This module adds an official daily U.S. Treasury curve layer and bond ETF proxy
quotes to the Market Analytics Terminal. It is designed for educational/demo
market context, not live execution, issuer pricing, TRACE replacement, or
bank-grade fixed-income market data infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests

from engines.market_data_engine import fetch_yfinance_quotes


TREASURY_SOURCE = "U.S. Treasury"
TREASURY_DATA_MODE = "official daily public rates"
TREASURY_YIELD_CURVE_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
)
TREASURY_DATA_KEY = "daily_treasury_yield_curve"

BOND_ETF_PROXY_WATCHLIST = ["SHY", "IEF", "TLT", "LQD", "HYG"]

DISCLAIMER = (
    "Official U.S. Treasury curve data and public ETF proxy quotes for educational/demo "
    "use only. This is not individual bond pricing, TRACE data, execution data, "
    "investment advice, or bank-grade market data infrastructure."
)

TREASURY_TERMS = [
    ("1M", "BC_1MONTH"),
    ("2M", "BC_2MONTH"),
    ("3M", "BC_3MONTH"),
    ("4M", "BC_4MONTH"),
    ("6M", "BC_6MONTH"),
    ("1Y", "BC_1YEAR"),
    ("2Y", "BC_2YEAR"),
    ("3Y", "BC_3YEAR"),
    ("5Y", "BC_5YEAR"),
    ("7Y", "BC_7YEAR"),
    ("10Y", "BC_10YEAR"),
    ("20Y", "BC_20YEAR"),
    ("30Y", "BC_30YEAR"),
]

TREASURY_FIELD_TO_TERM = {field: tenor for tenor, field in TREASURY_TERMS}

SAMPLE_CURVE = {
    "1M": 5.35,
    "2M": 5.30,
    "3M": 5.25,
    "4M": 5.20,
    "6M": 5.10,
    "1Y": 4.85,
    "2Y": 4.45,
    "3Y": 4.25,
    "5Y": 4.15,
    "7Y": 4.18,
    "10Y": 4.25,
    "20Y": 4.55,
    "30Y": 4.50,
}


def utc_timestamp() -> str:
    """Return a compact UTC timestamp for data-freshness display."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def current_year() -> int:
    """Return the current UTC year."""
    return datetime.now(timezone.utc).year


def _local_name(tag: str) -> str:
    """Strip XML namespace from a tag name."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _parse_float(value: Optional[str]) -> Optional[float]:
    """Parse Treasury string values into floats, preserving missing values."""
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned or cleaned.lower() in {"n/a", "null", "none"}:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_treasury_date(value: Optional[str]) -> Optional[str]:
    """Normalize Treasury OData date strings to YYYY-MM-DD."""
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    if cleaned.startswith("datetime'") and cleaned.endswith("'"):
        cleaned = cleaned.replace("datetime'", "", 1)[:-1]

    return cleaned.split("T", 1)[0]


def parse_treasury_yield_curve_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    Parse U.S. Treasury Daily Treasury Par Yield Curve XML into records.

    Returns a list of records like:
    {
        "date": "2026-05-08",
        "1M": 4.30,
        "2Y": 3.90,
        "10Y": 4.15,
        ...
    }
    """
    root = ET.fromstring(xml_text)
    records: List[Dict[str, Any]] = []

    for element in root.iter():
        if _local_name(element.tag) != "properties":
            continue

        record: Dict[str, Any] = {}

        for child in list(element):
            key = _local_name(child.tag)
            value = child.text

            if key == "NEW_DATE":
                parsed_date = _parse_treasury_date(value)
                if parsed_date:
                    record["date"] = parsed_date

            elif key in TREASURY_FIELD_TO_TERM:
                tenor = TREASURY_FIELD_TO_TERM[key]
                parsed_value = _parse_float(value)
                if parsed_value is not None:
                    record[tenor] = parsed_value

        if "date" in record:
            records.append(record)

    return records


def select_latest_curve_record(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Select the latest record with at least one valid Treasury tenor."""
    valid_records = []

    for record in records:
        valid_tenors = [tenor for tenor, _ in TREASURY_TERMS if tenor in record]
        if record.get("date") and valid_tenors:
            valid_records.append(record)

    if not valid_records:
        return {}

    return sorted(valid_records, key=lambda row: str(row["date"]))[-1]


def calculate_curve_spreads_bps(curve: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Calculate key curve spreads in basis points."""
    def spread(long_tenor: str, short_tenor: str) -> Optional[float]:
        if long_tenor not in curve or short_tenor not in curve:
            return None
        return round((float(curve[long_tenor]) - float(curve[short_tenor])) * 100, 1)

    return {
        "3m10y_bps": spread("10Y", "3M"),
        "2s10s_bps": spread("10Y", "2Y"),
        "5s30s_bps": spread("30Y", "5Y"),
    }


def classify_curve_regime(spreads_bps: Dict[str, Optional[float]]) -> str:
    """
    Classify the curve using 2s10s.

    Thresholds are deliberately simple and transparent for demo/education:
    - below -25 bps: inverted
    - between -25 and +25 bps: flat
    - above +25 bps: steep
    """
    two_ten = spreads_bps.get("2s10s_bps")

    if two_ten is None:
        return "insufficient data"

    if two_ten < -25:
        return "inverted"

    if two_ten <= 25:
        return "flat"

    return "steep"


def generate_rates_desk_read(
    curve: Dict[str, float],
    spreads_bps: Dict[str, Optional[float]],
    curve_regime: str,
) -> List[str]:
    """Generate fixed-income desk-style interpretation from the curve snapshot."""
    desk_read = []

    two_ten = spreads_bps.get("2s10s_bps")
    five_thirty = spreads_bps.get("5s30s_bps")
    three_month_ten = spreads_bps.get("3m10y_bps")

    if curve_regime == "inverted":
        desk_read.append(
            "Curve regime is inverted: front-end yields remain above the long end, "
            "consistent with restrictive policy pricing and weaker forward growth expectations."
        )
    elif curve_regime == "flat":
        desk_read.append(
            "Curve regime is flat: carry/rolldown is less generous and parallel-rate risk "
            "can dominate simple duration exposure."
        )
    elif curve_regime == "steep":
        desk_read.append(
            "Curve regime is steep: long-end duration risk, term premium, issuance pressure, "
            "and inflation risk should be monitored."
        )
    else:
        desk_read.append("Curve regime cannot be classified because key tenors are missing.")

    if two_ten is not None:
        desk_read.append(f"2s10s spread is {two_ten:+.1f} bps, the main policy-vs-growth curve signal.")

    if five_thirty is not None:
        desk_read.append(f"5s30s spread is {five_thirty:+.1f} bps, useful for long-end steepening/flattening risk.")

    if three_month_ten is not None:
        desk_read.append(f"3m10y spread is {three_month_ten:+.1f} bps, useful for front-end policy tightness context.")

    if "10Y" in curve:
        desk_read.append(f"10Y Treasury yield is {curve['10Y']:.2f}%, anchoring long-duration risk and discount-rate sensitivity.")

    return desk_read


def build_curve_table(curve: Dict[str, float]) -> List[Dict[str, Any]]:
    """Build ordered curve table for Streamlit display."""
    table = []

    for tenor, _ in TREASURY_TERMS:
        table.append(
            {
                "tenor": tenor,
                "yield_pct": round(float(curve[tenor]), 4) if tenor in curve else None,
            }
        )

    return table


def build_treasury_curve_payload(
    curve: Dict[str, float],
    as_of_date: Optional[str],
    status: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build normalized Treasury curve payload."""
    spreads_bps = calculate_curve_spreads_bps(curve)
    curve_regime = classify_curve_regime(spreads_bps)

    return {
        "source": TREASURY_SOURCE,
        "data_mode": TREASURY_DATA_MODE,
        "status": status,
        "timestamp_utc": utc_timestamp(),
        "as_of_date": as_of_date,
        "curve": curve,
        "curve_table": build_curve_table(curve),
        "spreads_bps": spreads_bps,
        "curve_regime": curve_regime,
        "desk_read": generate_rates_desk_read(curve, spreads_bps, curve_regime),
        "disclaimer": DISCLAIMER,
        "error": error,
    }


def build_sample_treasury_curve_payload(status: str = "sample_fallback", error: Optional[str] = None) -> Dict[str, Any]:
    """Build transparent sample fallback payload if public data is unavailable."""
    return build_treasury_curve_payload(
        curve=dict(SAMPLE_CURVE),
        as_of_date="sample",
        status=status,
        error=error,
    )


def fetch_treasury_yield_curve(
    year: Optional[int] = None,
    timeout: int = 10,
    fallback_to_sample: bool = True,
) -> Dict[str, Any]:
    """
    Fetch official daily Treasury par yield curve rates.

    Uses the public U.S. Treasury XML feed. If the current year has no valid data,
    the previous year is tried once. If public data is unavailable and fallback is
    enabled, a transparent sample fallback is returned.
    """
    requested_year = int(year or current_year())
    years_to_try = [requested_year, requested_year - 1]

    last_error: Optional[str] = None

    for candidate_year in years_to_try:
        try:
            response = requests.get(
                TREASURY_YIELD_CURVE_URL,
                params={
                    "data": TREASURY_DATA_KEY,
                    "field_tdr_date_value": candidate_year,
                },
                timeout=timeout,
            )
            response.raise_for_status()

            records = parse_treasury_yield_curve_xml(response.text)
            latest_record = select_latest_curve_record(records)

            if latest_record:
                curve = {
                    tenor: float(latest_record[tenor])
                    for tenor, _ in TREASURY_TERMS
                    if tenor in latest_record
                }
                return build_treasury_curve_payload(
                    curve=curve,
                    as_of_date=str(latest_record.get("date")),
                    status="ok",
                )

            last_error = f"No valid Treasury curve records found for {candidate_year}."

        except Exception as exc:
            last_error = str(exc)

    if fallback_to_sample:
        return build_sample_treasury_curve_payload(error=last_error)

    return build_treasury_curve_payload(
        curve={},
        as_of_date=None,
        status="error",
        error=last_error,
    )


def curve_payload_to_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
    """Convert a curve payload to a display-ready DataFrame."""
    return pd.DataFrame(payload.get("curve_table", []), columns=["tenor", "yield_pct"])


def spreads_payload_to_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
    """Convert spread payload to a display-ready DataFrame."""
    spreads = payload.get("spreads_bps", {})

    labels = {
        "3m10y_bps": "3M10Y",
        "2s10s_bps": "2s10s",
        "5s30s_bps": "5s30s",
    }

    rows = [
        {
            "spread": labels.get(key, key),
            "value_bps": value,
        }
        for key, value in spreads.items()
    ]

    return pd.DataFrame(rows, columns=["spread", "value_bps"])


def bond_proxy_quotes_to_dataframe(quotes_payload: Dict[str, Any]) -> pd.DataFrame:
    """Convert yfinance bond ETF proxy quotes to a display-ready DataFrame."""
    rows = []

    for symbol, quote in quotes_payload.get("quotes", {}).items():
        rows.append(
            {
                "symbol": quote.get("symbol", symbol),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct"),
                "currency": quote.get("currency") or "",
                "status": quote.get("status"),
                "source": quote.get("source", quotes_payload.get("source")),
                "data_mode": quote.get("data_mode", quotes_payload.get("data_mode")),
                "timestamp_utc": quote.get("timestamp_utc", quotes_payload.get("timestamp_utc")),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "symbol",
            "price",
            "change_pct",
            "currency",
            "status",
            "source",
            "data_mode",
            "timestamp_utc",
        ],
    )


def build_rates_and_bond_market_snapshot(
    bond_etf_symbols: Optional[Iterable[str]] = None,
    include_bond_etfs: bool = True,
) -> Dict[str, Any]:
    """
    Build combined rates and bond ETF proxy snapshot.

    The Treasury curve is official daily public data. Bond ETF prices are public
    ETF proxies, not individual bond prices or executable quotes.
    """
    treasury_curve = fetch_treasury_yield_curve(fallback_to_sample=True)

    bond_etf_proxies: Dict[str, Any] = {}

    if include_bond_etfs:
        symbols = list(bond_etf_symbols or BOND_ETF_PROXY_WATCHLIST)
        bond_etf_proxies = fetch_yfinance_quotes(
            symbols=symbols,
            period="5d",
            interval="1d",
            force_refresh=True,
        )

    return {
        "source": "U.S. Treasury + yfinance ETF proxies",
        "data_mode": "official daily rates + public ETF proxy quotes",
        "timestamp_utc": utc_timestamp(),
        "treasury_curve": treasury_curve,
        "bond_etf_proxies": bond_etf_proxies,
        "disclaimer": DISCLAIMER,
    }
