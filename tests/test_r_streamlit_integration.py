from pathlib import Path


def test_portfolio_risk_page_contains_r_companion_section():
    page_text = Path("app_pages/portfolio_risk.py").read_text()

    assert "R Portfolio Analytics Companion" in page_text
    assert "performance_summary.csv" in page_text
    assert "rolling_risk_metrics.csv" in page_text
    assert "monthly_returns.csv" in page_text
    assert "correlation_matrix.csv" in page_text


def test_r_output_references_exist_in_page():
    page_text = Path("app_pages/portfolio_risk.py").read_text()

    expected_outputs = [
        "cumulative_performance.png",
        "drawdown_chart.png",
        "rolling_volatility.png",
    ]

    for output in expected_outputs:
        assert output in page_text


def test_portfolio_risk_page_imports_pathlib():
    page_text = Path("app_pages/portfolio_risk.py").read_text()

    assert "from pathlib import Path" in page_text
