# Project Overview

The Market Analytics Terminal V2 connects market context, positions, risk, scenarios and hedge expressions through one shared application state. Five workspaces replace the earlier independent pages: Desk Overview, Markets, Risk Lab, Derivatives Lab and Financing.

## State and calculation flow

`core/models.py` defines MarketState, PositionBook, RiskState, ScenarioState and UIState inside TerminalState. `core/state.py` loads one of four demo books, validates optional CSV/editor inputs, migrates open sessions and converts monetary financing terms when the base currency changes. Quantities drive exposure; optional weights must reconcile to marked positions before financing liabilities.

`services/market_data.py` populates dated public context with bounded requests and explicit fallback. `services/analytics.py` marks the book once through cached audited bond/option and structured engines, then translates monetary exposures into the base currency. Overview, Risk Lab, scenarios and Excel reports consume these same marks and contract terms. Language/theme never change financial inputs.

`services/book_risk.py` applies deterministic synthetic factor observations to current signed exposures. `engines/risk_factor_engine.py` calculates covariance and risk decomposition; `engines/desk_scenario_engine.py` aggregates economic stress separately from financing liquidity. `services/structured.py` connects shared note contracts to controlled Monte Carlo revaluation. `services/financing.py` connects the book's borrowing/collateral to contractual repo logic.

## Presentation

`components/global_header.py` owns stable routes, EN/FR and light/dark controls. `core/i18n.py`, `core/theme.py` and `core/charting.py` centralize text and styling. Five small `app_pages/` entry points select lazy tabs; reusable components contain detailed rates, FX, options, structured and financing workflows. Dataframes are reserved for editing or expandable calculation details.

The Overview starts with dated market context, six KPIs and a chart grid. Its commentary comes from calculated concentration, scenario and Greek exposure. Markets translates rates/FX views into trade and hedge expressions. Risk Lab edits the same book and compares losses. Derivatives explains nonlinear exposures. Financing shows their collateral and cash implications.

## Reporting and performance

`reports/desk_report.py` builds unified or focused workbooks with marks, risk, scenarios, contracts, sources and methodology. `reports/excel_exporter.py` retains all four audited legacy APIs. Text cells do not execute Excel formulas. The R companion remains a reproducible technical report on a separate bundled return sample; it does not duplicate the live desk charts.

Market data has a 15-minute cache. Marks and synthetic observations are cached; Monte Carlo uses vectorized operations, deterministic seeds, bounded caches and lazy advanced tabs. A local cold calculation for 100 equity positions and 756 observations took 0.8312 seconds, excluding imports and public network fetches. This is an observed benchmark, not a latency guarantee for 100 complex notes.

## Scope and evidence

All seven implementation phases are recorded in [checkpoint history](v2_progress.md). [Requirement coverage](v2_completion.md) maps the 36-section brief to code and tests. [Technical validation](technical_validation.md) distinguishes financial identities, finite-difference checks, deterministic proxy tests and external data limitations. Higher-complexity calibrated models remain deferred as requested.
