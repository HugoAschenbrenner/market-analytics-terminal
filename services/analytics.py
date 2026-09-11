"""One book valuation consumed by every workspace; no display-state inputs."""
from datetime import timedelta
import numpy as np
import pandas as pd
import streamlit as st
from core.state import validate_book
from engines import fixed_income_engine as fi
from engines.options_pricing_engine import black_scholes_price, black_scholes_greeks

@st.cache_data(show_spinner=False, max_entries=32)
def calculate_positions(positions, market, valuation_date, contracts=None):
    frame = validate_book(positions)
    rows = []
    for row in frame.to_dict('records'):
        result = dict(row, market_value=0., dv01=0., cs01=0., delta=0., delta_cash=0., gamma=0., vega=0., theta=0., rho=0., duration=0., convexity=0.)
        units = row['quantity'] * row['multiplier']
        price = row['price']
        result['mark_source']='USER INPUT'
        if row['asset_class']=='Equity' and row['mark_mode']=='Market':
            if row['ticker'] not in market.spots:raise ValueError('book.underlying')
            price=market.spots[row['ticker']]
            result['mark_source']=market.provenance.get(row['ticker'],{}).get('source','SYNTHETIC')
        if row['asset_class'] in ['Option','Structured']:result['mark_source']='MODEL'
        if row['asset_class'] == 'Bond' and row['quantity'] != 0:
            contract = dict(bond_id=row['id'], issuer=row['ticker'], currency=row['currency'], coupon_rate=row['coupon'],
                issue_date=valuation_date-timedelta(days=366), maturity_date=valuation_date+timedelta(days=round(365*row['maturity'])),
                frequency=2, clean_price=price, yield_to_maturity=row['yield_rate'], notional=abs(row['quantity']),
                rating='A' if row['sleeve']=='Credit' else 'AAA', sector='Corporate' if row['sleeve']=='Credit' else 'Government',
                spread_bps=100 if row['sleeve']=='Credit' else 0, curve_bucket=f"{row['maturity']:g}Y")
            r = fi.calculate_bond_risk_metrics(pd.DataFrame([contract]), valuation_date).iloc[0]
            result.update(r.to_dict())
            sign = np.sign(row['quantity'])
            price = r.dirty_price
            result.update(dv01=sign*r.dv01, cs01=sign*r.cs01, duration=r.modified_duration, convexity=r.convexity,
                clean_price=row['price'], accrued=r.accrued_interest_per_100, pricing_yield=r.pricing_yield_used,
                price_error=r.clean_price_reconciliation_error, day_count='ACT/ACT', maturity_date=r.maturity_date)
        elif row['asset_class'] == 'Option':
            if row['underlying'] not in market.spots:
                raise ValueError('book.underlying')
            spot = market.spots[row['underlying']]
            rate = market.rates[row['currency']]
            args = (row['option_type'], spot, row['strike'], row['maturity'], rate, row['volatility'])
            price = black_scholes_price(*args)
            g = black_scholes_greeks(*args)
            result.update(spot=spot, delta=g['delta']*units, delta_cash=g['delta']*units*spot,
                          gamma=g['gamma']*units, vega=g['vega_1pct']*units,
                          theta=g['theta_daily']*units, rho=g['rho_1pct']*units)
        elif row['asset_class'] == 'Structured':
            from services.structured import note_value
            valuation,risk=note_value(row,market,contracts or {})
            price=risk['value']
            result.update(delta_cash=risk['delta_cash']*units,vega=risk['vega']*units,rho=risk['rho']*units,correlation_1pct=risk['correlation_1pct']*units,autocall_probability=valuation['summary']['autocall_probability'],loss_probability=valuation['summary']['loss_probability'])
        elif row['asset_class'] == 'Equity':
            result.update(delta=units, delta_cash=units*price)
        result.update(mark=price, market_value=price*units)
        rows.append(result)
    return pd.DataFrame(rows)

def marked_positions(state):
    frame = calculate_positions(state.book.positions, state.market, state.valuation_date, state.book.structured_terms)
    fx = frame.currency.map(state.market.fx) / state.market.fx[state.book.base_currency]
    for col in ('market_value','dv01','cs01','delta_cash','gamma','vega','theta','rho'):
        frame[col] *= fx
    if 'correlation_1pct' in frame:frame['correlation_1pct'] *= fx
    frame['gamma_cash_1pct']=.5*frame.gamma*frame.get('spot',pd.Series(0.,index=frame.index)).fillna(0.)**2*.0001
    if frame.weight.notna().any():
        values = frame.market_value
        if values.sum() <= 0 or not np.allclose(frame.weight, values/values.sum(), atol=1e-5):
            raise ValueError('book.weights')
    return frame

def nav(state, marks):
    value = float(marks.market_value.sum() - state.book.repo_cash)
    if value <= 0:
        raise ValueError('book.nav')
    return value
