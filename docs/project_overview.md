# Project Overview

The Market Analytics Terminal is designed as a practical multi-asset analytics platform.

The design principle is simple:

Build tools that are useful to a desk, not just technically impressive demos.

The project covers six main market/risk areas:

1. Fixed Income Risk
2. Repo & Securities Lending
3. Options payoff and Black-Scholes pricing
4. Structured Products and autocallable valuation proxies
5. Portfolio Risk
6. Cross-Asset Dashboard synthesis

It also includes an R analytics companion for portfolio reporting.

---

## Workflow Philosophy

Each module follows the same workflow:

Input → Calculation → Scenario Analysis → Interpretation → Export

This mirrors real desk behavior more closely than a static calculator.

A sales, trader, structurer, PM, or risk analyst rarely needs only one number. They need:

- drivers
- sensitivities
- scenarios
- downside cases
- clean exports
- client/desk explanations

---

## Design Choices

### Python for the Main Terminal

Python is used for:

- analytics engines
- Streamlit interface
- scenario calculations
- Excel exports
- automated tests

### R for Portfolio Analytics

R is used as a companion layer for:

- portfolio performance reporting
- rolling risk metrics
- drawdown analytics
- monthly returns
- correlation diagnostics

This avoids duplicating every Python module in R and keeps R where it is most credible.


---

## Professional Demo Angle

The strongest demo path is not to present the app as a single calculator. It should be presented as a workflow:

1. Market/risk input
2. Analytics engine
3. Scenario or sensitivity analysis
4. Desk interpretation
5. Export or dashboard synthesis

This is closer to how a sales, structuring, trading, portfolio or risk team would discuss a problem than a static academic model.
