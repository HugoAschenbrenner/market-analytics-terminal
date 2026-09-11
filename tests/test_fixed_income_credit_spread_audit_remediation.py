from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from engines.fixed_income_engine import (
    apply_fx_conversion,
    build_credit_spread_exposure_table,
    calculate_bond_risk_metrics,
    calculate_scenario_pnl,
    load_bond_data,
)


VALUATION_DATE = date(2026, 8, 3)


def _sample_risk() -> pd.DataFrame:
    bonds = load_bond_data(
        "data/sample_bonds.csv"
    )
    local = calculate_bond_risk_metrics(
        bonds,
        valuation_date=VALUATION_DATE,
        pricing_mode="Solve YTM from clean price",
        when_issued_policy="Flag",
    )
    return apply_fx_conversion(
        local,
        base_currency="EUR",
        fx_rates={
            "EUR": 1.0,
            "USD": 0.92,
        },
    )


def test_sovereigns_are_excluded_from_credit_spread_stress():
    risk = _sample_risk()
    sovereign = risk.loc[
        risk["sector"]
        .astype(str)
        .str.upper()
        .eq("SOVEREIGN")
    ]

    assert not sovereign.empty
    assert (
        ~sovereign[
            "credit_spread_eligible"
        ]
    ).all()
    assert (
        sovereign["cs01_base"] == 0.0
    ).all()
    assert (
        sovereign["credit_risk_class"]
        == "Sovereign / rates-only"
    ).all()


def test_credit_bonds_receive_positive_repriced_cs01():
    risk = _sample_risk()
    credit = risk.loc[
        risk["credit_spread_eligible"]
    ]

    assert not credit.empty
    assert (credit["cs01"] > 0).all()
    assert (credit["cs01_base"] > 0).all()
    assert (credit["spread_duration"] > 0).all()
    assert credit[
        "spread_risk_method"
    ].str.contains(
        "contractual-cashflow repricing"
    ).all()


def test_credit_scenario_reconciles_to_credit_only_cs01():
    risk = _sample_risk()
    scenario_df = calculate_scenario_pnl(
        risk
    )

    credit_row = scenario_df.loc[
        scenario_df["scenario_name"]
        == "Credit spread +50 bps"
    ].iloc[0]

    eligible_cs01 = risk.loc[
        risk["credit_spread_eligible"],
        "cs01_base",
    ].sum()

    expected_loss = -50.0 * eligible_cs01

    assert credit_row[
        "estimated_pnl"
    ] == pytest.approx(expected_loss)
    assert credit_row[
        "credit_cs01_base"
    ] == pytest.approx(eligible_cs01)
    assert credit_row[
        "sovereign_excluded_count"
    ] == int(
        (~risk["credit_spread_eligible"]).sum()
    )


def test_sovereign_dv01_does_not_enter_credit_loss():
    risk = _sample_risk()
    credit_row = calculate_scenario_pnl(
        risk
    ).query(
        "scenario_name == 'Credit spread +50 bps'"
    ).iloc[0]

    old_invalid_loss = (
        -50.0 * risk["dv01_base"].sum()
    )

    assert credit_row[
        "estimated_pnl"
    ] != pytest.approx(old_invalid_loss)
    assert abs(
        credit_row["estimated_pnl"]
    ) < abs(old_invalid_loss)


def test_curve_specific_spread_shocks_are_respected():
    risk = _sample_risk()
    eligible = risk.loc[
        risk["credit_spread_eligible"]
    ]
    curve_keys = sorted(
        eligible["credit_curve_key"].unique()
    )
    shocks = {
        key: float(
            25 + 5 * index
        )
        for index, key in enumerate(
            curve_keys
        )
    }

    scenario_df = calculate_scenario_pnl(
        risk,
        credit_spread_shocks_bps=shocks,
    )
    credit_row = scenario_df.loc[
        scenario_df["scenario_name"]
        == "Credit spread curve stress"
    ].iloc[0]

    expected = 0.0
    for _, row in eligible.iterrows():
        expected += (
            -float(row["cs01_base"])
            * shocks[
                str(row["credit_curve_key"])
            ]
        )

    assert credit_row[
        "estimated_pnl"
    ] == pytest.approx(expected)
    assert credit_row[
        "credit_curve_count"
    ] == len(curve_keys)


def test_missing_curve_shock_is_rejected():
    risk = _sample_risk()
    curve_keys = sorted(
        risk.loc[
            risk["credit_spread_eligible"],
            "credit_curve_key",
        ].unique()
    )

    incomplete = {
        curve_keys[0]: 50.0
    }

    with pytest.raises(
        ValueError,
        match="Missing credit spread shock",
    ):
        calculate_scenario_pnl(
            risk,
            credit_spread_shocks_bps=(
                incomplete
            ),
        )


def test_credit_exposure_table_is_auditable():
    risk = _sample_risk()
    exposure = (
        build_credit_spread_exposure_table(
            risk
        )
    )

    assert {
        "credit_spread_eligible",
        "credit_curve_key",
        "credit_risk_class",
        "full_market_value_base",
        "cs01_base",
        "spread_duration",
        "pct_total_credit_cs01",
    }.issubset(exposure.columns)

    eligible = exposure.loc[
        exposure["credit_spread_eligible"]
    ]

    assert eligible[
        "pct_total_credit_cs01"
    ].sum() == pytest.approx(1.0)


def test_explicit_credit_eligibility_override_is_respected():
    bonds = load_bond_data(
        "data/sample_bonds.csv"
    ).iloc[[0]].copy()
    bonds["credit_spread_eligible"] = True
    bonds["credit_curve_key"] = (
        "EUR|EXPLICIT_TEST|AA"
    )

    local = calculate_bond_risk_metrics(
        bonds,
        valuation_date=VALUATION_DATE,
        pricing_mode="Solve YTM from clean price",
    )

    row = local.iloc[0]

    assert row["credit_spread_eligible"]
    assert row[
        "credit_mapping_source"
    ] == "Explicit input"
    assert row[
        "credit_curve_key"
    ] == "EUR|EXPLICIT_TEST|AA"
    assert row["cs01"] > 0


def test_ui_and_excel_expose_credit_spread_contract():
    report = Path(
        "reports/excel_exporter.py"
    ).read_text()

    assert "Credit_Spread_Exposure" in report
    assert "sovereign and rates-only" in report
    assert "parallel-spread proxy" in report
