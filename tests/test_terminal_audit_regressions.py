"""Independent financial identities and adversarial inputs from the September audit."""

from datetime import date
from dataclasses import replace
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

from engines import fixed_income_engine as fi
from engines import market_data_engine as md
from engines import portfolio_risk_engine as pr
from engines import structured_products_valuation_engine as sv
from engines.options_pricing_engine import build_black_scholes_snapshot
from engines.rates_market_data_engine import build_sample_treasury_curve_payload
from engines.repo_engine import calculate_contractual_variation_margin
from reports.excel_exporter import generate_portfolio_risk_report


def test_drawdown_includes_initial_capital_and_recovery():
    returns = pd.Series([-0.20, 0.10, 0.20, -0.25])
    # Wealth: 1 -> .8 -> .88 -> 1.056 -> .792.
    assert pr.calculate_drawdown_series(returns).tolist() == pytest.approx(
        [-0.20, -0.12, 0.0, -0.25]
    )


def test_first_period_total_loss_is_a_full_drawdown():
    assert pr.calculate_drawdown_series(pd.Series([-1.0, 0.0])).tolist() == [-1.0, -1.0]


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
def test_invalid_prices_are_rejected(bad):
    frame = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=3),
                          "A": [100, bad, 110], "B": [100, 102, 104]})
    with pytest.raises(ValueError):
        pr.calculate_asset_returns(frame)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), -0.1])
def test_long_only_weights_reject_nonfinite_and_negative_values(bad):
    with pytest.raises(ValueError):
        pr.normalize_weights({"A": bad, "B": 1.0})


def test_zero_volatility_risk_contribution_is_defined_without_division():
    frame = pd.DataFrame({"A": [0.0] * 5, "B": [0.0] * 5})
    result = pr.calculate_risk_contribution(frame, {"A": 0.5, "B": 0.5})
    assert (result["contribution_to_volatility"] == 0).all()
    assert result["pct_contribution_to_volatility"].isna().all()


def test_cash_has_no_price_shock_in_all_demo_stresses():
    frame = pr.calculate_stress_scenario_table({"CASH": 1.0})
    assert (frame["estimated_portfolio_return"] == 0.0).all()


def test_cvar_selects_raw_return_tail_before_flooring_losses():
    # At 80% confidence the worst two returns are -1% and +2%.
    # The mean tail return is positive, so the positive-loss metric is zero.
    returns = pd.Series([-0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10])
    assert pr.calculate_historical_cvar(returns, confidence_level=0.8) == 0.0


def test_nondefault_confidence_is_not_reported_as_95_percent():
    returns = pd.DataFrame({"A": [-0.05, -0.03, 0.01, 0.04, 0.02], "B": [0.01, 0.02, -0.01, 0.03, 0.01]})
    weights = {"A": 0.5, "B": 0.5}
    summary = pr.summarize_portfolio_risk(returns, weights, confidence_level=0.8)
    report = pr.portfolio_risk_summary_to_dict(summary)
    assert report["confidence_level"] == 0.8
    assert "historical_var_95" not in report
    commentary = pr.generate_portfolio_risk_commentary(summary, pr.calculate_risk_contribution(returns, weights), pr.calculate_stress_scenario_table(weights))
    assert "Historical 80% VaR" in " ".join(commentary)


def test_end_of_month_schedule_does_not_drift_after_february():
    schedule = fi.build_contractual_coupon_schedule("2024-08-31", "2026-08-31", 2)
    assert schedule.tolist() == list(pd.to_datetime([
        "2025-02-28", "2025-08-31", "2026-02-28", "2026-08-31"
    ]))


def test_regular_act_act_bond_prices_at_par_on_coupon_date():
    dates, coupons, exponents = fi.build_remaining_contractual_cashflows(
        0.06, 2, "2024-08-31", "2026-08-31", "2025-02-28", "ACT/ACT"
    )
    assert coupons.tolist() == [3.0, 3.0, 103.0]
    assert exponents.tolist() == pytest.approx([1, 2, 3])
    assert fi.calculate_dirty_price_from_ytm(coupons, exponents, 0.06, 2) == pytest.approx(100.0)


def test_short_first_coupon_accrual_uses_the_full_reference_period():
    accrued = fi.calculate_contractual_accrued_interest_per_100(
        0.06, 2, "2025-04-30", "2026-08-31", "2025-06-30", "ACT/ACT"
    )
    assert accrued == pytest.approx(3 * 61 / 184)
    _, coupons, _ = fi.build_remaining_contractual_cashflows(
        0.06, 2, "2025-04-30", "2026-08-31", "2025-06-30", "ACT/ACT"
    )
    assert coupons[0] == pytest.approx(3 * 123 / 184)


