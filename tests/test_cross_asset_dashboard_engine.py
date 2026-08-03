import pandas as pd
import pytest

from engines.cross_asset_dashboard_engine import (
    build_default_cross_asset_inputs,
    build_risk_heatmap_table,
    build_sleeve_reconciliation_table,
    calculate_cross_asset_stress_table,
    calculate_cross_asset_summary,
    calculate_financing_risk_score,
    calculate_portfolio_risk_score,
    calculate_rates_risk_score,
    calculate_structured_products_risk_score,
    classify_risk_score,
    cross_asset_inputs_to_dict,
    cross_asset_summary_to_dict,
    generate_cross_asset_commentary,
    identify_dominant_risk_bucket,
)


def test_classify_risk_score_returns_expected_labels():
    assert classify_risk_score(10) == "Low"
    assert classify_risk_score(30) == "Moderate"
    assert classify_risk_score(60) == "High"
    assert classify_risk_score(90) == "Critical"


def test_heuristic_scores_remain_bounded():
    assert 0 <= calculate_rates_risk_score(25_000, 0.50) <= 100
    assert 0 <= calculate_financing_risk_score(250_000, 10_000_000) <= 100
    assert 0 <= calculate_structured_products_risk_score(0.40, 0.20) <= 100
    assert 0 <= calculate_portfolio_risk_score(0.02, 0.03, -0.10) <= 100


def test_identify_dominant_risk_bucket_returns_highest_score_key():
    bucket = identify_dominant_risk_bucket(
        {
            "Rates": 20,
            "Financing": 30,
            "Structured Products": 80,
        }
    )
    assert bucket == "Structured Products"


def test_cross_asset_summary_contains_nav_contract():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)

    assert 0 <= summary.composite_score <= 100
    assert summary.base_currency == "EUR"
    assert summary.portfolio_nav == pytest.approx(100_000_000)
    assert summary.allocated_sleeve_notional == pytest.approx(100_000_000)
    assert summary.unallocated_nav == pytest.approx(0.0)


def test_input_and_summary_dictionaries_are_reconstructable():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)

    input_dict = cross_asset_inputs_to_dict(inputs)
    summary_dict = cross_asset_summary_to_dict(summary)

    assert input_dict["portfolio_nav"] == 100_000_000
    assert summary_dict["base_currency"] == "EUR"
    assert "composite_score" in summary_dict


def test_risk_heatmap_is_explicitly_heuristic():
    summary = calculate_cross_asset_summary(
        build_default_cross_asset_inputs()
    )
    heatmap = build_risk_heatmap_table(summary)

    assert isinstance(heatmap, pd.DataFrame)
    assert len(heatmap) == 4
    assert "heuristic_score" in heatmap.columns
    assert "heuristic_label" in heatmap.columns


def test_sleeve_reconciliation_sums_to_nav():
    inputs = build_default_cross_asset_inputs()
    sleeve_df = build_sleeve_reconciliation_table(inputs)

    assert sleeve_df["notional_base"].sum() == pytest.approx(
        inputs.portfolio_nav
    )
    assert sleeve_df["share_of_nav"].sum() == pytest.approx(1.0)


def test_cross_asset_stress_table_has_amount_first_outputs():
    stress_df = calculate_cross_asset_stress_table(
        build_default_cross_asset_inputs()
    )

    assert isinstance(stress_df, pd.DataFrame)
    assert len(stress_df) == 5
    assert "economic_pnl_amount" in stress_df.columns
    assert "economic_pnl_pct_nav" in stress_df.columns
    assert "stressed_financing_liquidity_requirement_amount" in stress_df.columns
    assert "total_proxy_impact_pct" not in stress_df.columns


def test_cross_asset_commentary_separates_pnl_and_liquidity():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)
    stress_df = calculate_cross_asset_stress_table(inputs)
    commentary = generate_cross_asset_commentary(
        inputs,
        summary,
        stress_df,
    )

    assert commentary
    assert any("not included in economic P&L" in line for line in commentary)
    assert any("common portfolio NAV" in line for line in commentary)


def test_invalid_structured_probability_raises_error():
    with pytest.raises(ValueError):
        calculate_structured_products_risk_score(
            autocall_probability=1.20,
            barrier_breach_probability=0.20,
        )
