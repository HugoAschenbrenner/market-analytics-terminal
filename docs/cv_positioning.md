# CV / Interview Positioning

## One-Line CV Bullet

Built a bilingual Python/R Market Analytics Terminal linking a shared cross-asset book to risk decomposition, stress scenarios, rates/FX hedges, derivatives P&L attribution and Excel reporting.

## Technical CV Bullet

Developed a five-workspace Streamlit terminal with 100-position book validation, sample/EWMA/Ledoit–Wolf risk, DV01-neutral curve trades, Garman–Kohlhagen FX hedges, finite-difference-validated advanced Greeks and controlled Monte Carlo autocallable risk; preserved audited financing engines and Python/R regression checks.

## Interview Pitch

I built the Market Analytics Terminal to show the connection between a market move and a desk decision. It starts with a shared demo book, shows the principal risk concentrations, applies coherent scenarios, and lets me express a rates or FX hedge or explain nonlinear option P&L. Every workspace uses the same book and market state.

The main engineering decisions were preserving validated financial calculations, centralizing units and source provenance, and separating economic P&L from liquidity requirements. Tests check reconciliation and financial identities, including analytical Greeks against finite differences and hedging cash-account identities. English/French, light/dark, optional CSV and Excel reporting make the workflow demonstrable without setup.

## Boundaries to explain clearly

The market strip combines dated public sources with labelled fallbacks. Portfolio risk history and volatility surfaces are synthetic demonstrations. Structured valuations and bump Greeks are Monte Carlo proxies with sampling error, not calibrated issuer prices. The 97.5% ES view does not establish regulatory compliance. R provides a separate reproducible companion report with parity checks rather than implying a second production risk platform.

Show a specific stress loss, the contributing exposure and a possible hedge expression. Discuss the assumptions and residual risk alongside the result. Current validation evidence is recorded in [technical validation](technical_validation.md) and [V2 completion](v2_completion.md).
