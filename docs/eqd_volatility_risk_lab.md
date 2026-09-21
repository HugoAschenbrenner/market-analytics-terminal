# Equity Derivatives, curves and risk attribution

Implementation and validation record — 21 September 2026. This extends the
existing BSM, P&L, rates, covariance and reporting engines without adding a
dependency. V1 remains the public default, with V2 available via the version
switch. Both interfaces expose the new Equity Derivatives module.

## Scope and data flow

The application has two explicit scopes. `TerminalState` holds the shared V2
book, market context and whole-book risk. `services/lab.py::LabState` holds an
independent option position, editable chain, curve example and lab scenario.
Lab positions are **not** automatically added to NAV or book stress totals.
The overview/Cross-Asset Dashboard recomputes the same lab inputs, separately
from portfolio totals. A combined workbook uses these same calculation paths.

The risk-attribution panel saves its last computed result, confidence, horizon,
units and source. The dashboard and lab export label it as a snapshot: visiting
another module does not silently invent a newly calculated portfolio history.
Reopen attribution after editing the book to update that snapshot.

The deterministic chain is anchored to 2026-09-09, with 30/91/182/365-day
expiries, sixteen strikes and calls/puts. Its prices are generated with a shaped
synthetic IV smile, not observed quotes. Its date is fixed for reproducible
demos; refreshing public markets does not change it. CSV/manual inputs replace
the demo only when applied, with `USER INPUT` provenance. Only one underlying,
spot, continuous rate and dividend convention is accepted per chain; invalid
rows remain visible with reasons and, where available, IV price bounds.

V2 EQD/Start do not fetch public data. The optional market-data layer is retained
for other workspaces. A quote can populate the lab position while preserving
signed quantity and multiplier. Editing that position changes its own source
label. Currency is an explicit denomination label, not an FX conversion.
In-session native navigation retains inputs. Switching V1/V2 or a full browser
reload starts a new session; export first. Legacy options tools remain reachable
from EQD → Additional option tools, and existing deep links remain supported.

## IV and empirical volatility

The existing European BSM pricer supplies both prices and analytical Greeks.
Rates, dividend yield and annualized IV are decimals. `0.215` means 21.5% IV;
a +3-vol-point shock adds `0.03`. Expiry minus valuation date uses ACT/365.

For discounted spot A = S exp(−qT) and strike B = K exp(−rT):

- Call bounds: max(A−B, 0) ≤ C < A for finite positive IV.
- Put bounds: max(B−A, 0) ≤ P < B for finite positive IV.

The diagnostic solver rejects nonfinite/impossible inputs before solving.
An exact lower bound returns a zero-volatility-limit diagnostic; the chain
excludes it because rounded deep ITM/OTM prices may not identify IV. The upper
bound is excluded. Brent brackets from 0 to 1 decimal IV, doubling the upper
endpoint up to 64 (6400%) as needed, with `xtol=rtol=1e-12`. Failures return
status/message rather than a fabricated volatility. Direct-IV mode bypasses
inversion and labels the resulting option price as a model price.

The empirical smile selects puts below F = S exp((r−q)T) and calls at/above F;
the other type is a fallback only when the preferred quote is absent. Calls and
puts can be displayed separately in the smile view. ATM here explicitly means
K/S = 1, not forward ATM. IV at K/S = 0.9 and 1.1 uses linear interpolation in
moneyness. 25-delta IV uses linear interpolation in **signed spot delta** within
each option type, using q in BSM. No extrapolation is performed; unavailable
targets show N/A, and observed/interpolated methods are exported.

RR25 = Call25 IV − Put25 IV; Put Skew is its negative. Downside/upside measures
are IV90−IVATM and IV110−IVATM. Differences shown in vol points multiply decimal
differences by 100. The term table shows ATM IV and changes between available
expiries. A range ≤0.5 vol points is approximately flat; otherwise successive
changes with a 0.1-point tolerance classify upward/downward, or mixed. Fewer
than two usable maturities is explicitly insufficient. These are descriptions,
not trading signals.

