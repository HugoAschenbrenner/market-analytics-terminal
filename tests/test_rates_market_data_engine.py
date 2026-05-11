from engines.rates_market_data_engine import (
    DISCLAIMER,
    TREASURY_DATA_MODE,
    build_curve_table,
    build_sample_treasury_curve_payload,
    calculate_curve_spreads_bps,
    classify_curve_regime,
    curve_payload_to_dataframe,
    generate_rates_desk_read,
    parse_treasury_yield_curve_xml,
    select_latest_curve_record,
    spreads_payload_to_dataframe,
)


SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:NEW_DATE>2026-05-07T00:00:00</d:NEW_DATE>
        <d:BC_3MONTH>5.20</d:BC_3MONTH>
        <d:BC_2YEAR>4.40</d:BC_2YEAR>
        <d:BC_5YEAR>4.15</d:BC_5YEAR>
        <d:BC_10YEAR>4.25</d:BC_10YEAR>
        <d:BC_30YEAR>4.55</d:BC_30YEAR>
      </m:properties>
    </content>
  </entry>
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:NEW_DATE>2026-05-08T00:00:00</d:NEW_DATE>
        <d:BC_3MONTH>5.10</d:BC_3MONTH>
        <d:BC_2YEAR>4.30</d:BC_2YEAR>
        <d:BC_5YEAR>4.10</d:BC_5YEAR>
        <d:BC_10YEAR>4.20</d:BC_10YEAR>
        <d:BC_30YEAR>4.50</d:BC_30YEAR>
      </m:properties>
    </content>
  </entry>
</feed>
"""


def test_parse_treasury_yield_curve_xml_extracts_records():
    records = parse_treasury_yield_curve_xml(SAMPLE_XML)

    assert len(records) == 2
    assert records[0]["date"] == "2026-05-07"
    assert records[0]["3M"] == 5.20
    assert records[0]["2Y"] == 4.40
    assert records[0]["10Y"] == 4.25


def test_select_latest_curve_record_uses_latest_valid_date():
    records = parse_treasury_yield_curve_xml(SAMPLE_XML)

    latest = select_latest_curve_record(records)

    assert latest["date"] == "2026-05-08"
    assert latest["10Y"] == 4.20


def test_calculate_curve_spreads_bps():
    curve = {"3M": 5.10, "2Y": 4.30, "5Y": 4.10, "10Y": 4.20, "30Y": 4.50}

    spreads = calculate_curve_spreads_bps(curve)

    assert spreads["3m10y_bps"] == -90.0
    assert spreads["2s10s_bps"] == -10.0
    assert spreads["5s30s_bps"] == 40.0


def test_classify_curve_regime():
    assert classify_curve_regime({"2s10s_bps": -40.0}) == "inverted"
    assert classify_curve_regime({"2s10s_bps": 10.0}) == "flat"
    assert classify_curve_regime({"2s10s_bps": 55.0}) == "steep"
    assert classify_curve_regime({"2s10s_bps": None}) == "insufficient data"


def test_build_sample_treasury_curve_payload_is_transparent():
    payload = build_sample_treasury_curve_payload(error="network down")

    assert payload["source"] == "U.S. Treasury"
    assert payload["data_mode"] == TREASURY_DATA_MODE
    assert payload["status"] == "sample_fallback"
    assert payload["as_of_date"] == "sample"
    assert "2s10s_bps" in payload["spreads_bps"]
    assert DISCLAIMER in payload["disclaimer"]
    assert payload["error"] == "network down"


def test_curve_payload_dataframe_helpers():
    payload = build_sample_treasury_curve_payload()

    curve_df = curve_payload_to_dataframe(payload)
    spreads_df = spreads_payload_to_dataframe(payload)

    assert list(curve_df.columns) == ["tenor", "yield_pct"]
    assert "10Y" in list(curve_df["tenor"])
    assert list(spreads_df.columns) == ["spread", "value_bps"]
    assert "2s10s" in list(spreads_df["spread"])


def test_generate_rates_desk_read_includes_core_signals():
    curve = {"10Y": 4.25}
    spreads = {"2s10s_bps": -35.0, "5s30s_bps": 20.0, "3m10y_bps": -100.0}

    desk_read = generate_rates_desk_read(curve, spreads, "inverted")

    assert any("inverted" in line for line in desk_read)
    assert any("2s10s" in line for line in desk_read)
    assert any("10Y Treasury yield" in line for line in desk_read)


def test_build_curve_table_preserves_tenor_order():
    table = build_curve_table({"1M": 5.0, "2Y": 4.2, "10Y": 4.5})

    assert table[0] == {"tenor": "1M", "yield_pct": 5.0}
    assert any(row["tenor"] == "10Y" and row["yield_pct"] == 4.5 for row in table)
