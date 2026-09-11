"""Synthetic risk history driven by current signed exposures, distinct from public context."""
import hashlib
import numpy as np
import pandas as pd
import streamlit as st
from engines.portfolio_risk_engine import calculate_drawdown_series
from services.analytics import marked_positions,nav

@st.cache_data(show_spinner=False,max_entries=16)
def synthetic_pnl_history(marks,base_currency="USD"):
    rng=np.random.default_rng(731)
    factors=rng.normal(size=(756,5))
    data={}
    for row in marks.itertuples():
        seed=int.from_bytes(hashlib.sha256(str(row.underlying if row.asset_class=='Option' else row.ticker).encode()).digest()[:4],'little')
        idio=np.random.default_rng(seed).normal(size=756)
        eq=(.8*factors[:,0]+.6*idio)*.012
        rate=factors[:,1]*5
        fx=factors[:,2]*.006
        vol=(-.5*factors[:,0]+.866*factors[:,3])*.6
        pnl=np.zeros(756)
        if row.asset_class=='Equity': pnl=row.market_value*eq
        elif row.asset_class=='Bond': pnl=-row.dv01*rate-row.cs01*factors[:,4]*3
        elif row.asset_class=='Option': pnl=row.delta_cash*eq+.5*row.gamma*(row.spot*eq)**2+row.vega*vol
        elif row.asset_class=='Structured': pnl=row.market_value*(.55*eq-.002*vol)
        if row.currency!=base_currency: pnl+=row.market_value*fx
        data[row.id]=pnl
    return pd.DataFrame(data,index=pd.bdate_range(end='2026-09-09',periods=756))

def book_risk(state):
    marks=marked_positions(state)
    pnl=synthetic_pnl_history(marks,state.book.base_currency)
    value=nav(state,marks)
    total=pnl.sum(axis=1)
    returns=total/value
    quantile=total.quantile(1-state.risk.confidence)
    var=max(0.,-quantile)
    es=max(0.,-total[total<=quantile].mean())
    covariance=pnl.cov().to_numpy()
    sigma=np.sqrt(max(0.,covariance.sum()))
    contrib=covariance.sum(axis=1)/sigma if sigma else np.zeros(len(marks))
    return dict(marks=marks,pnl=pnl,total=total,nav=value,returns=returns,var=var,es=es,
                volatility=float(returns.std()*np.sqrt(252)),drawdown=calculate_drawdown_series(returns),
                contributions=pd.DataFrame({'id':pnl.columns,'contribution':contrib*np.sqrt(252)/value}))
