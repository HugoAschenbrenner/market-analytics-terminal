import numpy as np
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from engines.options_pricing_engine import black_scholes_price as price,black_scholes_greeks as greeks
from engines.pnl_explain_engine import advanced_greeks,implied_volatility,pnl_explain,simulate_hedge,fx_vol_quotes

@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('s,t,q',[(100.,1.,0.),(1.1,.1,.03),(75.,2.,.02)])
def test_advanced_greeks_finite_differences(kind,s,t,q):
    k=s*1.03;r=.04;v=.23;h=1e-4
    a=advanced_greeks(kind,s,k,t,r,v,q)
    g=lambda v=v,t=t:greeks(kind,s,k,t,r,v,q)
    assert a['vanna']==pytest.approx((g(v=v+h)['delta']-g(v=v-h)['delta'])/(2*h),rel=2e-5,abs=2e-6)
    assert a['volga']==pytest.approx((g(v=v+h)['vega_1pct']-g(v=v-h)['vega_1pct'])/(2*h)*100,rel=3e-5,abs=1e-5)
    assert a['charm']==pytest.approx(-(g(t=t+h)['delta']-g(t=t-h)['delta'])/(2*h),rel=2e-5,abs=2e-6)

@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('s,k,t,v',[(100,105,1,.2),(1.1,1.09,.01,.3),(100,100,1e-5,.4),(100,100,3,1.7)])
def test_iv_recovery(kind,s,k,t,v):
    p=price(kind,s,k,t,.04,v,.01)
    assert implied_volatility(p,kind,s,k,t,.04,.01)==pytest.approx(v,abs=1e-7)

@pytest.mark.parametrize('observed',[-1,100,float('nan'),float('inf')])
def test_iv_bounds(observed):
    with pytest.raises(ValueError):implied_volatility(observed,'Call',100,100,1,0)

def test_explain_reconciliation_and_small_shock_accuracy():
    r=pnl_explain('Call',100,100,1,.04,.2,ds=.1,dv=.0001,days=.01,dr=.00001,units=-100)
    assert sum(r['parts'].values())==pytest.approx(r['full'])
    assert abs(r['parts']['residual'])<.001
    assert pnl_explain('Put',100,90,1,.02,.3)['full']==0

@pytest.mark.parametrize('kind',['Call','Put','Straddle'])
def test_hedge_is_self_financing_with_costs_and_dividends(kind):
    result=simulate_hedge(kind,100,100,1,.04,.2,.25,steps=100,frequency=5,cost_bps=3,dividend=.02)
    p=result['path']
    assert p.total.to_numpy()==pytest.approx((p.option_pnl+p.hedge_pnl+p.funding-p.costs).to_numpy(),abs=1e-10)
    assert p.iloc[-1].delta_hedge==0
    assert p.costs.is_monotonic_increasing
    assert result['hedge_error']==p.iloc[-1].total
    assert result['realized_vol']>0

def test_hedge_frequency_and_cost_effect():
    a=simulate_hedge('Call',100,100,1,0,.2,.2,cost_bps=0)
    b=simulate_hedge('Call',100,100,1,0,.2,.2,cost_bps=10)
    assert a['hedge_error']-b['hedge_error']==pytest.approx(b['path'].iloc[-1].costs)
    assert fx_vol_quotes(.2,.02,.005)==pytest.approx(dict(atm=.2,call25=.215,put25=.195))

@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('main,sub',[('vanilla','option.price'),('vanilla','pnl_explain'),('vanilla','hedge.sim'),('greeks',None),('volatility',None)])
def test_derivative_tabs_render(lang,main,sub):
    from core.i18n import TRANSLATIONS
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page='derivatives',lang=lang)
    app.session_state['derivative_tabs']=TRANSLATIONS[lang][main]
    if sub:app.session_state['vanilla_tabs']=TRANSLATIONS[lang][sub]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0
