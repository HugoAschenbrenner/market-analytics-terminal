"""Key-rate bumps of the audited cashflows, carry proxies and DV01-neutral trades."""
from datetime import timedelta
import numpy as np
import pandas as pd
from engines.fixed_income_engine import build_remaining_contractual_cashflows,calculate_dirty_price_from_ytm

TENORS=np.array([1,2,5,10,30.])

def key_rate_ladder(bonds,state):
    rows=[]
    for row in bonds.itertuples():
        _,cf,exponents=build_remaining_contractual_cashflows(row.coupon,2,state.valuation_date-timedelta(days=366),row.maturity_date,state.valuation_date)
        weights=np.array([np.interp(exponents/2,TENORS,np.eye(5)[i]) for i in range(5)])
        y=row.pricing_yield
        scale=row.quantity/100*state.market.fx[row.currency]/state.market.fx[state.book.base_currency]
        values=[]
        for w in weights:
            down=np.sum(cf/(1+(y-1e-4*w)/2)**exponents)
            up=np.sum(cf/(1+(y+1e-4*w)/2)**exponents)
            values.append((down-up)/2*scale)
        rows.append(dict(id=row.id,currency=row.currency,**{str(int(t)):v for t,v in zip(TENORS,values)}))
    return pd.DataFrame(rows,columns=['id','currency',*[str(int(t)) for t in TENORS]])

def carry_roll(bonds,curves,horizon=.25):
    rows=[]
    for row in bonds.itertuples():
        if row.currency not in curves:
            rows.append({'id':row.id,'carry':row.market_value*row.pricing_yield*horizon,'roll':np.nan});continue
        curve=curves[row.currency]['history'].iloc[-1]
        roll_bps=(np.interp(max(.01,row.maturity-horizon),curve.index,curve.values)-np.interp(row.maturity,curve.index,curve.values))*100
        rows.append({'id':row.id,'carry':row.market_value*row.pricing_yield*horizon,'roll':-row.dv01*roll_bps})
    return pd.DataFrame(rows)

def yield_price_curve(row,state):
    _,cf,exponents=build_remaining_contractual_cashflows(row.coupon,2,state.valuation_date-timedelta(days=366),row.maturity_date,state.valuation_date)
    yields=np.linspace(max(-.5,row.pricing_yield-.03),row.pricing_yield+.03,61)
    return pd.DataFrame({'yield':yields*100,'price':[calculate_dirty_price_from_ytm(cf,exponents,y,2) for y in yields]})

def reference_dv01(tenor,yield_rate,valuation_date):
    maturity=pd.Timestamp(valuation_date)+pd.DateOffset(years=int(tenor))
    _,cf,exponents=build_remaining_contractual_cashflows(yield_rate,2,valuation_date,maturity,valuation_date)
    lower=calculate_dirty_price_from_ytm(cf,exponents,yield_rate-1e-4,2)
    upper=calculate_dirty_price_from_ytm(cf,exponents,yield_rate+1e-4,2)
    return (lower-upper)/200  # currency DV01 per one unit of nominal

def curve_trade(tenors,yields,notional,valuation_date,view='steepener'):
    tenors=np.asarray(tenors,float);yields=np.asarray(yields,float)
    if len(tenors) not in (2,3) or len(yields)!=len(tenors) or not np.isfinite([*tenors,*yields,notional]).all() or notional<=0 or (np.diff(tenors)<=0).any():
        raise ValueError('Invalid curve trade inputs')
    dv=np.array([reference_dv01(t,y,valuation_date) for t,y in zip(tenors,yields)])
    if len(tenors)==2:
        if view not in ('steepener','flattener'):raise ValueError('Invalid curve view')
        quantities=np.array([notional,-notional*dv[0]/dv[1]])*(1 if view=='steepener' else -1)
    else:
        left=(tenors[2]-tenors[1])/(tenors[2]-tenors[0]);right=1-left
        target=np.array([left,-1,right])*notional*dv[1]
        quantities=target/dv
    legs=pd.DataFrame({'tenor':tenors,'notional':quantities,'dv01':quantities*dv})
    shape=np.linspace(-20,20,len(tenors))
    curvature=np.zeros(len(tenors));curvature[len(tenors)//2]=20
    shocks={'parallel':np.ones(len(tenors))*25,'steepener':shape,'flattener':-shape,'curvature':curvature}
    pnl=pd.DataFrame([{'scenario':k,'pnl':float(-legs.dv01@shock)} for k,shock in shocks.items()])
    return {'legs':legs,'scenarios':pnl}
