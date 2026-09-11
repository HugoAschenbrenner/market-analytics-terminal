from pathlib import Path
import time
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from services.analytics import marked_positions
from engines.risk_factor_engine import covariance_estimate,risk_statistics,backtest_var,curve_pca
from engines.rates_tools_engine import key_rate_ladder

@pytest.mark.parametrize('method',['sample','ewma','ledoit_wolf'])
def test_covariance_100_assets_psd_and_deterministic_cash(method):
    x=np.random.default_rng(15).normal(size=(400,100));x[:,0]=0
    started=time.perf_counter();cov,shrink=covariance_estimate(x,method)
    assert time.perf_counter()-started<5
    assert np.allclose(cov,cov.T)
    assert np.linalg.eigvalsh(cov).min()>-1e-10
    assert not cov[0].any()
    assert 0<=shrink<=1

def test_sample_covariance_matches_unbiased_reference():
    x=np.random.default_rng(3).normal(size=(100,5))
    cov,_=covariance_estimate(x)
    assert cov==pytest.approx(np.cov(x,rowvar=False))

def test_ewma_weights_emphasize_recent_variance():
    x=np.concatenate([np.zeros(100),np.tile([-5,5],20)])[:,None]
    sample,_=covariance_estimate(x);ewma,_=covariance_estimate(x,'ewma')
    assert ewma[0,0]>sample[0,0]

def test_ledoit_wolf_matches_independent_fourth_moment_reference():
    x=np.random.default_rng(45).normal(size=(30,4));x[:,1]+=2*x[:,0];x-=x.mean(0)
    n,p=x.shape;emp=x.T@x/n;target=np.eye(p)*np.trace(emp)/p
    delta=((emp-target)**2).sum()
    numerator=sum(np.sum((np.outer(row,row)-emp)**2) for row in x)/n**2
    shrink=np.clip(numerator/delta,0,1)
    cov,actual=covariance_estimate(x,'ledoit_wolf')
    assert actual==pytest.approx(shrink)
    assert cov==pytest.approx((1-shrink)*emp+shrink*target)

def test_component_marginal_and_incremental_var_reconcile_to_finite_differences():
    rng=np.random.default_rng(17);unit=rng.normal(size=(1000,4));q=np.array([3.,2.,-1.,4.]);pnl=unit*q
    risk=risk_statistics(pd.DataFrame(pnl),quantities=q)
    assert risk['contributions'].component_var.sum()==pytest.approx(risk['parametric_var'])
    for i in range(4):
        bump=np.zeros(4);bump[i]=1e-4
        up=risk_statistics(pd.DataFrame(unit*(q+bump)))['parametric_var']
        down=risk_statistics(pd.DataFrame(unit*(q-bump)))['parametric_var']
        assert (up-down)/2e-4==pytest.approx(risk['contributions'].marginal_var_per_unit[i],rel=1e-6)
        without=pnl.copy();without[:,i]=0
        assert risk['parametric_var']-risk_statistics(pd.DataFrame(without))['parametric_var']==pytest.approx(risk['contributions'].incremental_var[i])

def test_es_and_var_horizon_and_zero_risk():
    x=pd.DataFrame(np.random.default_rng(2).normal(size=(400,5)))
    risk=risk_statistics(x,horizon=10)
    assert risk['es']>=risk['var']>=0
    assert risk['parametric_var']==pytest.approx(risk_statistics(x)['parametric_var']*np.sqrt(10))
    assert risk_statistics(x*0)['parametric_es']==0

def test_backtest_does_not_look_ahead():
    series=pd.Series(np.random.default_rng(99).normal(size=400));changed=series.copy();changed.iloc[300:]=-10000
    before=backtest_var(series);after=backtest_var(changed)
    assert before['var'].iloc[:301].equals(after['var'].iloc[:301])
    assert before['var'].iloc[:250].isna().all()

def test_curve_pca_recovers_parallel_factor():
    levels=np.arange(50)[:,None]**2*.0001
    history=np.array([2.,3.,4.,5.,6.])[None,:]+levels
    pca=curve_pca(history)
    assert pca['explained'][0]==pytest.approx(1)
    assert pca['loadings'][0]==pytest.approx(np.ones(5)/np.sqrt(5))
    assert pca['loadings']@pca['loadings'].T==pytest.approx(np.eye(3))

def test_key_rate_ladder_reconciles_parallel_dv01():
    state=TerminalState(demo_book());bonds=marked_positions(state).query("asset_class=='Bond'")
    ladder=key_rate_ladder(bonds,state)
    assert ladder.iloc[:,2:].sum(axis=1).to_numpy()==pytest.approx(bonds.dv01.to_numpy(),rel=1e-6)

@pytest.mark.parametrize('tab_key',['risk_var','factor','stress','validation'])
@pytest.mark.parametrize('lang',['en','fr'])
def test_risk_tabs_execute_without_errors(tab_key,lang):
    from core.i18n import TRANSLATIONS
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page='risk',lang=lang)
    app.session_state['risk_tabs']=TRANSLATIONS[lang][tab_key]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0
