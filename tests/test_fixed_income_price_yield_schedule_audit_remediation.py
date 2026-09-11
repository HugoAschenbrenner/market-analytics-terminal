from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.fixed_income_engine import (
    build_contractual_coupon_schedule,
    build_remaining_contractual_cashflows,
    calculate_bond_risk_metrics,
    calculate_contractual_accrued_interest_per_100,
    calculate_dirty_price_from_ytm,
    solve_ytm_from_dirty_price,
    validate_bond_contract_dates,
)


VALUATION_DATE = date(2026, 8, 3)


def _bond(
    clean_price: float = 101.25,
    supplied_ytm: float = 0.09,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bond_id": ["TEST-2030"],
            "issuer": ["Test Issuer"],
            "currency": ["EUR"],
            "coupon_rate": [0.04],
            "maturity_date": ["2030-06-30"],
            "issue_date": ["2024-06-30"],
            "frequency": [2],
            "clean_price": [clean_price],
            "yield_to_maturity": [supplied_ytm],
            "notional": [1_000_000.0],
            "rating": ["A"],
            "sector": ["Corporate"],
            "spread_bps": [100.0],
            "curve_bucket": ["2-5Y"],
        }
    )


def test_schedule_is_anchored_to_contractual_maturity():
    schedule = build_contractual_coupon_schedule(
        issue_date="2024-06-30",
        maturity_date="2030-06-30",
        frequency=2,
    )

    assert schedule[-1] == pd.Timestamp("2030-06-30")
    assert all(
        current < following
        for current, following in zip(
            schedule[:-1],
            schedule[1:],
        )
    )


def test_remaining_cashflows_end_exactly_at_maturity():
    dates, cashflows, exponents = (
        build_remaining_contractual_cashflows(
            coupon_rate=0.04,
            frequency=2,
            issue_date="2024-06-30",
            maturity_date="2030-06-30",
            valuation_date=VALUATION_DATE,
            day_count_convention="ACT/ACT",
        )
    )

    assert dates[-1] == pd.Timestamp("2030-06-30")
    assert cashflows[-1] > 100.0
    assert np.all(np.diff(exponents) > 0)


def test_solved_ytm_reprices_dirty_quote():
    row = calculate_bond_risk_metrics(
        _bond(),
        valuation_date=VALUATION_DATE,
        pricing_mode="Solve YTM from clean price",
    ).iloc[0]

    assert row["price_reconciled"]
    assert row["pricing_status"] == "Reconciled"
    assert row["dirty_price_reconciliation_error"] == pytest.approx(
        0.0,
        abs=1e-9,
    )
    assert row["model_dirty_price"] == pytest.approx(
        row["dirty_price"],
        abs=1e-9,
    )


def test_supplied_ytm_audit_exposes_quote_mismatch():
    row = calculate_bond_risk_metrics(
        _bond(
            clean_price=101.25,
            supplied_ytm=0.20,
        ),
        valuation_date=VALUATION_DATE,
        pricing_mode="Audit supplied YTM against quote",
        reconciliation_tolerance_per_100=0.01,
    ).iloc[0]

    assert row["pricing_yield_used"] == pytest.approx(0.20)
    assert not row["price_reconciled"]
    assert row["pricing_status"] == "Quote/YTM mismatch"
    assert abs(row["dirty_price_reconciliation_error"]) > 0.01


def test_direct_yield_solver_matches_known_price():
    dates, cashflows, exponents = (
        build_remaining_contractual_cashflows(
            coupon_rate=0.04,
            frequency=2,
            issue_date="2024-06-30",
            maturity_date="2030-06-30",
            valuation_date=VALUATION_DATE,
            day_count_convention="ACT/ACT",
        )
    )

    known_yield = 0.0525
    target = calculate_dirty_price_from_ytm(
        cashflows,
        exponents,
        known_yield,
        2,
    )
    solved = solve_ytm_from_dirty_price(
        target,
        cashflows,
        exponents,
        2,
    )

    assert dates[-1] == pd.Timestamp("2030-06-30")
    assert solved == pytest.approx(
        known_yield,
        abs=1e-10,
    )


def test_contractual_accrual_is_zero_on_coupon_date():
    accrued = calculate_contractual_accrued_interest_per_100(
        coupon_rate=0.04,
        frequency=2,
        issue_date="2024-06-30",
        maturity_date="2030-06-30",
        valuation_date="2026-06-30",
        day_count_convention="ACT/ACT",
    )

    assert accrued == pytest.approx(0.0)


def test_invalid_contract_dates_are_rejected():
    with pytest.raises(
        ValueError,
        match="issue date must be strictly before maturity",
    ):
        build_contractual_coupon_schedule(
            issue_date="2030-06-30",
            maturity_date="2030-06-30",
            frequency=2,
        )

    with pytest.raises(
        ValueError,
        match="Valuation date must be strictly before maturity",
    ):
        validate_bond_contract_dates(
            issue_date="2024-06-30",
            maturity_date="2030-06-30",
            valuation_date="2030-06-30",
        )


def test_when_issued_positions_are_flagged_or_rejected_explicitly():
    flagged = validate_bond_contract_dates(
        issue_date="2026-09-18",
        maturity_date="2036-09-18",
        valuation_date="2026-08-03",
        when_issued_policy="Flag",
    )

    assert flagged == "When-issued (flagged)"

    with pytest.raises(
        ValueError,
        match="When-issued position rejected",
    ):
        validate_bond_contract_dates(
            issue_date="2026-09-18",
            maturity_date="2036-09-18",
            valuation_date="2026-08-03",
            when_issued_policy="Reject",
        )


def test_sample_portfolio_exposes_schedule_and_reconciliation_fields():
    bonds = pd.read_csv("data/sample_bonds.csv")
    risk = calculate_bond_risk_metrics(
        bonds,
        valuation_date=VALUATION_DATE,
        pricing_mode="Solve YTM from clean price",
        when_issued_policy="Flag",
    )

    required = {
        "pricing_mode",
        "day_count_convention",
        "provided_yield_to_maturity",
        "pricing_yield_used",
        "previous_coupon_date",
        "next_coupon_date",
        "final_cashflow_date",
        "model_dirty_price",
        "dirty_price_reconciliation_error",
        "price_reconciled",
        "schedule_status",
    }

    assert required.issubset(risk.columns)
    assert risk["price_reconciled"].all()
    assert (
        risk["final_cashflow_date"]
        == pd.to_datetime(
            risk["maturity_date"]
        ).dt.date.astype(str)
    ).all()


def test_ui_and_excel_expose_price_yield_schedule_contract():
    report = Path(
        "reports/excel_exporter.py"
    ).read_text()


    assert "previous_coupon_date" in report
    assert "pricing_mode" in report
    assert "price_reconciled" in report
    assert "same contractual cashflow schedule" in report
