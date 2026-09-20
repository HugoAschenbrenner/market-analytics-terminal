# Equity Derivatives upgrade — implementation ledger

Starting point: `a68b64c` on `codex/terminal-v2`, clean and also published on main.
V1 remains the public default; both interfaces and their switch must continue working.

## Reuse map

- `options_pricing_engine.py`: audited BSM, raw/scaled Greeks; retained.
- `pnl_explain_engine.py`: existing IV API, Taylor P&L and path hedge; reuse the
  P&L engine, preserve the old API, add a diagnostic Brent solver underneath.
- `risk_factor_engine.py`: covariance estimators, parametric VaR and Euler
  components already exist; extend their attribution/PCA/correlation outputs.
- `rates_tools_engine.py`: key-rate ladder, yield-price and carry/roll already
  exist; extend with editable zero curves and coherent cash-flow discounting.
- `scenario_engine.py`: legacy single-factor records retained; add a small
  common market-scenario contract for the option and curve labs.
- `desk_scenario_engine.py`: existing whole-book repricing retained.
- `services/analytics.py` / `book_risk.py`: shared book marks and risk retained.
- V1 six pages and V2 workspaces remain available; dedicated Equity Derivatives
  and Structured Products routes will expose focused workflows without removing
  legacy Derivatives Lab links or tests.
- Existing report exporters remain compatible. New lab outputs share a single
  workbook with explicit source, input and convention sheets.

## Stages

1. **Complete:** option chain, diagnostic IV, empirical smile/term, signed cash
   Greeks, scenario matrix and static hedge; financial tests and checkpoint.
2. **Next:** zero curve/scenario and risk-attribution extensions, invariants
   and checkpoint.
3. **Pending:** focused pages, navigation, shared scenario/dashboard snapshots,
   exports, bilingual controls, integration tests and checkpoint.
4. **Pending:** full regression, browser QA, documentation, final push and live
   verification. SVI/par bootstrap remain optional and will not displace Core.

Stage 1 validation: 733 tests passed (84.92 s); no BSM engine replacement or new dependency. The legacy IV interface delegates to the diagnostic Brent solver.
