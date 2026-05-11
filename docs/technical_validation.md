# Technical Validation

The project includes automated tests for the core analytics engines and report generators.

## Main Tested Areas

### Market Data and Rates

- public quote adapter normalization
- fallback handling
- Treasury curve snapshot logic
- curve spread calculations
- rates/bond proxy display helpers


### Fixed Income

- duration
- convexity
- DV01
- curve shock logic
- Excel export generation

### Repo & Securities Lending

- repo cashflows
- haircut sensitivity
- margin deficit logic
- securities lending economics
- specialness classification
- financing Excel report

### Structured Products and Options

- vanilla option payoff logic
- option strategy payoff and P&L profiles
- Black-Scholes-Merton pricing
- Greeks and sensitivity outputs
- Athena payoff logic
- Phoenix payoff logic
- memory coupon logic
- protection barrier logic
- worst-of basket logic
- path simulation payoff proxy
- autocallable valuation proxy
- structured products Excel report

### Portfolio Risk

- portfolio return calculation
- annualized return
- annualized volatility
- Sharpe ratio
- historical VaR
- historical CVaR
- drawdown
- risk contribution
- stress scenarios
- Excel report

### R Integration

- R file structure
- generated outputs
- Streamlit references to R outputs

---

## Full Test Command

python -m pytest -q

---

## Validation Philosophy

The tests are designed to verify:

- formula consistency
- output structure
- report generation
- robust handling of mixed data types
- integration between modules

They are not intended to certify bank-grade pricing accuracy.
