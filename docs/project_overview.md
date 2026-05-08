# Project Overview

The Market Analytics Terminal is designed as a practical multi-asset analytics platform.

The design principle is simple:

Build tools that are useful to a desk, not just technically impressive demos.

The project covers four main market/risk areas:

1. Fixed Income Risk
2. Repo & Securities Lending
3. Structured Products
4. Portfolio Risk

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
