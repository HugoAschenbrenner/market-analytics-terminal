# V2 market navigation redesign — implementation record

## Scope and starting point

21 September 2026; clean `codex/terminal-v2` at `b3ff1b1`. V1 is read-only.
The 42-file manifest remains unchanged, including `app.py`, the version switch,
requirements, `core/theme.py`, all V1 pages and their engine dependencies.
New presentation tokens must therefore live in `core/v2_theme.py`.

## Reference exploration before implementation

Tape Finance was explored in its rendered browser UI, not from source code:
Markets, Equities, Indexes, Forex, Commodities, Rates, ETFs, search → NVIDIA,
Summary, Volatility, Events, company Board, World, News, Watchlist, Black-Scholes
and Analysis/Risk Premia. Desktop screenshots were inspected. The personalized
watchlist requires login, so its authenticated editing behavior was not inspected.
No Tape code, branding, text, images, prices or datasets are imported into MAT.

Useful principles: a quiet near-black shell, thin dividers, compact aligned
numbers, shallow top navigation, instrument identity carried into contextual
tabs, short correlation lookbacks, dated sources, and a persistent market strip.
The large density of ratios on the reference security page is not reproduced;
MAT favors essential statistics and optional fundamentals. Company governance
“Board” is distinct from MAT's personal monitoring Board. Sentiment and headline
counts are not repackaged as geopolitical risk measures.

## Existing V2 inventory and decisions

- KEEP: shared `TerminalState`, demo/imported books, validated marks, scenarios,
  currency conversion, reports and the separate `LabState`.
- KEEP: EQD chain/Brent IV/smile/term/surface, signed Greeks and scenario P&L,
  delta hedging, matrix controls and combined workbook.
- KEEP: Derivatives Lab, BSM, higher-order Greeks, interactive browser Greeks,
  strategies/barriers/certificates, hedging paths; structured Monte Carlo and
  Athena/Phoenix/worst-of terms.
- RELOCATE: existing Markets rates/FX workspaces under Analytics; preserve curve
  overlays, zero curves, DV01/KRD, carry/roll, curve trades, CIP/GK/client hedges.
- MERGE: Overview, Risk Lab and Financing into a Portfolio navigation family;
  retain VaR/ES/Euler attribution/PCA, stress, repo and securities lending.
- IMPROVE: `components/global_header.py`, V2 styling, Plotly and interactive
  Greek colors; compact Start menu, progressive disclosure and responsive layout.
- ADD: reusable Security metadata, typed dated data results, bounded shared cache,
  search, public market monitor/ticker, asset classes and security pages.
- ADD: return correlations, realized volatility, news/events/fundamentals when
  available, regional World, market sessions and a portable personal Board.

The prior public-context adapter reads Yahoo/FRED/ECB with a labelled synthetic
fallback for educational book analytics. It stays separate from the market
monitor: the latter must never substitute synthetic observations. Shared price
reads for the new ticker, tables, security pages and Board use one data service.

## Checkpoints

1. Foundation: metadata, financial units, bounded cache, provider parsing and tests.
2. Shell/Markets: isolated theme, navigation, ticker, market monitor and sessions.
3. Security/context: charts, statistics, volatility, correlations, news/events,
   World, Board and contextual links to preserved analytics.
4. Polish: full regression, real-provider smoke checks, browser desktop/mobile,
   language/theme and V1 identity checks; final docs and verified remote pushes.

Each substantial validated unit is committed and pushed before continuing.

### Shell/Markets checkpoint

Added a V2-only neutral dark/light theme, grouped navigation, shared security
search, a five-minute ticker fragment (CSS animation does not poll), responsive
market rows and one reusable security route with seven chart horizons. Existing
rates/FX analytics now live at `page=analytics`; all pricers, books and reports
remain available. The ticker and rows navigate within the current session.
Cash-session schedules use IANA zones and include Asian lunch breaks; holidays
are explicitly unverified. No quote substitute is used when FRED is unavailable.

Validation: 861 tests passed, including the unchanged 42-file V1 manifest/import
closure and all frozen V1 routes. Existing UI tests were migrated to the grouped
navigation, while financial assertions were retained. Browser inspection found
and corrected a light table on the dark theme and navigation after component
triggers. Yahoo observations loaded in the local preview; FRED timed out, while
Treasury XML, Yahoo RSS, Federal Reserve RSS and ECB RSS responded successfully.
BLS calendar requests returned HTTP 403; event views must preserve this limitation.
