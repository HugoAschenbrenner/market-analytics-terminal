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

### Security/context checkpoint

Added return correlations (20/60/120/252 matched observations), adjusted-return
realized volatility, public RSS with source/date/filtering, corporate events,
official economic calendars, optional fundamentals, regional World, and a
personal Board. Board IDs can be added/removed/reordered, stored in the browser
or exported/imported as JSON. Explicit security→Options/FX transfers retain the
existing labs and label user assumptions; observed prices never relabel the
synthetic option chain. The old book is not silently re-marked by Board prices.

US yields now come from the official Treasury daily par-yield XML (year resources
shared across tenors). FRED remains the labelled German monthly series. Daily
moves use the preceding dated close, including crypto's UTC calendar boundary.
Compact sparklines, Treasury curves/spreads and indicative FX crosses were added.

Validation before interruption: 905 tests passed in 55.90s, including all V1
freeze tests. On resumption, 130 relevant tests passed again. Public-provider
smoke: all tested US tenors and 54 combined Yahoo/Fed/ECB headlines available.
The BEA subscription page's actual ICS link was resolved and verified: 119
calendar entries, 17 future releases at verification. BLS returned HTTP 403;
its failure is isolated with a direct official-calendar link. No invented dates.
Board browser checks cover instrument addition and persisted configuration.

### Completed polish and interruption recovery

The initial resumed state was `e81cc05`, already on GitHub, with local UI/session
polish only. That work was retained. A later interruption left `3a13766` already
pushed and four context-polish files locally modified; those were recovered
without resetting the checkout. The 63 targeted checks from that interruption
had completed successfully.

Completed afterward: compact responsive headers and chart controls, synchronized
theme colors, native semantic market tables, bilingual source explanations,
provider session labels, the verified NYSE 2026–2028 holiday/early-close calendar,
precise five-calendar-year chart clipping, selectable Board news/events, adjusted
event-date returns with no causal claim, and explicit partial-calendar coverage.
World now separates central-bank releases from regional market headlines.

Validated and pushed checkpoints: `6471599` (data foundation), `1925ddb`
(navigation/Markets), `e81cc05` (security/context/Board), `b759151` (responsive and
session polish), `3a13766` (event returns and Board selection), `1118f70` (macro
priorities and calendar coverage), `a3cf7e5` (compact table consistency).
The final documentation/visual-validation commit follows these checkpoints.

The final resumption found `a3cf7e5` on the remote branch, no staged changes, and
only this report plus two CSS corrections locally modified. The last complete
regression run had already succeeded. Those changes were preserved: custom HTML
blocks no longer inherit Streamlit's negative bottom margin, preventing the
version/book and market-strip/metric overlaps; link buttons now use the V2 theme's
surface and text colors. Rendered geometry confirmed an 8px strip-to-metrics gap,
and computed colors confirmed readable dark-theme links.

## Data conventions and limitations

- Yahoo Finance chart observations are delayed/indicative, not an exchange live
  feed; 5-minute cache, with one resource reused by all monitoring views. Daily
  charts show raw OHLC; return analytics use adjusted closes for equities/ETFs.
  Current local calendar days are conservatively excluded from daily analytics.
- US Treasury yields are daily published **par** yields, cached one hour. German
  10Y is a **monthly average** from FRED/OECD, never described as a live Bund quote.
  FRED was unavailable during verification and the UI kept an empty observation.
- Futures are continuous front contracts, not spot commodity prices. Contract
  rolls can affect changes. FX cross rates are calculated indications, checked
  for a common date, with potentially different observation times.
- Correlations use aligned returns or yield changes in basis points. The
  20/60/120/252 window counts common observations. Realized volatility uses sample
  log-return dispersion and 252 periods/year (365 for crypto). No market IV is
  invented; the existing educational chain retains its synthetic label.
- RSS uses Yahoo, Federal Reserve and ECB feeds, cached ten minutes. Security tags
  identify feeds; they are not a guarantee of article relevance or impact. Search
  ranking counts text matches, without a sentiment/geopolitical risk score.
- BEA's actual ICS subscription was verified, including UTC conversion across
  DST. BLS returned HTTP 403: coverage is explicitly incomplete and direct
  calendar links remain available. Corporate dividends/splits and optional
  earnings timestamps are provider-reported, not an exhaustive events service.
- Optional fundamentals use yfinance with an eight-second UI wait and bounded
  concurrency. Missing fields remain empty. Financial reporting and listing
  currencies are identified. Provider reporting periods may differ.
- Sessions use IANA time zones and Asian lunch breaks. Only NYSE holidays and
  early closes for 2026–2028 are verified; other holiday calendars, auctions and
  exceptional closures remain explicitly unverified. The display is a scheduled
  state, not live exchange status. Beyond 2028, NYSE holidays are not extrapolated.
- Caches retain the last successful observation on failure, preserving its date;
  failure retries are bounded. Last-success caches are in memory and disappear on
  server restart. A fresh fetch does not imply a fresh underlying observation.