The default heatmap and optional Plotly surface use empirical observations,
with missing cells left blank. This is not an arbitrage-free fitted surface.
SVI is deliberately deferred; the empirical view avoids presenting an untested
calibration as a pricing model.

## Cash Greeks, scenarios and hedge

Let U = signed contracts × units per contract. BSM Greeks are per underlying
unit; long vanilla Gamma and Vega are nonnegative, but position signs follow U.

- Position Delta = U Δ; cash Delta = U Δ S (currency exposure).
- Position Gamma = U Γ; cash Gamma = U Γ S².
- Gamma P&L for a 1% spot move = ½ cash Gamma × 0.01².
- Position Vega = U × raw Vega / 100, per **one vol point**.
- Theta = U × calendar-time Theta / 365, per calendar day elapsed.
- Rho = U × raw Rho / 100, per **100 bp**, not per bp.

For spot return x, decimal IV shock v, elapsed days d and rate shock b bp:

`approx = U × [Δ(Sx) + 0.5 Γ(Sx)² + Vega_1pt(100v)
               + Theta_daily d + Rho_1pct(b/100)]`.

Full P&L is U times the shocked BSM price minus the base price. Shocked inputs
are S(1+x), sigma+v, T−d/365 and r+b/10000. If a curve twist is present, b is the
parallel shift plus the twist interpolated at the option's initial maturity.
Residual = full − approximate P&L; it includes omitted cross terms and higher
orders, and is not automatically a bug. Expiry-crossing and nonpositive shocked
IV are rejected visibly. The matrix varies spot and IV alone, holding rates and
time fixed, with a zero-shock marker. Invalid IV cells are explicitly flagged.
Matrix ranges are saved and used by the export.

The static hedge holds −UΔ underlying units. Hedge cash value = units × S;
underlying P&L = hedge units × (S_new−S). Net P&L adds full option repricing.
New net Delta = new option Delta + existing hedge; rebalance units = −new net
Delta. Gamma, Vega and Theta remain. The separate hedge controls apply an
instantaneous spot/IV shock with zero elapsed time and unchanged rates. No
transaction costs, funding or dividend cash flows are claimed. The older
path-hedging experiment remains available in legacy tools but is not required
for this new workflow.

Delta/Gamma/Vega maps use the same per-unit analytical Greeks, changing spot
and maturity only. This is a small deterministic grid, not Monte Carlo.

## Direct zero curves and rates risk

The table requires tenor in years, `market_rate` in decimals, and `rate_type`
equal to `zero`. Zero rates are continuously compounded, interpolated linearly
in tenor, with constant endpoints. Par yields are rejected rather than silently
treated as zero rates. Discount factor D(t)=exp(−z(t)t), D(0)=1.
The continuous interval forward is ln[D(a)/D(b)]/(b−a). Negative rates are
allowed; monotonic discount factors are not imposed universally. 2s10s/5s30s
are long-minus-short zero rates in bp, using interpolation only inside the
quoted tenor span; otherwise they are N/A.

Shocks are numerical, reusable `MarketScenario` values:

- Parallel ±25/±50 bp.
- Bear steepener: 2Y +10 bp, 10Y +40 bp.
- Bull steepener: 2Y −40 bp, 10Y −10 bp.
- Bear flattener: 2Y +40 bp, 10Y +10 bp.
- Bull flattener: 2Y −10 bp, 10Y −40 bp.
- Custom twist: editable 2Y/10Y/30Y shifts.

Twist shifts interpolate linearly, remain flat outside their nodes, and add to
the parallel shift. Shock knots are unioned with curve knots so kinks between
quoted pillars are preserved. EQD and Curves share the rate/twist fields; other
fields do not change the curve-only valuation. The old whole-book stress engine
is retained as a separate, clearly labelled portfolio workflow.

For actual supplied signed cash flows, PV = Σ CF(t)D(t). Full curve P&L reprices
all flows. Bucket DV01 = [PV(node−1 bp)−PV(node+1 bp)]/2. Parallel DV01 applies
the same central difference to every node; bucket totals reconcile to the
parallel measure within finite-bump error. Positive DV01 means loss for rising
rates. Duration contribution = t × PV(flow)/PV(total), in years. Zero-valued
examples use zero contributions to avoid division by zero.

