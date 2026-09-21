# Market Analytics Terminal

A Python/R Sales & Trading and cross-asset risk workstation by Hugo Aschenbrenner. **Input → Calculation → Scenario → Interpretation → Export** connects an Equity Derivatives Volatility & Risk Lab with curve analytics, portfolio risk and structured products. V2 provides English/French and light/dark controls.

The [hosted terminal](https://market-analytics-terminal.streamlit.app/) opens on **V1**, the main version. Use **Discover V2** at the top of any V1 module to open the [V2 introduction](https://market-analytics-terminal.streamlit.app/?version=v2), and **Back to V1** to return. Both interfaces run in the same deployment. Switching versions starts a new session; export any work first. V1 retains its original modules and audit fixes, plus the new Equity Derivatives page; V2 is an explicit opt-in through `version=v2`.

V2 opens on **Start / Accueil**, with six focused workspace cards and explanations of data, controls and simulations. Book workspaces share a demo portfolio. The EQD and zero-curve labs use independent session inputs, synthesized in the overview without adding them to portfolio totals. Public context carries observation dates and source labels. The default option chain and portfolio risk history are deterministic synthetic examples; a user chain can supply prices or IVs. These are educational analytics, not executable quotes, issuer valuations or regulatory risk measures.

Select **Open the overview / Ouvrir la vue d’ensemble** to begin, or choose a workspace card. Returning to Start preserves the current portfolio. Start and Equity Derivatives load without fetching market data. Other book workspaces request optional public context. Use `?version=v2&page=welcome&lang=fr&theme=dark` for the French introduction, or `?version=v2&page=equity-derivatives` to enter the lab directly.

## A 90-second demonstration

1. **Home / Start — 0–10 s:** identify the version, the shared book and the independent lab examples.
2. **Equity Derivatives — 10–40 s:** read ATM IV and downside skew; switch smile/term views. Open Scenario P&L, apply −5% spot / +3 vol points and compare full repricing with local Greeks. Open Delta hedge to see the residual risk after neutralizing initial Delta.
3. **Structured Products — 40–50 s:** load the structured demo if needed (explicitly replaces the shared book); explain Athena/Phoenix barriers, Monte Carlo value and sampling error.
4. **Fixed Income / Curves — 50–65 s:** in V1 use Fixed Income Risk → Zero curve lab; in V2 use Markets → Rates → Zero Curve Lab. Apply Bear steepener: 2Y +10 bp, 10Y +40 bp. Compare full cash-flow repricing and nodal DV01.
5. **Portfolio Risk — 65–80 s:** open Gaussian attribution in V1, or Risk Lab → VaR in V2. Contrast historical VaR with Gaussian Component VaR, inspect the largest contributor and PCA, then vary the correlation blend.
6. **Cross-Asset Dashboard / Desk Overview — 80–90 s:** read the same lab scenario outputs beside the book summary, keeping their scopes separate. Prepare the combined lab workbook from EQD, Curves or Attribution.

Select Multi-Asset Balanced, Rates & FX Macro, Equity Options Book or Structured Products / Hedged Book. CSV import is optional under **Load custom book**; the editable book supports 100 positions. Language, theme and book selections persist within the session. Links can specify `?version=v2&page=overview&lang=en&theme=dark`.

## Workspaces and analytics

- **Desk Overview:** shared marked NAV and risk KPIs, yield curves, risk contributions, scenario P&L and calculated concentration/Greek insights.
- **Equity Derivatives:** European price-to-IV Brent inversion with row diagnostics; editable/CSV option chain; empirical smile, 25-delta interpolation, term structure and heatmap/3D surface; signed cash Greeks, five-Greek P&L versus full BSM, editable spot/vol matrix, static delta hedge and Delta/Gamma/Vega maps. No feed required.
- **Structured Products:** a dedicated route for Athena/Phoenix, worst-of contracts, payoff logic, Monte Carlo valuation proxy and contract risk. The existing structured-product engine is retained.
- **Markets — Fixed Income Risk and FX:** audited clean/dirty bond valuation, ACT/ACT schedules, duration/convexity, DV01/CS01, key-rate ladders, carry/roll estimates, curve overlays and trade builders. FX includes covered interest parity, cross-rates, swap points, Garman–Kohlhagen Greeks and client hedge comparisons.
- **Risk Lab — Portfolio Risk:** sample, EWMA and Ledoit–Wolf covariance; distinct historical/Gaussian VaR and ES; marginal/component/percentage risk and VaR; PSD-preserving correlation blends and covariance PCA with portfolio exposure and explained variance. Existing rolling diagnostics and whole-book scenarios remain available.
- **Additional derivative tools:** accessible from EQD → Additional option tools. The preserved V2 Derivatives Lab contains book options, higher-order Greeks, the existing hedging-path experiment, Product workshop (strategies, barriers and certificates), and Interactive Greeks. V1's earlier payoff/pricer/interactive tools are also retained under EQD's additional-tools expander.
- **Financing — Repo & Securities Lending:** contractual cash flows and margin with threshold/MTA/rounding, cash/non-cash lending economics, collateral shocks and haircut-dependent refinancing capacity.
- **R Portfolio Analytics Companion:** reproducible CSV/PNG reporting and Python/R parity checks, available as a technical expander in Risk Lab. Its bundled dataset is separate from the current book.

Charts and headline metrics lead each workflow. Detailed data, formulas, assumptions and reports are collapsible. The four original Excel exporter APIs and unified V2 book report remain available. A separate combined **lab workbook** exports chain, smile/term data, cash Greeks, scenario/matrix/hedge inputs and outputs, direct zero curves, nodal DV01, and the last computed risk-attribution snapshot with its source and units. See [EQD/curve/risk conventions and validation](docs/eqd_volatility_risk_lab.md).

## Reading the terminal on any screen

The header, controls, KPI cards and chart columns adapt to phone, tablet and large desktop widths. On a phone, scroll the market strip and long tab lists sideways; detailed tables scroll inside their own panels. Light and dark charts share consistent, contrast-checked colors.

Open **Understand this workspace · data & controls** in any analytical workspace for a plain-language introduction, an inventory of actual data sources and observation dates, explanations of why values change or stay fixed, and a metric glossary. The help icon beside each KPI explains its units and reveals a more precise value. The same guidance is available in French; Start provides a shorter introductory FAQ.

Public context refreshes on request through a 15-minute cache; there is no streaming feed. The guide distinguishes shared book edits from local what-if controls, public observations from synthetic samples, and market curves from model-rate assumptions. See the [responsive UI validation and current screenshots](docs/ui_responsiveness_2026_09_15.md).

The Product workshop is a separate experiment inside Derivatives Lab: its user-entered examples do not modify the shared book or exported desk report. Explanations distinguish theoretical price from cash redemption and P&L, and model touch probability from a market forecast. See the [product research, conventions and validation record](docs/derivatives_workshop_2026_09_17.md), including the 652-test regression result and mobile/desktop captures.

**Derivatives Lab → Interactive Greeks Lab / Dérivés → Greeks interactifs** adds a separate BSM explorer. Six sliders update twenty analytical curves, current points, tangents and prices continuously in the browser. Inputs are illustrative and independent of the book/feed. The exact four-row matrix connects each function to its derivative, with explicit elapsed-time signs, raw units and market-unit equivalents. It supports EN/FR, both themes and desktop/tablet/mobile layouts. See the [architecture, conventions and validation record](docs/interactive_greeks_lab.md).

## Demo Screenshots

Local V2 captures; displayed public observations are dated snapshots, not current quotations.

### Start / Accueil — French, dark

![Introductory menu and suggested first visit](docs/screenshots/v2_welcome_fr_dark.jpg)

### Desk Overview — light

![V2 Desk Overview in light mode](docs/screenshots/v2_overview_light.jpg)

### Markets — dark

![V2 Markets in dark mode](docs/screenshots/v2_markets_dark.jpg)

### Risk Lab — light

![V2 Risk Lab in light mode](docs/screenshots/v2_risk_light.jpg)

### Derivatives Lab — dark

![V2 Derivatives Lab in dark mode](docs/screenshots/v2_derivatives_dark.jpg)

### Financing — French, dark

![V2 Financing in French and dark mode](docs/screenshots/v2_financing_fr_dark.jpg)

## Run locally

Python 3.11+ is recommended; this revision was validated with Python 3.12 and Streamlit 1.63.0. R is optional for the terminal itself and required to regenerate companion outputs and execute R parity checks.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

No API key is required. On entry to an analytical workspace, the market service automatically requests public context, caches it for 15 minutes and falls back to dated cached or labelled synthetic series when a provider is unavailable. An offline session remains usable.

```sh
python -m pytest -q
python -m compileall -q app.py terminal_v1.py terminal_v2.py core components app_pages services engines reports
Rscript r_analytics/portfolio_performance_report.R
```

UI tests use deterministic offline market fixtures. Public adapter tests cover parsing, dates and failures; a passing suite does not promise continuing provider availability.

The full test suite also requires **Node.js 20+** on `PATH` (or `NODE_BINARY` set to its executable) to execute the actual Greeks browser modules and compare their results with Python/SciPy. Node and npm are **not** needed to run or deploy the Streamlit application; the component ships local JavaScript/CSS without a build step or CDN.

## Architecture

```text
app.py                 version router (V1 by default, V2 opt-in)
terminal_v1.py         Home plus six analytical modules; public default
terminal_v2.py         shared session initialization and V2 workspace routing
core/                  typed state, book validation, i18n, semantic themes
components/            shared controls, charts, formulas and nested workflows
app_pages/             V1 modules, six focused V2 workspaces and legacy tools
services/              market/book analytics and independent LabState inputs
engines/               audited pricing, payoff, risk and scenario calculations
reports/               shared-book report, lab workbook and legacy exporters
r_analytics/           standalone report, CSV/PNG outputs
tests/                financial, state, UI, report and R regression coverage
```

See [project architecture](docs/project_overview.md), [financial conventions and validation](docs/technical_validation.md), [V2 requirement completion](docs/v2_completion.md), [checkpoint history](docs/v2_progress.md), [test migration ledger](docs/v2_test_migration.md) and the [original audit](docs/audit_2026_09_10.md). Interview wording is in [CV positioning](docs/cv_positioning.md).

## Data and model boundaries

Yahoo daily bars may contain an unfinished session. FRED Treasury and ECB euro-area curves have different construction and publication calendars; the latest retrieval time is not an observation date. PUBLIC, SYNTHETIC and USER INPUT provenance remains visible, with MODEL identifying calculated marks.

V2 portfolio return/risk history is a deterministic 756-observation scenario sample applied to current exposures, **not historical performance or a backtest of a traded strategy**. Its ES view at 97.5% is educational/FRTB-inspired, without regulatory compliance. Bond schedules in the simplified editor assume semiannual coupons and inferred dates; the underlying audited engine supports fuller contractual inputs. Equity book options use European BSM with zero dividend yield; FX options are priced in the dedicated GK workspace rather than accepted as equity options in the book.

Synthetic volatility surfaces are not calibrated or guaranteed arbitrage-free. Monte Carlo structured prices and sensitivities have sampling error and omit issuer credit, funding, transaction costs and model calibration. Curve trades, carry/roll and hedges are analytical approximations. The [validation document](docs/technical_validation.md) specifies units, signs, assumptions and tests so these limits remain reviewable.

The new lab uses continuous zero rates with linear interpolation, not a par/OIS bootstrap. Its illustrative coupon bond is separate from YTM-priced book positions. Option scenarios require positive shocked IV and remaining maturity; the static hedge excludes costs, funding and time passage. Optional SVI calibration and par-curve bootstrapping are deferred. No new heavy dependency, optimizer, backtest, automated trading or XVA module was added.
