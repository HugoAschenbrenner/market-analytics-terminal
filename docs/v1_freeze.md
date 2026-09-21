# Stable V1 freeze and selective rollback

Reference: `a68b64c1d1e9092322a4a6fce0c4f9fc19ced0b9` (20 September 2026,
10:56 +02:00). Correction requested on 21 September 2026.

**V1 is frozen. All new product, UI and functional work belongs to V2 unless
the user explicitly authorizes a V1 change.** Root URL opens V1; `version=v2`
is required for V2. Discover V2 and Back to V1 remain exactly as at the reference.
Language/theme preferences are carried by those links. V1 keeps its original
English interface and localized version banner; full EN/FR workspaces are V2.

## Investigation before editing

The working tree was clean at `e16d918`; both remote branches contained that
commit. All four commits after the reference were inspected, together with
their file diffs and the recursive imports of the original V1 renderer:

- `f22be16`: new option-chain/IV and EQD engines, common scenarios and V2 copy.
  These new engines were correctly used by V2 and remain.
- `dd84905`: new curve/risk functions; an attribution adapter was appended to
  the stable V1 portfolio engine. Its old functions had not changed, but the
  adapter is now moved out to make the freeze unambiguous.
- `fa2f017`: correctly integrated the new features into V2, but also incorrectly
  added them to V1's menu, Home, rates, risk and dashboard, and removed the
  original vanilla tools from V1's Structured Products page.
- `e16d918`: V2 workflow/validation/documentation polish retained. Documentation
  and tests that incorrectly expected the new lab in V1 were corrected.

Chronology supports the Sunday-noon cutoff, but selection is based on actual
ownership/imports rather than timestamps. No reset, rebase or force-push is used.

## Exact restoration

These seven files are restored byte-for-byte from `a68b64c`:

- `terminal_v1.py`: restores original six-page mapping and HTML sidebar links;
  removes new EQD entry and native-button navigation.
- `app_pages/home.py`: restores five analytical modules, four reports, original
  cards and copy; removes the EQD card.
- `app_pages/fixed_income.py`: removes the new zero-curve lab insertion.
- `app_pages/portfolio_risk.py`: removes the new Gaussian attribution/PCA panel.
- `app_pages/structured_products.py`: restores original copy, payoff strategies,
  BSM pricer and interactive Greeks in their original locations.
- `app_pages/cross_asset_dashboard.py`: removes the new lab snapshot insertion.
- `engines/portfolio_risk_engine.py`: removes only the appended V2 adapter;
  every original function remains exactly as at the reference.

V1's existing styles, repo/lending page, pricing engines, market adapters,
exporters, version switch and root router were already unchanged. They remain
unchanged. The identity check covers these dependencies as well as the seven
restored files. Dynamic public quotes and date-dependent outputs can naturally
vary; their source code and behavior, rather than old observations, are frozen.

## V2 destination and preservation

No feature is duplicated merely because its incorrect V1 insertion is removed:

- EQD, option chains, smile/skew/term/surface, cash Greeks, scenario matrices,
  static hedging and Greek maps remain in `app_pages/equity_derivatives.py`,
  routed only by `terminal_v2.py`. Its obsolete V1 rendering branch is removed.
- The separate Structured Products route remains `app_pages/structured_lab.py`.
  The existing V2 Derivatives Lab/Product workshop/Interactive Greeks remain
  available through EQD's additional-tools link and their existing deep links.
- Editable zero curves and curve shocks remain under V2 Markets → Rates → Zero
  Curve Lab via `components/curve_builder.py` and `components/rates_workspace.py`.
- Gaussian/Euler attribution, correlation blends and PCA remain in V2 Risk Lab
  via `components/risk_attribution.py`. The return-weighted adapter is preserved
  in `engines/portfolio_attribution_engine.py`, reusing the frozen weight validator.
- Lab synthesis remains in V2 Desk Overview via `components/lab_dashboard.py`.
- `services/lab.py`, the common scenario definitions and `reports/lab_report.py`
  retain session inputs, conventions and the combined workbook.
- V2 Start cards, EN/FR explanations, themes and responsive controls remain.

## Isolation guard

The existing root router imports only the selected interface. V1's complete
local import closure is frozen; none of its pages imports the new lab components
or V2 state. V2 consumes audited shared pure functions without changing them;
extensions belong in V2 modules/adapters. No full architecture rewrite or copy
of the whole V1 codebase is needed.

`tests/v1_frozen_manifest.json` records SHA-256 digests from the reference commit
for 42 files: V1 entry/pages, all local imports (including package initializers),
shared version-banner colors, root router, Streamlit config, requirements,
original exporters and sample/R assets. `test_v1_freeze.py` checks these bytes,
the recursive import boundary and all six rendered V1 routes. A new V2-only
route without `version=v2` must fall back to the original V1 Home.

Do not regenerate the manifest to make a V2 change pass. If V2 needs to change a
frozen shared module, introduce a V2 adapter or isolate the changed presentation
in a V2-specific file. Changing V1 itself requires explicit user authorization.
The shared theme file is currently frozen because the stable version banner
reads its colors; future V2 styling can extend a separate theme module.

Tests for EQD use V2 only. The prior V1 lab-persistence test now verifies the
same behavior through V2 Overview navigation; it was an erroneous product
expectation, not a financial regression test removed to hide a failure.
New freeze tests replace the invalid expectation that V1 should expose EQD.

## Validation

Run the full Python/R/JavaScript test suite, compilation, diff checks and the
42-file reference comparison. Exercise the root/version-switch round trip in
EN/FR, desktop/mobile, then verify V2's current analytical pages and reports.
No separate lint/type-check/build pipeline is configured in this repository;
Streamlit runs the Python source and the browser component has no build step.
Original V1 Streamlit deprecation messages are retained with the frozen source;
they do not require changing its behavior during this rollback.

Validation completed on 21 September 2026:

- Full suite: **826 passed in 52.97 s**, with the installed Node runtime enabled.
- Python compilation and `git diff --check` passed.
- Direct comparison against Git: **42/42 frozen files byte-identical** to
  `a68b64c`, including the seven restored files.
- All six original V1 routes render offline without loading V2 state; the
  restored vanilla BSM controls are present in Structured Products.
- Browser: bare local URL opens the original five-module V1 Home; Discover V2
  opens Start, EQD and scenario controls. EN/FR version links round-trip to V1.
  Desktop and 391 CSS-pixel mobile views were inspected without page overflow;
  the temporary viewport override was reset.
- V2 analytical views, curves, risk attribution, input persistence, additional
  tools, structured products and workbook consistency remain covered by the
  passing regression suite.
