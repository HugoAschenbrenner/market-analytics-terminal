# V2 final workstation — execution ledger

## Checkpoint 0: reconstruction, 29 September 2026

Starting revision: `ca8105a226ecfa38299d34ff675e14273ba9b0de`, confirmed on
both `origin/main` and `origin/codex/terminal-v2`. Working tree and index clean.
Dedicated development branch: `codex/v2-final-workstation`. Production stays
on its validated dual-version release until checkpoint 8 is complete.

The new master brief explicitly supersedes the previous V1-default constraint
**at final release only**. Before then, the 42-file V1 freeze remains enforced.
Archive the final historical release before changing the router; retain all
shared pricing engines and financial regression tests.

Baseline actually executed: **917 passed in 61.75s**, no failures or skips.
This includes the Node-executed Interactive Greeks tests and Python/JS parity.
Compilation of both routers, pages, components, core, services, engines and
reports passed. Python environment: Streamlit 1.63.0, pandas 2.2.3, NumPy 2.3.5,
SciPy 1.18.1, Plotly 7.0.0, pytest 9.1.1, yfinance 1.7.0. Requirements are mostly
unpinned; no existing CI configuration. No package upgrade is needed initially.

Measured baseline is saved in `performance/v2_final_baseline.json` using
`scripts/benchmark_workstation.py`. Imports: 1.2612s. Under a controlled 0.15s
per-request provider outage, first/warm AppTest renders: welcome 1.3367/0.0162s,
EQD 0.8873/0.0393s, structured entry 0.7182/0.0167s (the latter currently has no
independent product). 100-equity risk 0.0431s; 35-cell option matrix 0.0006s;
10,000-path 3-name note 0.0163s; lab workbook 0.1313s. These local timings exclude
browser paint and are not Cloud SLAs. Page-first runs share imported Python
modules; the separately measured import time is reported rather than hidden.

Required prior documents were reviewed alongside the code: README, product
brief, completion/progress, market redesign, EQD lab, Interactive Greeks,
technical validation, assumptions and V1 freeze. Historical completion records
describe their own revisions, not the final scope of this new project.

## Architecture and verified audit findings

- `app.py` imports one of the two routers; `terminal_v1.py` and its original
  pages use frozen pure engines/report APIs. `terminal_v2.py` owns the new routes.
- Shared portfolio: `core.models.TerminalState` / `core.state`, consumed through
  `services.analytics`, `book_risk`, `financing`, `structured` and desk reports.
- Independent EQD/curve inputs: `services.lab.LabState`; scenario definitions
  and validated BSM/IV/Greek functions are already reusable. Interactive Greeks
  executes locally in JS and has separate browser session storage.
- Public monitoring: `services.market_monitor` plus typed `core.market_contracts`;
  cache, quotes, history, news and calculation views are already centralized.
  Educational book context is separately owned by `services.market_data`.
- **Confirmed:** global header calls a blocking 17-instrument ticker before every
  page. Each quote batch creates its own thread pool; welcome/EQD therefore do
  request data despite older documentation saying otherwise.
- **Confirmed:** the dedicated structured route requires a shared-book note and
  offers to replace the book. Its correlation slider allows invalid 3-name
  values below -0.5, and Athena displays a memory checkbox without an effect.
- **Confirmed:** fixed 2026-09-09 EQD/risk examples coexist with moving-date
  synthetic curve labels. Current historical risk is synthetic, not observed.
- **Confirmed:** Board JSON is limited to IDs; there is no complete validated
  analytical case import/export. Widget state and typed state have multiple
  owners and need explicit restoration with stale-result invalidation.
- The existing financial engines already cover the bulk of BSM, advanced
  Greeks, static/dynamic hedging, structured payoff/MC, rates/FX and portfolio
  attribution requirements. Extend those interfaces rather than duplicating them.

## Ordered implementation and acceptance gates

0. **Baseline — complete:** reconstruct, inspect required documents/code,
   run existing suite/compilation, record repeatable performance measurements.
