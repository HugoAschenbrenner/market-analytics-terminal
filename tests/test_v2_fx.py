from datetime import date
from pathlib import Path
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
from engines.fx_engine import fx_forward,fx_swap_points,cross_rate,garman_kohlhagen,client_hedges
from engines.rates_tools_engine import curve_trade

def test_forward_cip_cross_rate_and_swap_identities():
    assert fx_forward(1.1,.05,.03,2)['forward']==pytest.approx(1.1*np.exp(.04))
    assert fx_forward(1.1,.03,.03,1)['points']==0
    assert fx_swap_points(1.1,.05,.03,0,1)==pytest.approx(fx_forward(1.1,.05,.03,1)['points'])
    values={'USD':1,'EUR':1.1,'GBP':1.3}
    assert cross_rate(values,'EUR','GBP')*cross_rate(values,'GBP','USD')==pytest.approx(cross_rate(values,'EUR','USD'))

@pytest.mark.parametrize('kind',['Call','Put'])
def test_gk_greeks_match_finite_differences(kind):
    s,k,t,rd,rf,v=1.1,1.15,.75,.04,.02,.15
    price=lambda s=s,t=t,rd=rd,rf=rf,v=v:garman_kohlhagen(kind,s,k,t,rd,rf,v)['price']
    g=garman_kohlhagen(kind,s,k,t,rd,rf,v);h=1e-4
    assert (price(s=s+h)-price(s=s-h))/(2*h)==pytest.approx(g['delta'],rel=1e-6)
    assert (price(s=s+h)-2*price()+price(s=s-h))/h**2==pytest.approx(g['gamma'],rel=1e-6)
    assert (price(v=v+h)-price(v=v-h))/(2*h)*.01==pytest.approx(g['vega_1pct'],rel=1e-6)
    assert (price(rd=rd+h)-price(rd=rd-h))/(2*h)*.01==pytest.approx(g['rho_1pct'],rel=1e-6)
    assert (price(rf=rf+h)-price(rf=rf-h))/(2*h)*.01==pytest.approx(g['foreign_rho_1pct'],rel=1e-6)
    assert -(price(t=t+h)-price(t=t-h))/(2*h)/365==pytest.approx(g['theta_daily'],rel=1e-5)

def test_gk_put_call_parity():
    args=(1.1,1.12,1,.04,.02,.15)
    c=garman_kohlhagen('Call',*args)['price'];p=garman_kohlhagen('Put',*args)['price']
    assert c-p==pytest.approx(1.1*np.exp(-.02)-1.12*np.exp(-.04))

@pytest.mark.parametrize('client',['importer','exporter'])
def test_client_hedges_lock_cashflows_and_protect_correct_direction(client):
    result=client_hedges(1.1,.04,.02,1,.15,1e6,client,outcomes=[.5,1.1,2.])
    flows=result['flows'];details=result['details'].set_index('strategy')
    sign=1 if client=='exporter' else -1
    assert flows.forward.to_numpy()==pytest.approx(np.ones(3)*sign*1e6*result['forward'])
    assert flows.option.min()>=sign*1e6*details.loc['option','protected_rate']-1e-7
    assert abs(result['collar']['net_premium'])<1e-10
    effective=sign*flows.collar/1e6
    assert effective.min()>=result['collar']['lower']-1e-10
    assert effective.max()<=result['collar']['upper']+1e-10

@pytest.mark.parametrize('tenors,view',[([2,10],'steepener'),([5,30],'flattener'),([2,5,10],'butterfly')])
def test_curve_trades_are_dv01_neutral(tenors,view):
    result=curve_trade(tenors,[.04]*len(tenors),1e6,date(2026,9,11),view)
    assert result['legs'].dv01.sum()==pytest.approx(0,abs=1e-8)
    assert result['scenarios'].set_index('scenario').loc['parallel','pnl']==pytest.approx(0,abs=1e-7)
    if len(tenors)==3:assert result['legs'].dv01@np.array(tenors)==pytest.approx(0,abs=1e-7)

@pytest.mark.parametrize('tab_key',['fx.forwards','fx.options','fx.hedge'])
@pytest.mark.parametrize('lang',['en','fr'])
def test_fx_workflows_render(tab_key,lang):
    from core.i18n import TRANSLATIONS
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page='markets',lang=lang)
    app.session_state['markets_tabs']=TRANSLATIONS[lang]['fx']
    app.session_state['fx_tabs']=TRANSLATIONS[lang][tab_key]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0

@pytest.mark.parametrize('tab_key',['curve','curve.bucket','curve_trade'])
def test_rates_workflows_render(tab_key):
    from core.i18n import TRANSLATIONS
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params['page']='markets'
    app.session_state['rates_tabs']=TRANSLATIONS['en'][tab_key]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0
