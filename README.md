# Multi-Asset Desk Utility Platform

## Objective

This project is a desk-oriented market analytics platform designed to convert market, portfolio, and product inputs into practical outputs such as risk metrics, stress tests, P&L explainers, scenario reports, and Excel exports.

The goal is not to build generic student calculators or a trading bot. The goal is to create a modular analytics toolkit close to the workflow of a sales, trader, structurer, portfolio analyst, or risk analyst.

## Planned Modules

1. Fixed Income Risk  
   DV01, duration, convexity, curve shock P&L, bucket risk decomposition, risk report.

2. Repo & Securities Lending  
   Haircuts, repo cashflows, collateral shocks, margin calls, borrow fees, specialness analytics.

3. Structured Products  
   Athena/Phoenix payoff logic, autocall probability, barrier breach probability, worst-of analytics, stress tests, factsheet export.

4. Portfolio Risk  
   Volatility, Sharpe ratio, VaR, Expected Shortfall, drawdowns, tracking error, benchmark comparison, R analytics layer.

5. Cross-Asset Dashboard  
   Equities, rates, FX, commodities, volatility, credit proxies, market regime, morning snapshot export.

## Core Workflow

Input → Calculation → Scenario Analysis → Interpretation → Export

## Current Status

Initial project structure created. Financial engines will be implemented module by module.

## Disclaimer

This project uses synthetic/sample data and simplified analytics for educational and demonstration purposes. It is not investment advice, not a trading signal engine, and not a bank-grade pricing platform.
