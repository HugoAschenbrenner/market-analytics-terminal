# V2 implementation and validation record

Brief: [V2 product specification](v2_product_brief.md).
Baseline: `53368ad64ac50f2381766949fcba3ca112e03cdc`; 394 tests passed on 10 September 2026 before refactoring.
Branch: `codex/terminal-v2`, based on the audited engines. V2 is implemented in seven sequential checkpoints. It is not deployed to the public Streamlit app during development.

## Phase 1 — Foundation

Shared typed MarketState, PositionBook, RiskState, ScenarioState and UIState; four demo books; one quantity-driven mark/exposure service; editable/importable book; five stable workspace slugs; in-session navigation; EN/FR catalog; semantic light/dark tokens; shared Plotly styling; collapsible details and methodology. Streamlit is pinned to 1.63.0 for lazy tabs and current widget APIs. All valuations ignore language/theme.

22 foundation tests passed, including 100 positions, invalid-input isolation, shared exposures, both languages/themes and navigation persistence. The browser layout was inspected; the native header overlap was corrected. The complete suite passed 406 tests (no failures) after the deliberate navigation specification changes.

Intentional test migrations: seven duplicate/source-only tests requiring the previous sidebar links were replaced by executable navigation/state tests. Ownership and global-style assertions now point to centralized components. Audited financial-engine and export assertions remain. Legacy page modules are temporarily retained solely while their deeper workflows migrate in phases 2–6; they are not routes and will be removed after replacements are validated.

## Remaining phases

2. Overview and Markets: automatic public context with provenance/fallback, US/ECB curves and history, rates charts, shared calculated risk KPIs.
3. Risk: covariance estimators, historical/parametric VaR and ES, component/marginal/incremental risk, rolling diagnostics, coherent scenarios, curve PCA.
4. Sales/trading: curve trades, FX forwards and Garman–Kohlhagen, client hedges.
5. Derivatives: formulas, advanced Greeks, IV, volatility surface, P&L explain, hedging simulation.
6. Structured/financing: lazy product/risk/simulation/advanced views, controlled MC bump risk, financing charts, retire superseded page implementations.
7. Polish: unified exports, translations/visual QA, performance, documentation/screenshots, complete regression suite and remote verification.

## Convention decisions

- Quantities drive exposure. Signed quantities support hedges; asset values are translated to the book base currency.
- Bonds retain audited ACT/ACT coupon schedules, clean/dirty reconciliation, DV01 and CS01. Prices are per 100 nominal.
- Equity options use audited European BSM with shared underlying spot and currency rate; contract volatility and strike belong to the position.
- Repo cash is a liability deducted from NAV; matching proceeds must be booked in cash. Liquidity is separate from economic P&L.
- Demo data is synthetic, explicitly labelled. Public observations must carry their own date/source and cannot be presented as live data by inference.
