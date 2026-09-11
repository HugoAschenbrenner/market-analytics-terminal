"""European option risk. Volatility/rates use decimals; time uses ACT/365 years."""
from math import exp, sqrt, isfinite
import numpy as np
import pandas as pd
from engines.options_pricing_engine import black_scholes_price as price, black_scholes_greeks as greeks, calculate_d1_d2, norm_pdf, validate_black_scholes_inputs


def advanced_greeks(kind, spot, strike, maturity, rate, vol, dividend=0.):
    validate_black_scholes_inputs(kind,spot,strike,maturity,rate,vol,dividend)
    d=calculate_d1_d2(spot,strike,maturity,rate,vol,dividend);d1,d2=d['d1'],d['d2']
    g=greeks(kind,spot,strike,maturity,rate,vol,dividend)
    density=exp(-dividend*maturity)*norm_pdf(d1)
    return dict(vanna=-density*d2/vol,volga=spot*density*sqrt(maturity)*d1*d2/vol,
        charm=dividend*g['delta']-density*(2*(rate-dividend)*maturity-d2*vol*sqrt(maturity))/(2*maturity*vol*sqrt(maturity)))


def implied_volatility(observed, kind, spot, strike, maturity, rate, dividend=0.):
    inputs=validate_black_scholes_inputs(kind,spot,strike,maturity,rate,.2,dividend)
    if not isfinite(observed):raise ValueError('iv.bounds')
    s=spot*exp(-dividend*maturity);k=strike*exp(-rate*maturity)
    lower=max(0.,s-k) if inputs.option_type=='Call' else max(0.,k-s)
    upper=s if inputs.option_type=='Call' else k
    if observed<lower or observed>=upper:raise ValueError('iv.bounds')
    if observed==lower:return 0.
    lo,hi=0.,1.
    while price(kind,spot,strike,maturity,rate,hi,dividend)<observed and hi<64:hi*=2
    if price(kind,spot,strike,maturity,rate,hi,dividend)<observed:raise ValueError('iv.convergence')
    for _ in range(180):
        mid=(lo+hi)/2
        if price(kind,spot,strike,maturity,rate,mid,dividend)<observed:lo=mid
        else:hi=mid
        if hi-lo<1e-10:return (hi+lo)/2
    raise ValueError('iv.convergence')


def pnl_explain(kind,spot,strike,maturity,rate,vol,ds=0.,dv=0.,days=0.,dr=0.,units=1.,dividend=0.,advanced=True):
    if not all(isfinite(x) for x in (ds,dv,days,dr,units)) or days<0 or days/365>=maturity:raise ValueError('explain.invalid')
    args=(kind,spot,strike,maturity,rate,vol,dividend)
    base=price(*args);g=greeks(*args);a=advanced_greeks(*args)
    full=(price(kind,spot+ds,strike,maturity-days/365,rate+dr,vol+dv,dividend)-base)*units
    parts=dict(delta=g['delta']*ds,gamma=.5*g['gamma']*ds*ds,vega=g['vega_1pct']*100*dv,
        theta=g['theta_daily']*days,rates=g['rho_1pct']*100*dr,
        vanna=a['vanna']*ds*dv if advanced else 0.,volga=.5*a['volga']*dv*dv if advanced else 0.)
    parts={k:v*units for k,v in parts.items()};approx=sum(parts.values());parts['residual']=full-approx
    return dict(parts=parts,full=full,approximation=approx)


def volatility_surface(atm=.2,skew=-.08,curvature=.12,term=.015):
    if atm<=0 or not all(isfinite(x) for x in (atm,skew,curvature,term)):raise ValueError('iv.bounds')
    times=np.array([.05,.10,.25,.5,1.,2.,3.]);m=np.linspace(.65,1.35,31)
    x=np.log(m)
    surface=np.maximum(.01,atm+skew*x[None,:]+curvature*x[None,:]**2+term*(np.sqrt(times[:,None])-1))
    return m,times,surface


def fx_vol_quotes(atm,rr,bf):
    vols=dict(atm=atm,call25=atm+bf+rr/2,put25=atm+bf-rr/2)
    if not all(isfinite(v) and v>0 for v in vols.values()):raise ValueError('iv.bounds')
    return vols


def simulate_hedge(kind,spot,strike,maturity,rate,implied,realized,steps=252,frequency=1,cost_bps=1.,seed=42,path=None,dividend=0.):
    """Long option/straddle, self-financing short delta; terminal liquidation included."""
    kinds=['Call','Put'] if kind=='Straddle' else [kind]
    for k in kinds:validate_black_scholes_inputs(k,spot,strike,maturity,rate,implied,dividend)
    if not isfinite(realized) or realized<0 or not isfinite(cost_bps) or cost_bps<0 or frequency<1 or int(frequency)!=frequency or steps<2:raise ValueError('hedge.invalid')
    if path is None:
        dt=maturity/steps;z=np.random.default_rng(seed).normal(size=steps)
        path=spot*np.exp(np.r_[0,np.cumsum((rate-dividend-.5*realized**2)*dt+realized*sqrt(dt)*z)])
    else:
        path=np.asarray(path,dtype=float)
        if len(path)<3 or not np.all(np.isfinite(path)) or np.any(path<=0) or not np.isclose(path[0],spot):raise ValueError('hedge.invalid')
        steps=len(path)-1;dt=maturity/steps
    value=lambda s,t:sum(price(k,s,strike,t,rate,implied,dividend) for k in kinds) if t>1e-12 else sum(max(s-strike,0) if k=='Call' else max(strike-s,0) for k in kinds)
    delta=lambda s,t:sum(greeks(k,s,strike,t,rate,implied,dividend)['delta'] for k in kinds)
    initial=value(spot,maturity);shares=-delta(spot,maturity)
    cost=abs(shares)*spot*cost_bps/10000;cash=-initial-shares*spot-cost
    hedge_pnl=0.;funding=0.;records=[]
    records.append(dict(time=0.,spot=spot,option_pnl=0.,hedge_pnl=0.,funding=0.,costs=cost,total=-cost,delta_hedge=shares))
    for i in range(1,steps+1):
        s=path[i];old=path[i-1];remaining=max(0.,maturity-i*dt)
        interest=cash*np.expm1(rate*dt);div=shares*old*np.expm1(dividend*dt)
        cash+=interest+div;funding+=interest;hedge_pnl+=shares*(s-old)+div
        option=value(s,remaining)
        if i==steps or i%frequency==0:
            target=0. if i==steps else -delta(s,remaining)
            trade=target-shares;fee=abs(trade)*s*cost_bps/10000
            cash-=trade*s+fee;cost+=fee;shares=target
        total=option+shares*s+cash
        records.append(dict(time=i*dt,spot=s,option_pnl=option-initial,hedge_pnl=hedge_pnl,funding=funding,costs=cost,total=total,delta_hedge=shares))
    return dict(path=pd.DataFrame(records),realized_vol=float(np.std(np.diff(np.log(path)),ddof=1)/sqrt(dt)),hedge_error=float(records[-1]['total']))
