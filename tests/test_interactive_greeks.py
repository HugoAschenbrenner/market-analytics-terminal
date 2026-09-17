"""Financial tests execute the actual browser modules in Node, without a browser."""
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest
from scipy.special import ndtr

from engines.options_pricing_engine import (
    black_scholes_price, black_scholes_raw_greeks, black_scholes_greeks,
    calculate_d1_d2, greek_conventions, norm_cdf,
)
from engines.pnl_explain_engine import advanced_greeks

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = dict(S=100., K=80., T=2., r=.03, sigma=.25, q=0.)
CASES = [DEFAULT, *[dict(S=s,K=100.,T=t,r=r,sigma=v,q=q) for s,t,r,v,q in [
    (100,1,.03,.2,0), (120,1,.03,.2,.02), (80,1,.03,.2,0),
    (100,.01,.03,.05,.02), (100,10,.03,.2,0), (90,3,-.05,1.5,.2),
    (100,.1,-.03,.3,.04), (100,2,.02,.25,.2),
]]]

def args(p, side):
    return side,p['S'],p['K'],p['T'],p['r'],p['sigma'],p['q']

def raw(p, side='Call'):
    return black_scholes_raw_greeks(*args(p,side))

def price(p, side='Call'):
    return black_scholes_price(*args(p,side))

def js(request):
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    assert node, 'Node.js 20+ is required for browser-engine parity tests (or set NODE_BINARY).'
    result=subprocess.run([node,str(ROOT/'tests/js/greeks_bridge.mjs')],
        input=json.dumps(request),text=True,capture_output=True,check=True,cwd=ROOT)
    return json.loads(result.stdout)


@pytest.mark.parametrize('p',CASES)
def test_parity_and_common_greeks(p):
    c,u=raw(p),raw(p,'Put')
    assert price(p)-price(p,'Put') == pytest.approx(p['S']*math.exp(-p['q']*p['T'])-p['K']*math.exp(-p['r']*p['T']),abs=1e-11)
    assert c['delta']-u['delta'] == pytest.approx(math.exp(-p['q']*p['T']),abs=1e-14)
    for key in ['gamma','vega','vanna','vomma','veta']:
        assert c[key] == u[key]


@pytest.mark.parametrize('p',CASES)
@pytest.mark.parametrize('side',['Call','Put'])
def test_analytic_derivatives_against_central_differences(p,side):
    expected=raw(p,side)
    derivatives=[('delta','S','price',1),('dual_delta','K','price',1),
        ('theta','T','price',-1),('vega','sigma','price',1),('rho','r','price',1),
        ('gamma','S','delta',1),('vanna','sigma','delta',1),
        ('charm','T','delta',-1),('vomma','sigma','vega',1),('veta','T','vega',-1)]
    for greek,axis,value,sign in derivatives:
        h=max(abs(p[axis])*1e-5,1e-7)
        fn=lambda x: price({**p,axis:x},side) if value=='price' else raw({**p,axis:x},side)[value]
        fd=sign*(fn(p[axis]+h)-fn(p[axis]-h))/(2*h)
        assert expected[greek] == pytest.approx(fd,rel=3e-5,abs=2e-7),greek
    h=p['S']*1e-4
    gamma=(price({**p,'S':p['S']+h},side)-2*price(p,side)+price({**p,'S':p['S']-h},side))/h**2
    assert expected['gamma'] == pytest.approx(gamma,rel=4e-5,abs=3e-7)


def test_normal_cdf_tails_against_scipy():
    values=np.unique(np.r_[np.linspace(-12,12,501),[-38,-30,-20,0]]).tolist()
    browser=js(dict(mode='cdf',values=values))
    for x,actual in zip(values,browser):
        assert actual == pytest.approx(float(ndtr(x)),rel=5e-12,abs=1e-315)
        assert norm_cdf(x) == pytest.approx(float(ndtr(x)),rel=5e-12,abs=1e-315)


