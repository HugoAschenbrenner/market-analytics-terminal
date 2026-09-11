"""Domestic currency per unit of foreign currency; continuously compounded rates."""
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from engines.options_pricing_engine import black_scholes_price,black_scholes_greeks

def fx_forward(spot,domestic_rate,foreign_rate,maturity,pip=.0001):
    values=np.array([spot,domestic_rate,foreign_rate,maturity,pip],float)
    if not np.isfinite(values).all() or spot<=0 or maturity<0 or pip<=0:
        raise ValueError('Invalid FX forward inputs')
    forward=spot*np.exp((domestic_rate-foreign_rate)*maturity)
    if not np.isfinite(forward):raise ValueError('Forward overflow')
    return {'forward':float(forward),'points':float((forward-spot)/pip),'carry':float(forward/spot-1)}

def cross_rate(usd_values,foreign,domestic):
    a,b=float(usd_values[foreign]),float(usd_values[domestic])
    if not np.isfinite([a,b]).all() or min(a,b)<=0:raise ValueError('Invalid currency values')
    return a/b

def garman_kohlhagen(option_type,spot,strike,maturity,domestic_rate,foreign_rate,volatility):
    args=(option_type,spot,strike,maturity,domestic_rate,volatility,foreign_rate)
    price=black_scholes_price(*args);greeks=black_scholes_greeks(*args)
    return dict(price=price,**greeks,foreign_rho_1pct=-maturity*spot*greeks['delta']/100)

def fx_swap_points(spot,domestic_rate,foreign_rate,near,far,pip=.0001):
    if near>far:raise ValueError('Near date must precede far date')
    return (fx_forward(spot,domestic_rate,foreign_rate,far,pip)['forward']-fx_forward(spot,domestic_rate,foreign_rate,near,pip)['forward'])/pip

def client_hedges(spot,domestic_rate,foreign_rate,maturity,volatility,notional=1e6,client='exporter',outcomes=None):
    if client not in ('exporter','importer') or not np.isfinite(notional) or notional<=0:
        raise ValueError('Invalid corporate exposure')
    f=fx_forward(spot,domestic_rate,foreign_rate,maturity)['forward']
    sign=1 if client=='exporter' else -1
    option_type='Put' if sign==1 else 'Call'
    option_strike=f
    price=lambda kind,k:black_scholes_price(kind,spot,k,maturity,domestic_rate,volatility,foreign_rate)
    premium=price(option_type,option_strike)
    premium_fv=premium*np.exp(domestic_rate*maturity)
    s=np.linspace(.6*spot,1.4*spot,121) if outcomes is None else np.asarray(outcomes,dtype=float)
    if not np.isfinite(s).all() or (s<=0).any():raise ValueError('Terminal spots must be finite and positive')
    option_payoff=np.maximum(sign*(option_strike-s),0)
    flows=pd.DataFrame({'spot':s,'unhedged':sign*notional*s,'forward':np.full(len(s),sign*notional*f),
                        'option':sign*notional*s+notional*(option_payoff-premium_fv)})
    details=[dict(strategy='unhedged',protected_rate=np.nan,upfront_premium=0.,breakeven=np.nan,participation_limit=np.nan),
             dict(strategy='forward',protected_rate=f,upfront_premium=0.,breakeven=f,participation_limit=f),
             dict(strategy='option',protected_rate=f-sign*premium_fv,upfront_premium=premium*notional,breakeven=f-sign*premium_fv,participation_limit=np.nan)]
    collar=None
    try:
        if sign==1:
            lower=.95*f;target=price('Put',lower)
            if target<=1e-12:raise ValueError('Degenerate collar')
            upper=brentq(lambda k:price('Call',k)-target,f,spot*20)
        else:
            upper=1.05*f;target=price('Call',upper)
            if target<=1e-12:raise ValueError('Degenerate collar')
            lower=brentq(lambda k:price('Put',k)-target,spot*1e-6,f)
        collar={'lower':lower,'upper':upper,'net_premium':price('Put',lower)-price('Call',upper)}
        flows['collar']=sign*notional*np.clip(s,lower,upper)
        details.append(dict(strategy='collar',protected_rate=lower if sign==1 else upper,upfront_premium=0.,breakeven=np.nan,participation_limit=upper if sign==1 else lower))
    except ValueError:
        pass  # A zero-cost collar is only offered when a valid strike bracket exists.
    return {'flows':flows,'details':pd.DataFrame(details),'collar':collar,'forward':f}
