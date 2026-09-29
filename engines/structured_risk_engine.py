"""Controlled Monte Carlo proxies using the audited GBM observation schedule.

Current spot is bumped relative to fixed contractual initial fixings. Replacing
both spot and fixing would cancel Delta and is deliberately never done here.
"""
from dataclasses import asdict,replace
from functools import lru_cache
import numpy as np
import pandas as pd
from engines.structured_products_valuation_engine import validate_valuation_inputs,simulate_correlated_gbm_performance_paths,build_observation_times



def correlation_bounds(asset_count):
    """Closed PSD domain for an equicorrelation matrix; n=1 has no parameter."""
    if isinstance(asset_count, bool) or int(asset_count) != asset_count or asset_count < 1:
        raise ValueError('A positive asset count is required.')
    return (-1. / (asset_count - 1), 1.) if asset_count > 1 else (0., 0.)


def validate_note_inputs(inputs):
    """Reuse audited contract checks, extending only V2's correlation domain.

    Bound workload before constructing any observation grid or path array.
    The historical V1 engine deliberately retains its original contract.
    """
    n = len(inputs.initial_spots)
    lower, upper = correlation_bounds(n)
    if not np.isfinite(inputs.correlation) or (n > 1 and not lower <= inputs.correlation <= upper):
        raise ValueError(f'Correlation must be in [{lower:g}, {upper:g}] for {n} names.')
    for value in (inputs.simulations, inputs.observations_per_year):
        if isinstance(value, bool) or not np.isfinite(value) or int(value) != value:
            raise ValueError('Simulation count and observation frequency must be integers.')
    if not 2 <= inputs.simulations <= 20000 or not 1 <= inputs.observations_per_year <= 12:
        raise ValueError('Use 2–20,000 paths and 1–12 observations per year.')
    if not 1 <= n <= 8 or not 0 < inputs.maturity_years <= 30:
        raise ValueError('Use 1–8 names and a maturity up to 30 years.')
    if inputs.simulations * np.ceil(inputs.maturity_years * inputs.observations_per_year) * n > 2_000_000:
        raise ValueError('Workload exceeds two million simulated observation values; reduce paths or frequency.')
    # Zero correlation passes the historical PD restriction for any dimension.
    validated = validate_valuation_inputs(**asdict(replace(inputs, correlation=0.)))
    return replace(validated, correlation=float(inputs.correlation) if n > 1 else 0.)


def correlation_factor(asset_count, correlation):
    """Cholesky factor, including its continuous limits at both PSD endpoints."""
    lower, upper = correlation_bounds(asset_count)
    if not np.isfinite(correlation) or (asset_count > 1 and not lower <= correlation <= upper):
        raise ValueError('Invalid correlation matrix.')
    matrix = np.full((asset_count, asset_count), correlation)
    np.fill_diagonal(matrix, 1.)
    if asset_count == 1 or lower < correlation < upper:
        return np.linalg.cholesky(matrix)
    if correlation == 1.:
        factor = np.zeros_like(matrix); factor[:, 0] = 1.
        return factor
    # At the negative PSD bound only the final pivot vanishes. Build the
    # nonsingular leading block and solve the last row, avoiding jitter.
    factor = np.zeros_like(matrix)
    factor[:-1, :-1] = np.linalg.cholesky(matrix[:-1, :-1])
    factor[-1, :-1] = np.linalg.solve(factor[:-1, :-1], matrix[-1, :-1])
    return factor


def simulate_note_paths(inputs):
    n = len(inputs.initial_spots)
    lower, upper = correlation_bounds(n)
    if n == 1 or lower < inputs.correlation < upper:
        return simulate_correlated_gbm_performance_paths(inputs)
    times = build_observation_times(inputs)
    steps = np.diff(np.r_[0., times])
    factor = correlation_factor(n, inputs.correlation)
    rng = np.random.default_rng(inputs.seed)
    vol = np.asarray(inputs.volatilities)
    drift = inputs.risk_free_rate - inputs.dividend_yield - .5 * vol**2
    log_path = np.zeros((inputs.simulations, n))
    paths = np.empty((inputs.simulations, len(times), n))
    for j, dt in enumerate(steps):
        normals = rng.standard_normal((inputs.simulations, n)) @ factor.T
        log_path += drift * dt + vol * np.sqrt(dt) * normals
        paths[:, j, :] = np.exp(log_path)
    return paths


