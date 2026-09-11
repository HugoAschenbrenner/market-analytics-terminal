"""Controlled Monte Carlo proxies using the audited GBM observation schedule.

Current spot is bumped relative to fixed contractual initial fixings. Replacing
both spot and fixing would cancel Delta and is deliberately never done here.
"""
from dataclasses import asdict,replace
from functools import lru_cache
import numpy as np
import pandas as pd
from engines.structured_products_valuation_engine import validate_valuation_inputs,simulate_correlated_gbm_performance_paths,build_observation_times


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


@lru_cache(maxsize=128)
def value_note(inputs,ratios,product='Athena',memory=True):
    inputs=validate_valuation_inputs(**asdict(inputs))
    ratios=np.asarray(ratios,dtype=float)
    if ratios.shape!=(len(inputs.initial_spots),) or not np.isfinite(ratios).all() or np.any(ratios<=0):raise ValueError('structured.invalid')
    paths=simulate_correlated_gbm_performance_paths(inputs)*ratios[None,None,:]
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
    n=len(ratios);corr=0.
    if n>1:
        hc=min(.01,(inputs.correlation+1/(n-1))*.25,(1-inputs.correlation)*.25)
        corr=(val(replace(inputs,correlation=inputs.correlation+hc))-val(replace(inputs,correlation=inputs.correlation-hc)))/(2*hc)*.01
    return dict(value=base,deltas=tuple(deltas),delta_cash=float(np.dot(deltas,spots)),vega=vega,rho=rho,correlation_1pct=corr)