The UI uses a separately labelled illustrative semiannual coupon bond valued
on a coupon date, with no accrued interest, credit or funding. It does not
reinterpret book clean prices or YTMs. Existing book key-rate ladders and
carry/roll remain: carry approximates value × pricing yield × horizon; roll
uses −DV01 × the yield change from moving down an unchanged observed curve.
These are educational approximations. A par/OIS bootstrap is deferred.

## Portfolio attribution, correlations and PCA

For weights w, covariance C and per-observation volatility s=√(wᵀCw):

`marginal_vol_i = (Cw)_i/s; component_vol_i = w_i marginal_vol_i`.

Percentage risk = component_vol/s (fractions sum to 1 when s>0; individual
values may be negative or exceed 1). Zero-risk portfolios return zero
contributions. At confidence c and horizon h observations, zero-mean Gaussian
VaR = Φ⁻¹(c)s√h; marginal/component VaR scale the corresponding volatility
contribution by Φ⁻¹(c)√h. Components sum to VaR. V1 uses return observations and
weights; V2 uses base-currency position P&Ls and unit weights with its selected
covariance estimator. Captions distinguish these units. These numbers do not
allocate historical VaR/CVaR, which retain their existing sample-based methods.

The correlation control is a signed **blend**, not an additive rho shock.
For a≥0, C'=(1−a)C+a ssᵀ, where s contains individual standard deviations;
for a<0, C'=(1−|a|)C+|a|diag(C). Both preserve variances and positive
semidefiniteness. Negative blend moves toward independence, not all −1
correlations. The shared scenario records this blend explicitly.

Covariance PCA orders eigenpairs by descending eigenvalue, with deterministic
signs for reproducibility. Explained variance λ/Σλ is distinct from portfolio
variance share λ(vᵀw)²/(wᵀCw). Tables include cumulative explained variance and
portfolio component exposure vᵀw. Components are statistical directions;
they are not automatically named economic factors. Existing curve PCA remains.

## Reports, validation and limits

One lab workbook contains original chain inputs and rejected rows, accepted
quotes, empirical surface observations, smile methods/metrics, term data,
cash Greeks, scenario parts/full/residual, spot/vol matrix, hedge inputs/results,
zero-curve and illustrative-bond inputs, forwards, cash flows, nodal DV01 and
the last risk snapshot. Sources and methodology are separate sheets. Workbook
generation uses the shared writer with formula/URL auto-detection disabled,
so user CSV strings beginning with `=` remain strings.

Validation combines analytical identities, finite differences, deterministic
examples and Streamlit AppTest flows. `test_eqd_engines.py` covers IV recovery,
bounds, missing observations, signed scaling, local/full P&L, zero shocks and
hedge identities. `test_curve_risk_extensions.py` covers discount/forward
identities, shock knots, DV01, PSD stress, Euler sums and PCA reconciliation.
`test_eqd_integration.py` covers V1/V2, EN/FR, every main EQD view, navigation,
quote loading, price workflow, invalid scenarios, persistence, language changes
and workbook consistency. The existing Python/R/JavaScript suite is retained.
See the [checkpoint ledger](eqd_upgrade_progress.md) for run results.

No paid API is required. European BSM excludes American exercise and calibrated
stochastic volatility. Synthetic samples are not evidence of historical returns
or investment performance. Gaussian VaR assumes a distribution and square-root
time scaling; it does not bound losses. Monte Carlo structured pricing retains
its documented sampling/model limitations. No optimization, backtesting, XVA,
trading automation or LLM recommendations were introduced.

Method references: [SciPy Brent solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html),
[Tasche on Euler allocation](https://arxiv.org/abs/0708.2542), and
[Options Industry Council: volatility and Greeks](https://prd-web.optionseducation.org/advancedconcepts/volatility-the-greeks).
