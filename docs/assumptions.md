# Financial Assumptions

## Data

Core analytics use synthetic sample data or user-provided inputs. Optional yfinance quotes and official daily Treasury par yields provide separate public market context; they do not feed the portfolio or cross-asset stress calculations. A failed Treasury request uses an explicitly labelled synthetic sample curve.

The bond dataset in `data/sample_bonds.csv` is artificial and designed for demonstration purposes. It does not represent real client positions, proprietary portfolios, or live market data.

## Bond Dataset Conventions

The sample bond dataset uses the following fields:

- `bond_id`: synthetic identifier
- `issuer`: synthetic issuer name
- `currency`: EUR or USD
- `coupon_rate`: annual coupon rate in decimal format, e.g. 5% = 0.05
- `maturity_date`: bond maturity date
- `issue_date`: synthetic issue date
- `frequency`: coupon frequency per year
- `clean_price`: clean price per 100 notional
- `yield_to_maturity`: annualized yield in decimal format
- `notional`: position notional
- `rating`: synthetic credit rating
- `sector`: broad issuer sector
- `spread_bps`: synthetic credit spread in basis points
- `curve_bucket`: maturity bucket used for DV01 decomposition

## Important Limitations

The dataset is built for analytics development and interview demonstration. It is not intended for valuation, trading, investment advice, or risk reporting on real portfolios.

Fixed-income coupon dates are unadjusted, anchored independently to maturity and preserve maturity month-end. The generated schedule supports regular coupons and a short first stub. It does not infer business-day calendars, ex-coupon dates or bespoke long stubs. ACT/ACT bond accrual and discount exponents use coupon-reference periods (ICMA-style); the date-only year-fraction helper uses calendar ACT/ACT (ISDA). ACT/365F and US 30/360 are also supported. These conventions must match the instrument before interpreting results.

Portfolio analytics assume a fully invested long-only portfolio rebalanced to fixed weights each observation. Uploaded price series must share a currency basis and should include distributions if total-return analytics are intended. The engine does not perform portfolio FX conversion or dividend adjustment. The frequency selector controls summary volatility and absolute risk contributions. Stress classification is an illustrative asset-name heuristic; unrecognized labels use generic shocks. Cash has zero price shocks. Zero-volatility Sharpe ratios and risk-contribution percentages are undefined.

Drawdowns include initial capital before the first return. Historical CVaR selects observations below the raw return quantile before flooring the reported average loss at zero. VaR/CVaR use overlapping compounded windows for multiple periods and record the confidence level. Legacy Python summary attributes ending in `_95` remain available, but non-95% exports use neutral names.

Repo variation margin is calculated in cash-equivalent exposure units. If settling in securities with the same contractual haircut, the required dirty market value is absolute cash-equivalent VM divided by one minus that haircut. Threshold, minimum transfer amount and rounding are expressed in cash-equivalent units. Refinancing haircut resets remain a separate liquidity scenario.

The valuation proxy is a separate redemption-only coupon contract, not a price for the Athena/Phoenix payoff terms elsewhere on the page. Valuation paths use risk-free rate less dividend yield as drift; the separate payoff simulator uses the entered drift assumption. Simulation probabilities are model-dependent, not empirical forecasts. The reported autocall event includes a qualifying final observation. European capital protection is evaluated at maturity on surviving paths. Sensitivity scenarios disclose the applied correlation when the requested shock is outside the valid constant-correlation range.

Quote observation dates/timestamps are provider bar dates, which may describe an incomplete daily bar. Retrieval timestamps are separate and do not certify freshness. Snapshot changes use the provider's Close field with dividend auto-adjustment disabled and exclude cash distributions; they are not total returns. The data mode describes historical/delayed public data without promising near-live observations. Missing quotes and missing changes are unavailable values, not zeroes. The R companion is a separate static sample with equal weights, 252 periods/year and a 2% risk-free rate; it is not linked to the current Python portfolio inputs.