1. **Technical remediation — pending:** bounded deferred ticker; provenance and
   adapter failure audit; independent structured state, valid correlation and
   meaningful memory controls; fixed-date demo labels; versioned atomic JSON
   cases for book/labs/curves/scenarios/preferences/Board and provenance.
2. **UX — pending:** workflow navigation with compatible slugs, consistent
   context and progressive detail; three reproducible offline demonstrations;
   EN/FR, themes and 390/768/900/1440/1920px responsive checks.
3. **EQD — pending:** forward/spot/delta volatility metrics and provenance;
   multi-position options book with currency-safe aggregation; simple/advanced
   P&L waterfall; validated skew/term shocks; hedge solver, static/dynamic
   comparisons and explicit Interactive Greeks transfer.
4. **Structured — pending:** shared term-sheet contract, observation schedule,
   investor/dealer/contract views, contractual timeline and scenarios, bounded
   MC/convergence/common random numbers, comparison and educational client sheet.
5. **Markets — pending:** configurable groups/columns, EQD defaults, derivatives
   context, two-window correlation comparison and verified event-risk panel.
6. **Portfolio/rates/financing — pending:** aligned observed-factor hypothetical
   P&L mode; before/after trade under identical conditions; preserve/improve
   explicit rates/FX/financing conventions and collateral linkage.
7. **Integration — pending:** explicit cross-module transfers, UI/export result
   parity, safe report strings, updated docs/README/screenshots/demo guide,
   performance comparisons and deterministic Python/Node GitHub Actions CI.
8. **Final release — pending:** full regression, historical V1 archive tag,
   V2-only root/legacy URL mapping, retirement of unused presentation only,
   test migration without weakening financial assertions, validated publication
   and real public-browser verification. Never infer deployment from push alone.

Each substantial completed unit must be tested, committed and pushed before the
next. Live-provider smoke tests are bounded and separate from deterministic CI.
No advanced stochastic-volatility/correlation/XVA model is planned. Unavailable
external inputs retain manual/offline alternatives with honest labels.

## Checkpoint 1a — deferred global ticker, complete

The global ticker now returns a nonblocking snapshot and polls its fragment every
5 seconds, with 5-minute price and 1-hour yield refresh eligibility. A shared
six-worker queue de-duplicates requests across sessions and is bounded by the
security directory; failure retries wait 60 seconds. Prior observations and
successful retrieval dates survive failed refreshes. No worker touches session
state. Explicit market pages reuse the same in-flight requests. Ticker DOM nodes
are updated in place so polling does not restart the scrolling animation.

Validation: **922 passed in 61.08s**, including blocked-provider independent-page
render tests, concurrency/retry/observation preservation and Node DOM identity.
Local browser: English/dark welcome rendered while all ticker data was loading,
with explicit loading labels and no substituted prices. Full responsive matrix
remains checkpoint 7. Diff whitespace check passed.

Measured local timings in `performance/v2_deferred_ticker.json`: welcome first
0.6967s/warm 0.0074s; EQD 0.2032s/0.0413s; structured entry 0.1046s/0.0064s;
controlled failure 0.3104s/cached 0.0000s. Independent pages no longer wait for
provider completion. These measurements include local runtime variation; the
stronger regression is that rendering completes while providers remain blocked.
Benchmark teardown cancels unneeded queued work; its request count is not a
production traffic forecast. Other checkpoint 1 items remain pending.

## Checkpoint 1b — independent structured laboratory, complete

Structured Products opens a fixed-date Phoenix worst-of example immediately,
without calling the shared-book market initializer. Independent edits preserve
positions, NAV inputs, market context, risk settings and financing; shared-book
analysis is an explicit alternate mode. An empty shared book is never replaced.
Draft product/basket selectors update dependent fields before applying a validated
contract. Athena has no ineffective memory checkbox. Independent labels describe
laboratory terms rather than claiming they modify the portfolio.

V2 accepts the closed PSD equicorrelation domain [-1/(n-1), 1]. The audited
interior GBM simulator remains reused; singular endpoints use the limiting
Cholesky factor without artificial jitter. Correlation sensitivities use common
random draws and bounded one-sided/secant bumps at endpoints. Zero-shock book
scenarios now preserve endpoint correlations exactly. Workloads are bounded to
20,000 paths, 8 names, 12 observations/year, 30 years and two million path values;
path-cache capacity is reduced from 128 to 16. The independent example contains
no inherited repo liability or unrelated collateral.

