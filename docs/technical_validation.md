# Technical Validation

The project includes automated tests for the core analytics engines and report generators.

## Main Tested Areas

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

### Structured Products

- Athena payoff logic
- Phoenix payoff logic
- memory coupon logic
- protection barrier logic
- worst-of basket logic
- Monte Carlo simulation outputs
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
