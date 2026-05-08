# Market Analytics Terminal

A multi-asset desk utility platform built with Python, Streamlit, and R.

The objective is not to build a generic student pricer. The objective is to build a practical analytics terminal that converts market, portfolio, trade, and product inputs into outputs a sales, trader, structurer, portfolio manager, or risk analyst can actually use:

- risk summaries
- scenario analysis
- stress tests
- payoff explainers
- margin analytics
- portfolio diagnostics
- Excel reports
- R-generated performance analytics

This project is educational and proxy-based. It is not bank-grade pricing, not investment advice, and not a production risk system.

---


---

## Demo Screenshots

### Home — Multi-Asset Desk Utility Platform

![Home](docs/screenshots/01_home.png)

### Fixed Income Risk

![Fixed Income Risk](docs/screenshots/02_fixed_income_risk.png)

### Repo & Securities Lending

![Repo and Securities Lending](docs/screenshots/03_repo_sec_lending.png)

### Structured Products

![Structured Products](docs/screenshots/04_structured_products.png)

### Portfolio Risk

![Portfolio Risk](docs/screenshots/05_portfolio_risk.png)

### Cross-Asset Dashboard

![Cross-Asset Dashboard](docs/screenshots/06_cross_asset_dashboard.png)


## Core Modules

### 1. Fixed Income Risk

Bond portfolio analytics:

- clean / dirty price handling
- accrued interest proxy
- modified duration
- convexity
- DV01
- bucket risk decomposition
- curve shock scenarios
- simple hedge approximation
- Excel risk report

### 2. Repo & Securities Lending

Financing and collateral analytics:

- repo cash amount
- repo interest
- repurchase amount
- haircut sensitivity
- collateral shock
- margin deficit / surplus
- margin call logic
- securities lending borrow fee
- rebate amount
- collateralization rate
- specialness indicator
- financing and margin Excel report

### 3. Structured Products

Autocallable analytics:

- Athena payoff logic
- Phoenix payoff logic
- memory coupon
- autocall condition
- coupon condition
- protection barrier
- capital loss logic
- worst-of basket analytics
- Monte Carlo proxy
- autocall probability
- barrier breach probability
- expected payoff / P&L
- payoff distribution
- structured products Excel report

### 4. Portfolio Risk

Portfolio and risk analytics:

- asset weights
- portfolio returns
- annualized return
- annualized volatility
- Sharpe ratio
- max drawdown
- historical VaR / CVaR
- correlation matrix
- covariance-based risk contribution
- predefined stress scenarios
- portfolio risk Excel report

### 5. R Portfolio Analytics Companion

R companion layer for buy-side style analytics:

- performance summary
- rolling volatility
- rolling Sharpe
- drawdown series
- monthly returns
- correlation matrix
- R-generated charts
- outputs displayed inside Streamlit

---

## Tech Stack

Python:

- Streamlit
- pandas
- numpy
- scipy
- plotly
- openpyxl
- xlsxwriter
- pytest

R:

- Base R implementation
- CSV output generation
- PNG chart generation
- portfolio analytics companion workflow

---

## Project Structure

market-analytics-terminal/
│
├── app.py
├── app_pages/
│   ├── home.py
│   ├── fixed_income.py
│   ├── repo_sec_lending.py
│   ├── structured_products.py
│   ├── portfolio_risk.py
│   └── cross_asset_dashboard.py
│
├── engines/
│   ├── fixed_income_engine.py
│   ├── repo_engine.py
│   ├── sec_lending_engine.py
│   ├── structured_products_engine.py
│   ├── portfolio_risk_engine.py
│   └── scenario_engine.py
│
├── reports/
│   └── excel_exporter.py
│
├── r_analytics/
│   ├── portfolio_performance_report.R
│   ├── README.md
│   └── outputs/
│
├── data/
│   ├── sample_bonds.csv
│   └── portfolio_returns_sample.csv
│
├── docs/
│   ├── project_overview.md
│   ├── technical_validation.md
│   └── cv_positioning.md
│
└── tests/

---

## How to Run

Create and activate a virtual environment:

python3 -m venv .venv
source .venv/bin/activate

Install requirements:

python -m pip install -r requirements.txt

Run the app:

python -m streamlit run app.py

Run the R analytics companion:

Rscript r_analytics/portfolio_performance_report.R

Run the full test suite:

python -m pytest -q

---

## Current Test Coverage

The project contains more than 130 passing tests covering:

- fixed income analytics
- repo and securities lending
- Excel report generation
- structured product payoff logic
- worst-of basket analytics
- Monte Carlo simulation outputs
- portfolio risk analytics
- R analytics structure
- Streamlit integration checks

---

## Why This Project Matters

A basic pricer shows that someone can code a formula.

This project is different because it focuses on desk workflow:

1. Inputs are converted into interpretable risk outputs.
2. Outputs are linked to sales/trading/risk use cases.
3. Scenario analysis is prioritized over static valuation.
4. Excel reports are generated because desks still use Excel heavily.
5. R is used where it is credible: portfolio analytics and reporting.
6. Each module is tested, modular, and documented.

---

## Important Limitations

This project is not:

- bank-grade pricing
- live market data infrastructure
- a trading bot
- investment advice
- a production risk system
- a replacement for Bloomberg, Murex, Sophis, or internal desk tools

It is a transparent educational and portfolio project designed to demonstrate market understanding, technical execution, and practical desk workflow thinking.