def test_us_thirty_360_handles_february_end():
    assert fi.calculate_day_count_year_fraction("2025-02-28", "2025-08-31", "30/360") == 0.5
    assert fi.calculate_day_count_year_fraction("2024-02-29", "2025-02-28", "30/360") == 1.0


def test_missing_bond_columns_raise_actionable_validation_error():
    with pytest.raises(ValueError, match="Missing"):
        fi.calculate_bond_risk_metrics(pd.DataFrame({"bond_id": ["X"]}))


@pytest.mark.parametrize("option_type,spot,strike,rate,dividend", [
    ("Put", 50, 100, 0.10, 0.0),
    ("Call", 100, 50, 0.0, 0.10),
])
def test_european_option_value_reconciles_to_intrinsic_plus_time_value(
    option_type, spot, strike, rate, dividend
):
    outputs = build_black_scholes_snapshot(option_type, spot, strike, 1.0, rate, 0.10, dividend)["outputs"]
    assert outputs["time_value"] < 0
    assert outputs["intrinsic_value"] + outputs["time_value"] == pytest.approx(outputs["price"], abs=2e-6)


@pytest.mark.parametrize("dirty", [80.0, 120.0])
def test_repo_securities_transfer_closes_the_haircut_adjusted_exposure(dirty):
    result = calculate_contractual_variation_margin(
        cash_amount=90, repo_rate=0, start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1), margin_date=date(2026, 1, 1), day_count_basis=360,
        current_dirty_collateral_value=dirty, contractual_haircut=0.10,
        transaction_direction="Cash lender / reverse repo", rounding_method="None",
    )
    signed_collateral = np.sign(result.contractual_margin_transfer) * result.collateral_transfer_amount
    assert (dirty + signed_collateral) * 0.90 == pytest.approx(90.0)


def test_single_quote_does_not_invent_a_zero_return():
    quote = md.build_quote_from_history("SPY", pd.DataFrame({"Close": [100]}))
    assert quote["change_pct"] is None


def test_quote_records_observation_date_separately_from_fetch_time():
    history = pd.DataFrame({"Close": [105, 100]}, index=pd.to_datetime(["2020-01-03", "2020-01-02"]))
    quote = md.build_quote_from_history("SPY", history)
    assert quote["price"] == 105
    assert quote["change_pct"] == 5
    assert quote["observation_date"] == "2020-01-03"
    assert quote["timestamp_utc"].endswith("Z")


@pytest.mark.parametrize("bad", [np.inf, -np.inf, 0.0, -10.0])
def test_bad_latest_quote_is_not_replaced_with_a_good_old_quote(bad):
    quote = md.build_quote_from_history("SPY", pd.DataFrame({"Close": [100, bad]}))
    assert quote["price"] is None
    assert quote["status"] != "ok"


def test_sample_curve_does_not_claim_to_be_official_data():
    payload = build_sample_treasury_curve_payload()
    assert "sample" in payload["source"].lower()
    assert "synthetic" in payload["data_mode"].lower()


def test_valuation_rejects_protection_above_initial_capital():
    with pytest.raises(ValueError):
        sv.validate_valuation_inputs(protection_barrier=1.1, coupon_barrier=1.2, autocall_barrier=1.3)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.1])
def test_valuation_rejects_invalid_performance_ratios(bad):
    inputs = sv.validate_valuation_inputs(simulations=1, maturity_years=1)
    with pytest.raises(ValueError):
        sv.evaluate_autocallable_cashflows(np.array([[[bad]]]), inputs)


def test_valuation_sensitivities_respect_basket_correlation_boundary():
    inputs = sv.validate_valuation_inputs(initial_spots=[100] * 3, volatilities=[0.2] * 3,
                                         correlation=-0.4, simulations=8)
    table = sv.build_valuation_sensitivity_table(inputs)
    assert len(table) == 9
    assert (table["correlation"] > -0.5).all()
    assert np.isfinite(table["fair_value_pct_notional"]).all()