- Board configuration persists on the same browser/origin only; it can be
  exported/imported as JSON. Portfolio and lab states are separate. Switching
  versions opens a new session; the existing export warning remains visible.

Source references: [Tape](https://tapefinance.com/#/),
[NYSE calendar](https://www.nyse.com/trade/hours-calendars),
[Treasury rates](https://home.treasury.gov/resource-center-data-chart-center/interest-rates),
[BEA subscription](https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics),
[BLS calendar](https://www.bls.gov/schedule/),
[FRED German yield series](https://fred.stlouisfed.org/series/IRLTLT01DEM156N).

## Architecture and material files

The V2 router is `terminal_v2.py`; `components/global_header.py` owns grouped
navigation and global security search. New routes are `app_pages/market_monitor.py`,
`security.py`, `world.py`, `news.py`, and `board.py`. The preserved rates/FX page is
registered as `analytics`. Metadata, contracts, financial formatting and exchange
schedules live in `core/securities.py` and `core/market_*`. Fetch/cache, news,
statistics and explicit lab transfers live in `services/market_*` and
`services/security_workflows.py`. Monitoring presentation lives in
`components/market_*` and `components/monitor/`; `core/v2_theme.py` is V2-only.

No dependencies, V1 pages, V1 engine files, `app.py`, `core/theme.py`, version-switch
implementation or freeze-manifest entries were changed by this redesign.

## Validation

Automated suite: **917 passed**, most recent completed full run 89.72 seconds,
including the final CSS corrections.
This includes financial calculation/regression tests, JS interactive-Greeks
parity, Streamlit route/state interactions, cache failure and single-flight tests,
feed parsing, date/return alignment, split adjustments, common-date comparisons,
Board persistence contracts and explicit Options/FX transfer preservation.
Python compilation and `git diff --check` pass. No separate lint/type/build
configuration is defined in this Python/Streamlit repository.

V1 proof: all **42 frozen files** were compared byte-for-byte with Git reference
`a68b64c1d1e9092322a4a6fce0c4f9fc19ced0b9`; zero differences. The tests also
verify its complete local import closure, all six V1 routes, and default/invalid
version routing in both languages. Existing analytics assertions were preserved;
navigation tests were adjusted to the new V2 grouping only.

Browser checks used real rendered Streamlit pages, live provider responses and
DOM width checks. Tested CSS widths include **391, 900, 1440 and 1920 pixels**.
Dark/English and light/French were inspected. Checked Markets and correlations,
NVDA price/volatility/events/fundamentals, chart theme changes, World regional news
and sessions, News, Board and its retained Apple entry after reload, Treasury
curve/2s10s and FX crosses. Mobile charts fit their container; menus wrap, metric
cards form two columns, and wide tables scroll within their own container.
No document-wide horizontal overflow was observed at those tested widths.
Preserved EQD smile/surface, rates/FX analytics and portfolio overview were also
inspected. Structured Products' unloaded-book state was inspected; its pricing
and loaded-book behaviors are covered by automated regression tests.

The actual V2 “Back to V1” link was followed and the frozen V1 appearance checked.
Opening the bare root URL displayed V1's “Multi-Asset Desk Utility Platform”;
clicking “Discover V2” then loaded the redesigned V2 welcome page with its market
ticker, grouped navigation and introductory workflows. Both directions work.

At the original implementation handoff, the redesigned code was pushed only to
`codex/terminal-v2`; the public deployment had not yet been updated or verified.

## Streamlit publication — 22 September 2026

The user subsequently requested publication on the existing Streamlit app.
The complete suite was rerun: **917 passed in 61.97 seconds**, with compilation,
diff checks and all 42 frozen V1 file comparisons passing. The tested application
commit `7e7bbce5048e7eaf0eb9d9a5a637e8ba586305f7` was fast-forwarded from
`codex/terminal-v2` to `main`; both remote refs were verified at that SHA. No
application code or dependency changes were needed for publication.

The public app refreshed after the push and loaded the restored five-module V1
at its bare root. Its Discover V2 link loaded the new grouped navigation, global
search, market ticker and introductory workflow. Production Markets displayed
dated Yahoo observations and Treasury yields; the unavailable German series
stayed empty. Clicking S&P 500 opened its security page with prices, provenance,
chart horizons and a rendered one-year history. This verifies the actual hosted
interface, rather than inferring deployment solely from a GitHub push.
The Back to V1 link then returned to the restored V1 home successfully.

Public entry points: [V1 default](https://market-analytics-terminal.streamlit.app/)
and [V2](https://market-analytics-terminal.streamlit.app/?version=v2&page=welcome&lang=en&theme=dark).
The earlier pending-deployment note in `docs/v1_freeze.md` records the prior
checkpoint and is superseded by this production verification. Provider and
calendar limitations documented above continue to apply.
