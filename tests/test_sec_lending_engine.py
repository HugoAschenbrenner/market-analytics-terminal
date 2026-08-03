import pandas as pd
import pytest

from engines.sec_lending_engine import (
    calculate_borrow_fee_amount,
    calculate_borrow_fee_comparison_table,
    calculate_collateral_required,
    calculate_net_lending_revenue,
    calculate_rebate_amount,
    calculate_reinvestment_income,
    calculate_securities_lending_trade,
    classify_specialness,
    generate_sec_lending_commentary,
    sec_lending_result_to_dict,
)


def test_collateral_required_formula():
    assert calculate_collateral_required(
        security_market_value=10_000_000,
        collateralization_rate=1.02,
    ) == 10_200_000


def test_borrow_fee_amount_increases_with_rate():
    low = calculate_borrow_fee_amount(
        security_market_value=10_000_000,
        borrow_fee_rate=0.01,
        loan_days=30,
        day_count_basis=360,
    )
    high = calculate_borrow_fee_amount(
        security_market_value=10_000_000,
        borrow_fee_rate=0.04,
        loan_days=30,
        day_count_basis=360,
    )

    assert high > low


def test_rebate_amount_increases_with_rate():
    low = calculate_rebate_amount(
        collateral_required=10_200_000,
        rebate_rate=0.005,
        loan_days=30,
        day_count_basis=360,
    )
    high = calculate_rebate_amount(
        collateral_required=10_200_000,
        rebate_rate=0.02,
        loan_days=30,
        day_count_basis=360,
    )

    assert high > low


def test_reinvestment_income_formula():
    income = calculate_reinvestment_income(
        collateral_required=10_200_000,
        reinvestment_yield=0.04,
        loan_days=30,
        day_count_basis=360,
    )

    assert income == pytest.approx(34_000.0)


def test_non_cash_trade_excludes_cash_path():
    result = calculate_securities_lending_trade(
        security_market_value=10_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.04,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.90,
        is_special=True,
    )

    assert result.collateral_required == 10_200_000
    assert result.borrow_fee_amount == pytest.approx(
        33_333.333333333336
    )
    assert result.rebate_amount == 0.0
    assert result.reinvestment_income == 0.0
    assert result.gross_lending_revenue == pytest.approx(
        result.borrow_fee_amount
    )
    assert result.net_lending_revenue == pytest.approx(
        result.borrow_fee_amount
    )


def test_cash_trade_excludes_non_cash_fee():
    result = calculate_securities_lending_trade(
        security_market_value=10_000_000,
        collateral_type="Cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0,
        rebate_rate=0.005,
        reinvestment_yield=0.04,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
        utilization_proxy=0.50,
    )

    assert result.borrow_fee_amount == 0.0
    assert result.reinvestment_income == pytest.approx(34_000.0)
    assert result.rebate_amount == pytest.approx(4_250.0)
    assert result.gross_lending_revenue == pytest.approx(29_750.0)
    assert result.net_lending_revenue == pytest.approx(29_750.0)


def test_audit_default_non_cash_and_cash_examples():
    non_cash = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
    )

    cash = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0,
        rebate_rate=0.005,
        reinvestment_yield=0.04,
        collateralization_rate=1.02,
        loan_days=30,
        day_count_basis=360,
    )

    assert non_cash.net_lending_revenue == pytest.approx(
        5_208.333333333333
    )
    assert cash.net_lending_revenue == pytest.approx(14_875.0)


def test_beneficial_owner_agent_split_and_costs():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        agent_fee_share=0.20,
        other_costs=100.0,
    )

    gross = 5_208.333333333333

    assert result.agent_fee_amount == pytest.approx(
        gross * 0.20
    )
    assert result.net_lending_revenue == pytest.approx(
        gross * 0.80 - 100.0
    )


def test_lending_agent_perspective_receives_fee_share_less_costs():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Lending agent",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
        agent_fee_share=0.20,
        other_costs=100.0,
    )

    assert result.net_lending_revenue == pytest.approx(
        result.agent_fee_amount - 100.0
    )


def test_non_cash_rejects_rebate_and_reinvestment():
    with pytest.raises(ValueError, match="Rebate rate must be zero"):
        calculate_securities_lending_trade(
            security_market_value=5_000_000,
            collateral_type="Non-cash",
            perspective="Beneficial owner",
            borrow_fee_rate=0.01,
            rebate_rate=0.005,
            reinvestment_yield=0.0,
            collateralization_rate=1.02,
            loan_days=30,
        )

    with pytest.raises(
        ValueError,
        match="Reinvestment yield must be zero",
    ):
        calculate_securities_lending_trade(
            security_market_value=5_000_000,
            collateral_type="Non-cash",
            perspective="Beneficial owner",
            borrow_fee_rate=0.01,
            rebate_rate=0.0,
            reinvestment_yield=0.04,
            collateralization_rate=1.02,
            loan_days=30,
        )


