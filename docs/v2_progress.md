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

## Phase 2 — Overview and Markets

Completed: automatic cached market context, per-series source/observation dates, latest/1W/1M US and ECB curve overlays, curve-change bars and spreads, DV01/CS01 charts, shared-book ES and exposures, hypothetical scenario bars with separate liquidity, numerical risk insights. The source status may be mixed and never relabels stale public observations as fresh. Portfolio risk history is explicitly synthetic and separate from public context.

Validation after resume: 410 tests passed; real Yahoo quote and ECB curve reads succeeded. FRED timed out within its bounded request window; the US curve was visibly labelled SYNTHETIC. The standard certifi trust bundle resolved the local ECB certificate-chain issue without disabling verification. Browser inspection confirmed the overview, market strip and dated source labels. Economic P&L reconciles by factor/position; liquidity-only stress does not enter P&L. Scenario and covariance detail are expanded in Phase 3.

## Phase 3 — Risk

Completed: sample/EWMA/Ledoit–Wolf covariance (transparent NumPy implementation), historical and Gaussian VaR/ES, marginal/component/incremental VaR, annual/rolling volatility, drawdown, correlations and rolling correlation, gross concentration diagnostics, prior-window VaR exceedances, custom factor and maturity shocks, scenario waterfalls/heatmaps, curve PCA, cashflow key-rate DV01, carry/roll proxies and full price–yield plots.

429 tests passed, including all risk tabs in EN/FR, 100-column covariance PSD, constant cash risk, Ledoit–Wolf fourth-moment reference, marginal VaR finite differences, component reconciliation, no-look-ahead validation and key-rate/parallel-DV01 reconciliation. The Risk Lab was inspected in the browser. The 97.5% ES setting is explicitly educational/FRTB-inspired without a regulatory claim. All P&L histories remain visibly synthetic unless user data is supplied; public curves retain separate provenance.
