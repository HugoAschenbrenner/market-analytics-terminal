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
- V1 original pages and V2 workspaces remain available; dedicated Equity Derivatives
  and Structured Products routes expose focused workflows without removing
  legacy Derivatives Lab links or tests.
- Existing report exporters remain compatible. New lab outputs share a single
  workbook with explicit source, input and convention sheets.

## Stages

1. **Complete:** option chain, diagnostic IV, empirical smile/term, signed cash
   Greeks, scenario matrix and static hedge; financial tests and checkpoint.
2. **Complete:** zero curve/scenario and risk-attribution extensions, invariants
   and checkpoint.
3. **Complete:** focused pages, navigation, shared scenario/dashboard snapshots,
   exports, bilingual controls, integration tests and checkpoint.
4. **Validation complete:** full regression, browser QA and documentation.
   Publication/live verification follows the final validated checkpoint.
   SVI/par bootstrap are deferred optional features, not missing Core work.

Stage 1 validation: 733 tests passed (84.92 s); no BSM engine replacement or new dependency. The legacy IV interface delegates to the diagnostic Brent solver.

Stage 2 validation: 746 tests passed (59.64 s). Zero-curve discount/forward identities, twist knots, signed cash flows, nodal/parallel DV01 reconciliation, Euler allocation and PSD correlation stress checked.

Stage 3 validation: 776 tests passed (54.88 s). Both interfaces and EN/FR views,
legacy workshop navigation, structured-demo loading, session persistence,
invalid-input recovery and workbook formula-injection protection checked.
Existing vanilla V1 tools remain available under EQD → Additional option tools;
the primary Structured Products route now focuses on structured contracts.

Stage 4 final validation: 781 tests passed (54.74 s), including label/layout polish.
Compilation and `git diff --check` passed. Browser checks covered EQD at 391 CSS
pixels, dark EN and light FR controls, real scenario edits, curve steepening,
structured demo loading, risk attribution/export and dashboard propagation.
No body overflow at 391 CSS pixels (body and viewport widths both 391).
The browser check caught and led to a fix for EQD view reset on language change;
a regression now preserves both selected view and numerical inputs.

Local deterministic timings: cold EQD outputs 0.105 s; warm 0.026 s; curve
outputs 0.001 s; 500-point Greek map 0.007 s; full lab workbook 0.114 s.
These are local engine measurements, not Streamlit Cloud latency guarantees.
New module methodology, limitations and release scope are in
`docs/eqd_volatility_risk_lab.md`; README includes the revised 90-second demo.
