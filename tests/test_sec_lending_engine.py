import pandas as pd
import pytest

from engines.sec_lending_engine import (
    calculate_borrow_fee_amount,
    calculate_borrow_fee_comparison_table,
    calculate_collateral_required,
    calculate_net_lending_revenue,
    calculate_rebate_amount,
    calculate_securities_lending_trade,
    classify_specialness,
    generate_sec_lending_commentary,
    sec_lending_result_to_dict,
)


def test_collateral_required_formula():
    collateral = calculate_collateral_required(
        security_market_value=10_000_000,
        collateralization_rate=1.02,
    )

    assert collateral == 10_200_000


def test_borrow_fee_amount_increases_with_borrow_fee_rate():
    low_fee = calculate_borrow_fee_amount(
        security_market_value=10_000_000,
        borrow_fee_rate=0.01,
        loan_days=30,
        day_count_basis=360,
    )
    high_fee = calculate_borrow_fee_amount(
        security_market_value=10_000_000,
        borrow_fee_rate=0.04,
        loan_days=30,
        day_count_basis=360,
    )

    assert high_fee > low_fee


def test_rebate_amount_increases_with_rebate_rate():
    low_rebate = calculate_rebate_amount(
        collateral_required=10_200_000,
        rebate_rate=0.005,
        loan_days=30,
        day_count_basis=360,
    )
    high_rebate = calculate_rebate_amount(
        collateral_required=10_200_000,
        rebate_rate=0.02,
        loan_days=30,
        day_count_basis=360,
    )

    assert high_rebate > low_rebate


def test_higher_rebate_reduces_net_lending_revenue():
    borrow_fee = 30_000

    low_rebate_net = calculate_net_lending_revenue(
        borrow_fee_amount=borrow_fee,
        rebate_amount=5_000,
    )
    high_rebate_net = calculate_net_lending_revenue(
        borrow_fee_amount=borrow_fee,
        rebate_amount=20_000,
    )

    assert high_rebate_net < low_rebate_net


def test_securities_lending_trade_outputs_consistent_values():
    result = calculate_securities_lending_trade(
        security_market_value=10_000_000,
        borrow_fee_rate=0.04,
        rebate_rate=0.005,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.90,
        is_special=True,
    )

    assert result.collateral_required == 10_200_000
    assert abs(result.borrow_fee_amount - 33_333.333333333336) < 1e-6
    assert abs(result.rebate_amount - 4_250.0) < 1e-6
    assert abs(result.net_lending_revenue - 29_083.333333333336) < 1e-6
    assert result.specialness_label == "Special / hard-to-borrow"


def test_special_flag_produces_specialness_label():
    label = classify_specialness(
        borrow_fee_rate=0.005,
        utilization_proxy=0.30,
        is_special=True,
    )

    assert label == "Special / hard-to-borrow"


def test_high_borrow_fee_produces_specialness_label():
    label = classify_specialness(
        borrow_fee_rate=0.04,
        utilization_proxy=0.40,
        is_special=False,
    )

    assert label == "Special / hard-to-borrow"


def test_warm_borrow_classification():
    label = classify_specialness(
        borrow_fee_rate=0.015,
        utilization_proxy=0.50,
        is_special=False,
    )

    assert label == "Warm / elevated borrow"


def test_general_collateral_classification():
    label = classify_specialness(
        borrow_fee_rate=0.0025,
        utilization_proxy=0.30,
        is_special=False,
    )

    assert label == "General collateral"


def test_sec_lending_result_to_dict_returns_dictionary():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        borrow_fee_rate=0.0125,
        rebate_rate=0.005,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.65,
        is_special=False,
    )

    result_dict = sec_lending_result_to_dict(result)

    assert isinstance(result_dict, dict)
    assert "collateral_required" in result_dict
    assert "net_lending_revenue" in result_dict


def test_borrow_fee_comparison_table_returns_dataframe():
    comparison_df = calculate_borrow_fee_comparison_table(
        security_market_value=5_000_000,
        rebate_rate=0.005,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
    )

    assert isinstance(comparison_df, pd.DataFrame)
    assert len(comparison_df) == 3
    assert "net_lending_revenue" in comparison_df.columns
    assert "specialness_label" in comparison_df.columns


def test_invalid_security_market_value_raises_error():
    with pytest.raises(ValueError):
        calculate_securities_lending_trade(
            security_market_value=-1,
            borrow_fee_rate=0.01,
            rebate_rate=0.005,
            collateralization_rate=1.02,
            loan_days=30,
        )


def test_invalid_utilization_raises_error():
    with pytest.raises(ValueError):
        calculate_securities_lending_trade(
            security_market_value=5_000_000,
            borrow_fee_rate=0.01,
            rebate_rate=0.005,
            collateralization_rate=1.02,
            loan_days=30,
            utilization_proxy=1.20,
        )


def test_sec_lending_commentary_returns_non_empty_list():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        borrow_fee_rate=0.04,
        rebate_rate=0.005,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.90,
        is_special=True,
    )

    commentary = generate_sec_lending_commentary(result)

    assert isinstance(commentary, list)
    assert len(commentary) > 0
    assert all(isinstance(comment, str) for comment in commentary)
