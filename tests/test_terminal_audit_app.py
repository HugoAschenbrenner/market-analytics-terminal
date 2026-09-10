"""Execute Streamlit workflows, including interactions missed by source-text tests."""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page", ["home", "fixed-income-risk", "repo-sec-lending",
                                  "structured-products", "portfolio-risk", "cross-asset-dashboard"])
def test_default_app_pages_render_without_errors(page):
    app = AppTest.from_file(str(Path("app.py").resolve()), default_timeout=40)
    app.query_params["page"] = page
    app.run()
    assert not app.exception
    assert not app.error


def test_monthly_page_risk_contributions_reconcile_to_monthly_summary(monkeypatch):
    from app_pages import portfolio_risk
    prices = pd.DataFrame({"date": pd.date_range("2024-01-31", periods=24, freq="ME"),
                           "A": 100 * np.cumprod(1 + np.linspace(-0.03, 0.04, 24)),
                           "B": 100 * np.cumprod(1 + np.linspace(0.03, -0.01, 24))})
    monkeypatch.setattr(portfolio_risk, "build_sample_price_data", lambda: prices)
    app = AppTest.from_string("from app_pages.portfolio_risk import render\nrender()", default_timeout=40).run()
    assert not app.exception
    risk = next(frame.value for frame in app.dataframe if "contribution_to_volatility" in frame.value)
    displayed_vol = next(metric.value for metric in app.metric if metric.label == "Ann. Volatility")
    assert displayed_vol == f'{risk["contribution_to_volatility"].sum():.2%}'


def test_zero_volatility_page_remains_usable(monkeypatch):
    from app_pages import portfolio_risk
    prices = pd.DataFrame({"date": pd.bdate_range("2026-01-01", periods=30), "A": 100.0, "B": 100.0})
    monkeypatch.setattr(portfolio_risk, "build_sample_price_data", lambda: prices)
    app = AppTest.from_string("from app_pages.portfolio_risk import render\nrender()", default_timeout=40).run()
    assert not app.exception
    assert not app.error
    assert next(metric.value for metric in app.metric if metric.label == "Arithmetic Sharpe") == "N/A"


def test_valuation_input_changes_hide_old_results():
    app = AppTest.from_string("from app_pages.structured_products import _render_structured_products_valuation_proxy\n_render_structured_products_valuation_proxy()", default_timeout=40).run()
    app.button(key="run_structured_products_valuation_proxy").click().run()
    assert not app.exception
    assert any(metric.label == "Fair Value Proxy" for metric in app.metric)
    app.number_input(key="valuation_proxy_notional").set_value(2000.0).run()
    assert not app.exception
    assert any("Inputs changed" in warning.value for warning in app.warning)
    assert not any(metric.label == "Fair Value Proxy" for metric in app.metric)
