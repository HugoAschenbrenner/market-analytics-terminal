# Technical Validation

V2 retains the audited pricing/payoff/financing engines and adds shared-state and numerical checks. The full pre-refactor baseline was 394 passing tests. The final suite passed 472 tests (no failures/skips) on 14 September 2026; the completed validation record is in [V2 completion](v2_completion.md). The [migration ledger](v2_test_migration.md) explains deliberate removal of superseded page tests; financial and original Excel contracts were preserved.

## Reproduce

From the repository root, after installing `requirements.txt`:

```sh
python -m pytest -q
python -m compileall -q app.py core components app_pages services engines reports
Rscript r_analytics/portfolio_performance_report.R
git diff --check
```

R is required for the Python/R numerical parity tests; inspect pytest's skip report if R is unavailable. Streamlit AppTest uses deterministic offline context fixtures. Live provider access is a separate availability check, not an assertion that prices remain fresh.

## Financial conventions

- **Book units and currency:** signed quantity × multiplier × mark. Equity marks explicitly select Book or Market; options and notes use model marks. Bonds quote clean prices per 100 nominal with multiplier 0.01; cash/FX quantities are currency units with price and multiplier 1. Monetary values translate using USD per local unit divided by USD per base unit. Optional weights reconcile to marked position value before repo liability, not net financed NAV.
- **Financing and NAV:** NAV is marked positions minus repo borrowing. Financing proceeds must also be recorded as cash. Changing base currency converts the liability and monetary margin terms. Contractual repo VM retains the agreed haircut; a new haircut changes refinancing capacity. Capacity loss and actual borrowing shortfall are distinct. Liquidity requirements are never added to economic scenario losses.
- **Bond cash flows:** ACT/ACT coupon accrual, clean plus accrued equals dirty, yield solved against quoted clean price, nominal coupon-frequency compounding. The simplified book constructs semiannual schedules from relative maturity and an inferred issue date; these are demo contracts. Long positive DV01/CS01 indicate a loss for a +1 bp rate/spread shock. Scenario P&L uses negative sensitivity × bp, with rate convexity. CS01 is a parallel spread-duration proxy. Key-rate ladders distribute discounted cash-flow exposure and reconcile to parallel DV01; carry and roll are estimates, not a funded total-return forecast.
- **Market curves:** FRED US constant-maturity par yields and ECB AAA zero-coupon yields are annual percent and have different bases. Changes are basis points. PCA centers daily changes, orders factors by explained variance and fixes their signs; level/slope/curvature are interpretations, not guaranteed shapes. Flat-YTM key-rate discounting is not calibrated curve pricing. Roll-down is unavailable where no matching USD/EUR contextual curve exists.
- **Options:** European BSM/GK, continuously compounded decimal rates and annual decimal volatility; time in years. Display controls labelled percent convert to decimals. Delta is price sensitivity per spot unit; Gamma is second derivative per squared spot unit; Vega and Rho are per +1 percentage point; Theta is per elapsed calendar day (annual Theta/365). Book quantities/multipliers and FX convert monetary Greeks. Cash Delta is spot × Delta; the 1% Gamma term is 0.5 × Gamma × (0.01 × spot)², not raw Gamma summed across unlike underlyings.
- **Advanced Greeks:** Vanna is ∂²V/∂S∂σ and Volga is ∂²V/∂σ² for decimal σ; Charm is calendar-time ∂Delta/∂t = −∂Delta/∂T per year. P&L Explain converts per-point Vega/Rho to decimal derivatives, uses ACT/365 elapsed days and reports the full-repricing residual. IV returns zero at discounted intrinsic value and rejects prices below that bound or at/above the finite-volatility upper bound.
- **FX and hedges:** S is domestic currency per foreign unit, F = S exp((rd−rf)T). GK replaces BSM dividend yield with the foreign rate; foreign Rho is also per percentage point. Pip size is 0.0001 except 0.01 for JPY domestic quotation. Exporter receipts are positive; importer payments negative. Option premium is paid upfront and financed to maturity in the proceeds comparison. A collar is offered only when a valid root exists. RR = 25Δ call vol − 25Δ put vol; simple BF = their average − ATM, not a premium-adjusted market-strangle calibration.
- **Risk:** deterministic 756-observation synthetic daily P&L histories use current fixed exposures. They are not observed strategy returns. Historical horizon P&L sums overlapping daily observations; VaR is the non-negative loss quantile and ES the non-negative average loss beyond it. Gaussian VaR/ES assume zero mean and square-root-of-horizon scaling. Annual volatility uses √252. Sample covariance is unbiased; EWMA uses normalized λ=0.94 weights and weighted-mean correction; Ledoit–Wolf shrinks stochastic columns toward a scaled identity while constant cash stays zero-risk.
- **Risk contribution:** Gaussian Component VaR sums to Gaussian VaR; it may be negative for hedges. Marginal VaR is per extra signed quantity unit holding the covariance model fixed. Incremental VaR compares current risk with removal of a position. Volatility contributions sum to annual portfolio volatility. Exceedances use only the prior 250 observations to estimate one-day thresholds. The 97.5% ES setting is FRTB-inspired, without regulatory compliance.
- **Structured products:** risk-neutral constant-volatility/correlation GBM, worst-of normalized to fixed initial fixings, contractual discrete observations and deterministic seeds. Athena and Phoenix retain their audited payoff conventions, including coupon memory and stub periods. Common-random-number bumps estimate per-underlying Delta, parallel Vega/Rho and correlation-point risk. Sampling error remains; barrier discontinuities can make sensitivities noisy. Cross-asset scenarios reprice spot → volatility → rates → correlation sequentially; allocations depend on that order. Valid correlation bounds are enforced. The flat-path payoff diagram is illustrative because actual cash flows are path-dependent.
- **Delta hedging:** long option/straddle and short model Delta, 252 simulated observations across the chosen contract life, adjustable rebalancing and transaction costs. The cash account includes interest, dividend cash flows and entry/rebalance/liquidation costs. Reported option P&L + hedge P&L + funding − costs reconciles to total. Initial implied volatility is constant; synthetic realized volatility is computed from the path's actual observation interval.

