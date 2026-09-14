# R Portfolio Analytics Companion

The standalone base-R report reads `data/portfolio_returns_sample.csv` and writes reproducible performance, rolling-risk, drawdown, monthly-return and correlation outputs. Risk Lab exposes its CSV downloads in a technical expander. These outputs describe the bundled sample, not the current shared PositionBook; duplicate R charts are kept out of the main terminal workflow.

Run from the repository root with R installed:

```sh
Rscript r_analytics/portfolio_performance_report.R
```

Outputs in `r_analytics/outputs/`:

- `performance_summary.csv`
- `rolling_risk_metrics.csv`
- `drawdown_series.csv`
- `monthly_returns.csv`
- `correlation_matrix.csv`
- `cumulative_performance.png`
- `drawdown_chart.png`
- `rolling_volatility.png`

The R implementation uses 252 daily observations per year and a 63-observation rolling window. Drawdown includes initial capital as a possible high-water mark. Python/R parity and generated-output checks run in the Python suite; install R to execute the parity checks rather than skip them. PNG byte output can vary slightly across graphics/font environments even when the CSV values agree.

This companion demonstrates reproducible analytics and interoperability; it is not a production portfolio risk service.
