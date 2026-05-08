import pandas as pd
import pytest

from engines.cross_asset_dashboard_engine import (
    build_default_cross_asset_inputs,
    build_risk_heatmap_table,
    calculate_cross_asset_stress_table,
    calculate_cross_asset_summary,
    calculate_financing_risk_score,
    calculate_portfolio_risk_score,
    calculate_rates_risk_score,
    calculate_structured_products_risk_score,
    classify_risk_score,
    cross_asset_summary_to_dict,
    generate_cross_asset_commentary,
    identify_dominant_risk_bucket,
)


def test_classify_risk_score_returns_expected_labels():
    assert classify_risk_score(10) == "Low"
    assert classify_risk_score(30) == "Moderate"
    assert classify_risk_score(60) == "High"
    assert classify_risk_score(90) == "Critical"


def test_rates_risk_score_between_zero_and_100():
    score = calculate_rates_risk_score(total_dv01=25_000, long_end_dv01_share=0.50)

    assert 0 <= score <= 100


def test_financing_risk_score_between_zero_and_100():
    score = calculate_financing_risk_score(
        repo_margin_deficit=250_000,
        collateral_market_value=10_000_000,
    )

    assert 0 <= score <= 100


def test_structured_products_risk_score_between_zero_and_100():
    score = calculate_structured_products_risk_score(
        autocall_probability=0.40,
        barrier_breach_probability=0.20,
    )

    assert 0 <= score <= 100


def test_portfolio_risk_score_between_zero_and_100():
    score = calculate_portfolio_risk_score(
        portfolio_var_95=0.02,
        portfolio_cvar_95=0.03,
        max_drawdown=-0.10,
    )

    assert 0 <= score <= 100


def test_identify_dominant_risk_bucket_returns_highest_score_key():
    bucket = identify_dominant_risk_bucket(
        {
            "Rates": 20,
            "Financing": 30,
            "Structured Products": 80,
        }
    )

    assert bucket == "Structured Products"


def test_cross_asset_summary_returns_valid_summary():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)

    assert 0 <= summary.composite_score <= 100
    assert summary.composite_risk_label in {"Low", "Moderate", "High", "Critical"}


def test_cross_asset_summary_to_dict_returns_dictionary():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)
    summary_dict = cross_asset_summary_to_dict(summary)

    assert isinstance(summary_dict, dict)
    assert "composite_score" in summary_dict


def test_risk_heatmap_table_returns_dataframe():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)
    heatmap = build_risk_heatmap_table(summary)

    assert isinstance(heatmap, pd.DataFrame)
    assert len(heatmap) == 4
    assert "risk_bucket" in heatmap.columns
    assert "risk_score" in heatmap.columns


def test_cross_asset_stress_table_returns_dataframe():
    inputs = build_default_cross_asset_inputs()
    stress_df = calculate_cross_asset_stress_table(inputs)

    assert isinstance(stress_df, pd.DataFrame)
    assert len(stress_df) == 5
    assert "total_proxy_impact_pct" in stress_df.columns


def test_cross_asset_commentary_returns_non_empty_list():
    inputs = build_default_cross_asset_inputs()
    summary = calculate_cross_asset_summary(inputs)
    stress_df = calculate_cross_asset_stress_table(inputs)

    commentary = generate_cross_asset_commentary(inputs, summary, stress_df)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)


def test_invalid_structured_probability_raises_error():
    with pytest.raises(ValueError):
        calculate_structured_products_risk_score(
            autocall_probability=1.20,
            barrier_breach_probability=0.20,
        )
