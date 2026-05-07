# R Portfolio Analytics Companion

This folder contains the R analytics layer for the Market Analytics Terminal.

Purpose:
- Generate buy-side style portfolio analytics.
- Produce CSV and PNG outputs.
- Later, Python Streamlit will read and display those outputs.

Run from the project root:

Rscript r_analytics/portfolio_performance_report.R

Input:
data/portfolio_returns_sample.csv

Outputs:
r_analytics/outputs/performance_summary.csv
r_analytics/outputs/rolling_risk_metrics.csv
r_analytics/outputs/drawdown_series.csv
r_analytics/outputs/monthly_returns.csv
r_analytics/outputs/correlation_matrix.csv
r_analytics/outputs/cumulative_performance.png
r_analytics/outputs/drawdown_chart.png
r_analytics/outputs/rolling_volatility.png

Limitation:
This is a simplified analytics companion, not a production risk engine.