## What the tests establish

`test_v2_foundation.py`, `test_v2_integrity.py` and `test_v2_polish.py` cover 100-position validation, atomic invalid edits, shared marks/state, stable navigation, EN/FR key coverage, theme-independent calculations, persistent scenarios and base-currency financing invariance.

`test_v2_risk.py` checks covariance PSD, Ledoit–Wolf against its fourth-moment identity, constant cash, component reconciliation, marginal finite differences, prior-window validation, PCA and key-rate/parallel DV01 reconciliation. `test_v2_fx.py` checks CIP, cross-rates, domestic/foreign GK sensitivities, importer/exporter protection and DV01-neutral trade expressions.

`test_v2_derivatives.py` compares advanced Greeks to finite differences across option/time/dividend cases, recovers known IVs, validates arbitrage bounds, reconciles P&L and tests pathwise hedging cash accounts. `test_v2_structured.py` checks audited payoff parity, fixed initial fixings under spot bumps, common-seed sensitivities, probabilities and coherent scenario aggregation.

`test_v2_financing.py` and preserved audit tests check repo cash flows, contractual VM, refinancing versus borrowing shortfall and mutually exclusive cash/non-cash lending economics. `test_v2_reports.py` reopens all five report scopes, reconciles NAV/provenance, blocks text-formula execution and checks non-mutation. Preserved tests cover all four original exporters and Python/R parity. AppTest renders the workspaces and their lazy tabs in both languages.

## Data, limits and references

Public context uses verified TLS, a 15-minute cache, bounded socket reads and explicit fallback. Each observation retains source/date; a header retrieval timestamp does not make stale data live. Yahoo daily-bar last prices may include an unfinished session and exclude cash distributions. Provider changes, throttling or outages remain possible.

No model here establishes issuer fair value, funding-adjusted price, executable hedge economics, calibrated volatility arbitrage consistency or production/regulatory suitability. In particular, book options assume zero dividends and reject FX pairs; the dedicated Markets GK workflow supplies foreign-rate FX option pricing. R companion metrics apply to the bundled input CSV, separately from current book risk.

Primary methodology references used during the audit and V2 validation:

- [QuantLib ACT/ACT implementation](https://github.com/lballabio/QuantLib/blob/master/ql/time/daycounters/actualactual.cpp) for day-count interpretation.
- [scikit-learn shrinkage implementation](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/covariance/_shrunk_covariance.py) for Ledoit–Wolf formula cross-checks; the terminal implementation is NumPy-based.
- [FRED DGS10](https://fred.stlouisfed.org/series/DGS10) and [ECB yield-curve methodology](https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/euro_area_yield_curves/html/index.en.html) for source/basis distinctions.
- [ICMA haircut explanation](https://www.icmagroup.org/market-practice-and-regulatory-policy/repo-and-collateral-markets/icma-ercc-publications/frequently-asked-questions-on-repo/21-what-is-a-haircut/) for collateral valuation conventions.
- [PerformanceAnalytics drawdowns](https://github.com/braverock/PerformanceAnalytics/blob/master/R/Drawdowns.R) and [XlsxWriter workbook options](https://xlsxwriter.readthedocs.io/workbook.html) for companion/report checks.