Validation: **940 passed in 82.50s**, zero failures/skips. Includes legacy Athena/
Phoenix payoff parity, endpoint matrix reconstruction for 2/3/5/8 names, fixed-seed
reproducibility, bounded sensitivity, zero-shock reconciliation and independent
state/mode/EN/FR application tests. V1 freeze remains intact. Local browser checked
French/light independent opening, model value and fixed-date caption; corrected
scope-specific wording was confirmed after server restart. Full responsive visual
coverage remains checkpoint 7. Other checkpoint 1 items remain pending.

## Checkpoint 1c — provenance and fixed demonstrations, complete (2 October)

Resumed from verified remote `293e6098c9f8493bb423dc32f23404beb32ec48e`.
The interrupted provenance changes were retained and reviewed; their former
transient test log was unavailable, so the targeted and full tests were rerun.

Book-context observations now expose source, observation time, successful
retrieval, attempted refresh, frequency, status and cache policy. Failed refreshes
retain the last success as stale, without inventing a new observation/retrieval.
Public monitoring cache records retrieval completion separately from request
start. Old observations remain old even after a recent retrieval. Context labels
and source cards expose this distinction; compact tiles retain detailed tooltips.
Synthetic USD/EUR curve histories now end on fixed 2026-09-09 instead of moving
with today's date. Invalid, duplicate/reversed/future quote timestamps and
oversized context responses are rejected. Missing changes remain unavailable.

The existing adapter separation is preserved: the public monitor has no synthetic
fallback; the educational portfolio context explicitly labels its fixed fallback.
Treasury par/constant-maturity versus ECB zero-curve conventions, German monthly
yield status, futures labels, adjusted-return disclosures and directional FX
conversion continue to pass their existing regression tests. Source cards do not
supply invented retrieval dates for older saved/manual metadata.

Validation: targeted provenance/market/guidance/deferred tests **51 passed**;
full suite **947 passed in 71.36s**, zero failures/skips; diff whitespace check
passed. Complete-case save/restore is the remaining checkpoint 1 item. The final
V2-only release remains pending and production has not been changed.

## Checkpoint 1d — versioned analytical cases, complete (2 October)

Added the Saved cases workspace under Board, a pure bounded JSON codec/validator,
preview then explicit restore, and labelled frozen market-context mode. Cases
include shared book/contracts/financing, both independent laboratories, chain/
curve/scenario inputs, attribution snapshots, Board IDs, views and preferences.
All validation precedes session replacement. Old widget/derived result caches
are invalidated; Board browser storage cannot overwrite a restored list. Existing
Board-only JSON import remains available. No credentials or arbitrary objects
are serialized. See `analytical_cases.md` for conventions and limits.

Interactive Greeks has one explicit capture button and one-time restored-input
handoff; its slider/curve loop remains in JavaScript. An edited independent note
now states USER INPUT rather than implying an unchanged fixed demonstration.

Validation: **106 targeted tests passed**; full regression **974 passed in
67.46s**, zero failures/skips, including existing Python/JS parity. Compilation
and diff whitespace checks passed. Round-trip tests reconcile marked positions,
option scenario P&L and curve PV and preserve provenance/snapshots. Adversarial
imports test atomic rejection of wrong versions/fields, invalid currencies/FX,
PSD/model domains, sizes, nesting, duplicate keys and nonfinite JSON numbers.

Real local browser, French/light: prepared and downloaded a 17.8 KB case, uploaded
that same file, previewed it and restored successfully. The independent Phoenix
value remained 97.27 per 100 nominal. Interactive Greeks spot was changed to 112
and explicitly captured with confirmation. Screenshot:
`screenshots/checkpoint1/case-restored-fr.jpg`. This is targeted workflow evidence,
not the final responsive/language/theme matrix. Checkpoint 1 is now implemented;
checkpoints 2–8 and final V2-only public deployment remain pending.