def cashflows(paths,inputs,product='Athena',memory=True):
    paths=np.asarray(paths,dtype=float);times=build_observation_times(inputs)
    if product not in ('Athena','Phoenix') or paths.ndim!=3 or paths.shape[1]!=len(times) or paths.shape[2]!=len(inputs.initial_spots) or not len(paths) or not np.isfinite(paths).all() or (paths<0).any():raise ValueError('structured.invalid')
    worst=paths.min(axis=2);n=len(paths);alive=np.ones(n,dtype=bool)
    coupon=np.zeros(n);pv=np.zeros(n);redemption=np.zeros(n);event=np.full(n,times[-1]);autocalled=np.zeros(n,dtype=bool);arrears=np.zeros(n)
    dt=np.diff(np.r_[0,times])
    for j,time in enumerate(times):
        call=alive&(worst[:,j]>=inputs.autocall_barrier)
        if product=='Phoenix':
            due=inputs.notional*inputs.coupon_rate*dt[j]
            arrears[alive]+=due
            paid=alive&(worst[:,j]>=inputs.coupon_barrier)
            amount=np.where(paid,arrears if memory else due,0.)
            coupon+=amount;pv+=amount*np.exp(-inputs.risk_free_rate*time);arrears[paid]=0
        else:
            amount=np.where(call,inputs.notional*inputs.coupon_rate*time,0.)
            coupon+=amount;pv+=amount*np.exp(-inputs.risk_free_rate*time)
        redemption[call]=inputs.notional;pv[call]+=inputs.notional*np.exp(-inputs.risk_free_rate*time)
        event[call]=time;autocalled[call]=True;alive[call]=False
    loss=alive&(worst[:,-1]<inputs.protection_barrier)
    redemption[alive]=np.where(loss[alive],inputs.notional*worst[alive,-1],inputs.notional)
    pv[alive]+=redemption[alive]*np.exp(-inputs.risk_free_rate*times[-1])
    if product=='Athena':
        amount=np.where(alive&(worst[:,-1]>=inputs.coupon_barrier),inputs.notional*inputs.coupon_rate*times[-1],0.)
        coupon+=amount;pv+=amount*np.exp(-inputs.risk_free_rate*times[-1])
    return pd.DataFrame(dict(payoff=redemption+coupon,discounted_payoff=pv,coupon_paid=coupon,redemption=redemption,event_time_years=event,autocalled=autocalled,protection_barrier_breached=loss))


@lru_cache(maxsize=16)
def value_note(inputs,ratios,product='Athena',memory=True):
    inputs=validate_note_inputs(inputs)
    ratios=np.asarray(ratios,dtype=float)
    if ratios.shape!=(len(inputs.initial_spots),) or not np.isfinite(ratios).all() or np.any(ratios<=0):raise ValueError('structured.invalid')
    paths=simulate_note_paths(inputs)*ratios[None,None,:]
    flows=cashflows(paths,inputs,product,memory)
    summary=dict(value=float(flows.discounted_payoff.mean()),mc_error=float(flows.discounted_payoff.std(ddof=1)/np.sqrt(len(flows))),autocall_probability=float(flows.autocalled.mean()),loss_probability=float(flows.protection_barrier_breached.mean()),coupon_probability=float((flows.coupon_paid>0).mean()),expected_maturity=float(flows.event_time_years.mean()))
    return dict(summary=summary,cashflows=flows,paths=paths,times=build_observation_times(inputs))


@lru_cache(maxsize=64)
def bump_risk(inputs,ratios,product='Athena',memory=True):
    base=value_note(inputs,ratios,product,memory)['summary']['value']
    spots=np.array(inputs.initial_spots)*ratios;deltas=[]
    def val(i=inputs,r=ratios):return value_note(i,tuple(r),product,memory)['summary']['value']
    for k,s in enumerate(spots):
        up=np.array(ratios);down=np.array(ratios);up[k]*=1.01;down[k]*=.99
        deltas.append((val(r=up)-val(r=down))/(.02*s))
    hv=min(.01,min(inputs.volatilities)*.25);hr=.001
    vega=(val(replace(inputs,volatilities=tuple(v+hv for v in inputs.volatilities)))-val(replace(inputs,volatilities=tuple(v-hv for v in inputs.volatilities))))/(2*hv)*.01
    rho=(val(replace(inputs,risk_free_rate=inputs.risk_free_rate+hr))-val(replace(inputs,risk_free_rate=inputs.risk_free_rate-hr)))/(2*hr)*.01
    n=len(ratios);corr=0.;method='not applicable (one name)'
    if n>1:
        lower,upper=correlation_bounds(n)
        down=max(lower,inputs.correlation-.01);up=min(upper,inputs.correlation+.01)
        corr=(val(replace(inputs,correlation=up))-val(replace(inputs,correlation=down)))/(up-down)*.01
        method='central 1-point bump' if inputs.correlation-.01>=lower and inputs.correlation+.01<=upper else 'bounded one-sided/secant bump'
    return dict(value=base,deltas=tuple(deltas),delta_cash=float(np.dot(deltas,spots)),vega=vega,rho=rho,correlation_1pct=corr,correlation_method=method)