@pytest.mark.parametrize("axis,value", [("Maturity", 0.73), ("Volatility", 0.237), ("Rate", -0.035)])
def test_interactive_bsm_curve_contains_the_exact_input(axis, value):
    from engines.options_pricing_engine import build_bsm_interactive_explorer_payload
    inputs = dict(option_type="Put", spot=90, strike=105, maturity_years=0.73,
                  risk_free_rate=-0.035, volatility=0.237, dividend_yield=0.01)
    payload = build_bsm_interactive_explorer_payload(**inputs)
    curve = payload["curves"][axis]
    row = curve.loc[np.isclose(curve["axis_value"], value)].iloc[0]
    assert row["price"] == pytest.approx(payload["snapshot"]["outputs"]["price"], abs=1e-6)


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_public_calculation_entrypoints_reject_nonfinite_values(bad):
    from engines.cross_asset_dashboard_engine import build_default_cross_asset_inputs, calculate_cross_asset_summary
    from engines.options_payoff_engine import build_strategy_legs
    from engines.structured_products_engine import AutocallableTerms, calculate_autocallable_payoff
    from engines.repo_engine import calculate_repo_trade
    calls = [
        lambda: build_black_scholes_snapshot("Call", bad, 100, 1, 0.03, 0.2),
        lambda: build_strategy_legs("Long Call", 100, 100, bad),
        lambda: calculate_cross_asset_summary(replace(build_default_cross_asset_inputs(), portfolio_nav=bad)),
        lambda: sv.validate_valuation_inputs(volatilities=[bad]),
        lambda: calculate_repo_trade(100, bad, 0.03, date(2026, 1, 1), date(2026, 2, 1)),
        lambda: calculate_autocallable_payoff(AutocallableTerms("Phoenix", 1000, 0.02, 0, -0.3, -0.4, True), [bad]),
    ]
    for call in calls:
        with pytest.raises(ValueError):
            call()


def test_market_cache_preserves_failures_and_refresh_really_fetches(monkeypatch):
    import sys
    from types import SimpleNamespace
    calls = []

    class Ticker:
        fast_info = {"currency": "USD"}

        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            calls.append(kwargs)
            assert kwargs["auto_adjust"] is False
            if self.symbol == "BAD":
                return pd.DataFrame()
            return pd.DataFrame({"Close": [100, 105]}, index=pd.date_range("2026-01-01", periods=2))

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=Ticker))
    monkeypatch.setattr(md, "_quote_cache", {})
    first = md.build_market_snapshot(["GOOD", "BAD"])
    assert first["status"] == "partial"
    first["quotes"]["GOOD"]["price"] = 999
    cached = md.build_market_snapshot(["GOOD", "BAD"])
    assert cached["status"] == "partial"
    assert cached["cache_status"] == "cached"
    assert cached["quotes"]["GOOD"]["price"] == 105
    assert len(calls) == 2
    md.build_market_snapshot(["GOOD", "BAD"], force_refresh=True)
    assert len(calls) == 4


def test_excel_treats_uploaded_labels_as_text():
    label = '=HYPERLINK("https://example.com","uploaded label")'
    data = pd.DataFrame({"asset": [label], "value": [1.0]})
    output = generate_portfolio_risk_report(
        summary={"number_of_assets": 1}, weights_df=data,
        portfolio_returns_df=data, drawdown_df=data,
        correlation_matrix=pd.DataFrame([[1.0]], columns=[label], index=[label]),
        risk_contribution_df=data, stress_df=data,
    )
    workbook = load_workbook(BytesIO(output), data_only=False)
    cells = [cell for sheet in workbook for row in sheet for cell in row if cell.value == label]
    assert cells
    assert all(cell.data_type == "s" for cell in cells)


def test_r_companion_matches_python_drawdown_and_risk_metrics(tmp_path):
    import shutil
    import subprocess
    from pathlib import Path
    rscript = shutil.which("Rscript")
    if rscript is None:
        pytest.skip("Rscript is not installed")
    (tmp_path / "data").mkdir()
    shutil.copy("data/portfolio_returns_sample.csv", tmp_path / "data")
    subprocess.run([rscript, str(Path("r_analytics/portfolio_performance_report.R").resolve())],
                   cwd=tmp_path, check=True, capture_output=True, timeout=30)
    source = pd.read_csv(tmp_path / "data/portfolio_returns_sample.csv")
    returns = source.drop(columns="date").mean(axis=1)
    drawdowns = pd.read_csv(tmp_path / "r_analytics/outputs/drawdown_series.csv")
    assert drawdowns["drawdown"].to_numpy() == pytest.approx(pr.calculate_drawdown_series(returns).to_numpy(), abs=1e-12)
    summary = pd.read_csv(tmp_path / "r_analytics/outputs/performance_summary.csv").set_index("metric")["value"]
    assert summary["historical_var_95"] == pytest.approx(pr.calculate_historical_var(returns))
    assert summary["historical_cvar_95"] == pytest.approx(pr.calculate_historical_cvar(returns))
    assert summary["annualized_volatility"] == pytest.approx(pr.calculate_annualized_volatility(returns))