def test_cross_runtime_parity_random_and_every_ui_corner():
    rng=np.random.default_rng(814)
    states=list(CASES)
    for s,k,t,v,r,q in itertools.product([1.,250.],[1.,250.],[.01,10.],[.01,1.5],[-.05,.2],[0.,.2]):
        states.append(dict(S=s,K=k,T=t,sigma=v,r=r,q=q))
    for _ in range(300):
        states.append(dict(S=rng.uniform(1,250),K=rng.uniform(1,250),T=rng.uniform(.01,10),
            sigma=rng.uniform(.01,1.5),r=rng.uniform(-.05,.2),q=rng.uniform(0,.2)))
    results=js(dict(states=states))
    for p,result in zip(states,results):
        d=calculate_d1_d2(*args(p,'Call')[1:])
        for key in d: assert result[key] == pytest.approx(d[key],rel=1e-12,abs=1e-12)
        for side in ['Call','Put']:
            expected={**raw(p,side),'price':price(p,side)}
            for key,value in expected.items():
                assert math.isfinite(result[side.lower()][key])
                assert result[side.lower()][key] == pytest.approx(value,rel=2e-10,abs=2e-11),(p,side,key)
        assert result['market'] == pytest.approx(greek_conventions(raw(p)),abs=1e-12)


def test_legacy_interfaces_and_explicit_units():
    g=raw(DEFAULT);old=black_scholes_greeks(*args(DEFAULT,'Call'))
    assert old['vega_1pct'] == round(g['vega']/100,10)
    assert old['rho_1pct'] == round(g['rho']/100,10)
    assert old['theta_daily'] == round(g['theta']/365,10)
    assert advanced_greeks(*args(DEFAULT,'Call')) == dict(vanna=g['vanna'],volga=g['vomma'],charm=g['charm'])
    assert greek_conventions(g,252)['theta_daily'] == g['theta']/252
    with pytest.raises(ValueError): greek_conventions(g,360)


def test_curves_matrix_points_and_true_tangents():
    charts=js(dict(mode='curves',state=DEFAULT))['charts']
    assert [c['greek'] for c in charts] == ['delta','dual_delta','theta','vega','rho','gamma','vanna','charm','vomma','veta']*2
    for c in charts:
        assert 80<=len(c['points'])<=150
        x,y=c['current'];assert x==DEFAULT[c['x']]
        assert any(px==x and py==y for px,py in c['points'])
        fn=lambda at: price({**DEFAULT,c['x']:at},c['side']) if c['y']=='price' else raw({**DEFAULT,c['x']:at},c['side'])[c['y']]
        h=max(x*1e-5,1e-6)
        assert c['slope'] == pytest.approx((fn(x+h)-fn(x-h))/(2*h),rel=1e-7,abs=1e-8)


@pytest.mark.parametrize('key',['S','K','T','sigma','r','q'])
def test_each_control_updates_affected_curves_and_metrics(key):
    base=js(dict(mode='curves',state=DEFAULT))
    state={**DEFAULT,key:DEFAULT[key]+(.01 if key in ['sigma','r','q'] else .5)}
    changed=js(dict(mode='curves',state=state))
    assert changed['current']['call']['price'] != base['current']['call']['price']
    assert changed['current']['call']['delta'] != base['current']['call']['delta']
    assert all(a['current']!=b['current'] or a['points']!=b['points']
               for a,b in zip(base['charts'],changed['charts']))


def test_browser_client_units_and_state():
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    assert node, 'Node.js 20+ is required (or set NODE_BINARY).'
    result=subprocess.run([node,'--test',str(ROOT/'tests/js/greeks_client.test.mjs')],capture_output=True,text=True)
    assert result.returncode == 0,result.stdout+result.stderr


@pytest.mark.parametrize('language',['en','fr'])
@pytest.mark.parametrize('theme',['dark','light'])
def test_interactive_lab_mounts_without_book_option(language,theme):
    from streamlit.testing.v1 import AppTest
    from core.i18n import t
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
    app.query_params.update(page='derivatives',lang=language,theme=theme)
    app.session_state['derivative_tabs']=t('interactive_greeks',language)
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('bidi_component')) == 1
    assert not any(s.key=='book_option' for s in app.selectbox)
    assert len(app.tabs) == 6