def test_cash_rejects_borrow_fee():
    with pytest.raises(
        ValueError,
        match="Borrow fee rate must be zero",
    ):
        calculate_securities_lending_trade(
            security_market_value=5_000_000,
            collateral_type="Cash",
            perspective="Beneficial owner",
            borrow_fee_rate=0.01,
            rebate_rate=0.005,
            reinvestment_yield=0.04,
            collateralization_rate=1.02,
            loan_days=30,
        )


def test_revenue_waterfall_rejects_hybrid_amounts():
    with pytest.raises(ValueError, match="cannot include rebate"):
        calculate_net_lending_revenue(
            collateral_type="Non-cash",
            perspective="Beneficial owner",
            borrow_fee_amount=5_000.0,
            rebate_amount=2_000.0,
        )

    with pytest.raises(
        ValueError,
        match="cannot include a securities loan fee",
    ):
        calculate_net_lending_revenue(
            collateral_type="Cash",
            perspective="Beneficial owner",
            borrow_fee_amount=5_000.0,
            rebate_amount=2_000.0,
            reinvestment_income=10_000.0,
        )


@pytest.mark.parametrize(
    ("borrow_fee_rate", "utilization", "manual_flag", "expected"),
    [
        (0.005, 0.30, True, "Special / hard-to-borrow"),
        (0.040, 0.40, False, "Special / hard-to-borrow"),
        (0.015, 0.50, False, "Warm / elevated borrow"),
        (0.0025, 0.30, False, "General collateral"),
    ],
)
def test_specialness_heuristic(
    borrow_fee_rate,
    utilization,
    manual_flag,
    expected,
):
    assert classify_specialness(
        borrow_fee_rate=borrow_fee_rate,
        utilization_proxy=utilization,
        is_special=manual_flag,
    ) == expected


def test_result_dictionary_exposes_convention():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0125,
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
    )

    result_dict = sec_lending_result_to_dict(result)

    assert isinstance(result_dict, dict)
    assert result_dict["collateral_type"] == "Non-cash"
    assert "revenue_convention" in result_dict
    assert "gross_lending_revenue" in result_dict


def test_non_cash_comparison_has_no_cash_economics():
    comparison = calculate_borrow_fee_comparison_table(
        security_market_value=5_000_000,
        collateral_type="Non-cash",
        perspective="Beneficial owner",
        rebate_rate=0.0,
        reinvestment_yield=0.0,
        collateralization_rate=1.02,
        loan_days=30,
    )

    assert isinstance(comparison, pd.DataFrame)
    assert len(comparison) == 3
    assert (comparison["rebate_amount"] == 0.0).all()
    assert (comparison["reinvestment_income"] == 0.0).all()
    assert (comparison["borrow_fee_amount"] > 0.0).all()


def test_cash_comparison_has_no_non_cash_fee():
    comparison = calculate_borrow_fee_comparison_table(
        security_market_value=5_000_000,
        collateral_type="Cash",
        perspective="Beneficial owner",
        rebate_rate=0.005,
        reinvestment_yield=0.04,
        collateralization_rate=1.02,
        loan_days=30,
    )

    assert len(comparison) == 3
    assert (comparison["borrow_fee_amount"] == 0.0).all()
    assert (comparison["reinvestment_income"] != 0.0).all()


def test_invalid_security_market_value_raises_error():
    with pytest.raises(ValueError):
        calculate_securities_lending_trade(
            security_market_value=-1,
            collateral_type="Non-cash",
            perspective="Beneficial owner",
            borrow_fee_rate=0.01,
            rebate_rate=0.0,
            reinvestment_yield=0.0,
            collateralization_rate=1.02,
            loan_days=30,
        )


def test_invalid_utilization_raises_error():
    with pytest.raises(ValueError):
        calculate_securities_lending_trade(
            security_market_value=5_000_000,
            collateral_type="Non-cash",
            perspective="Beneficial owner",
            borrow_fee_rate=0.01,
            rebate_rate=0.0,
            reinvestment_yield=0.0,
            collateralization_rate=1.02,
            loan_days=30,
            utilization_proxy=1.20,
        )


def test_commentary_is_path_specific():
    result = calculate_securities_lending_trade(
        security_market_value=5_000_000,
        collateral_type="Cash",
        perspective="Beneficial owner",
        borrow_fee_rate=0.0,
        rebate_rate=0.005,
        reinvestment_yield=0.04,
        collateralization_rate=1.02,
        loan_days=30,
    )

    commentary = generate_sec_lending_commentary(result)

    assert isinstance(commentary, list)
    assert commentary
    assert any("Cash reinvestment income" in line for line in commentary)
    assert not any(
        "fee income" in line.lower()
        and "non-cash" in line.lower()
        for line in commentary
    )
