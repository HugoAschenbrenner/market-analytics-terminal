from pathlib import Path


def test_r_analytics_files_exist():
    assert Path("r_analytics/portfolio_performance_report.R").exists()
    assert Path("r_analytics/README.md").exists()
    assert Path("data/portfolio_returns_sample.csv").exists()


def test_r_script_contains_expected_outputs():
    script_text = Path("r_analytics/portfolio_performance_report.R").read_text()

    expected_outputs = [
        "performance_summary.csv",
        "rolling_risk_metrics.csv",
        "drawdown_series.csv",
        "monthly_returns.csv",
        "correlation_matrix.csv",
        "cumulative_performance.png",
        "drawdown_chart.png",
        "rolling_volatility.png",
    ]

    for output in expected_outputs:
        assert output in script_text


def test_sample_returns_file_has_expected_header():
    first_line = Path("data/portfolio_returns_sample.csv").read_text().splitlines()[0]

    expected_columns = [
        "date",
        "US_EQUITY",
        "EUROPE_EQUITY",
        "US_TREASURY",
        "IG_CREDIT",
        "GOLD",
    ]

    for column in expected_columns:
        assert column in first_line
