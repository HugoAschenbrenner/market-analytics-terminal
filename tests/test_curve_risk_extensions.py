import numpy as np
import pandas as pd
import pytest
from engines.rates_tools_engine import ZeroCurve,curve_from_table,zero_curve_table,curve_spreads,cashflow_curve_risk,sample_curve_table
from engines.scenario_engine import MarketScenario,curve_scenarios
from engines.risk_factor_engine import correlation_stress,covariance_attribution
from engines.portfolio_risk_engine import calculate_portfolio_attribution


def test_zero_curve_discount_and_forward_identities():
    curve=ZeroCurve((1.,2.,5.,10.,30.),(.04,)*5)
    data=zero_curve_table(curve)
    assert data.discount_factor.to_numpy()==pytest.approx(np.exp(-.04*data.tenor.to_numpy()))
    assert data.forward_rate.to_numpy()==pytest.approx(np.full(5,.04))
    assert np.all(np.diff(data.discount_factor)<0)
    assert curve_spreads(curve)=={'2s10s_bp':0.,'5s30s_bp':0.}
    assert curve.discount(0)==1


def test_curve_risk_reconciles_cashflows_key_rates_and_zero_shock():
    curve=curve_from_table(sample_curve_table());times=np.arange(.5,10.5,.5)
    flows=np.full(20,2.);flows[-1]+=100
    result=cashflow_curve_risk(times,flows,curve,MarketScenario())
    assert result['pnl']==pytest.approx(0,abs=1e-12)
    assert result['base_value']==pytest.approx(result['cashflows'].present_value.sum())
    assert result['buckets'].dv01.sum()==pytest.approx(result['dv01'],rel=2e-6)
    assert result['duration']==pytest.approx(result['cashflows'].duration_contribution.sum())
    up=cashflow_curve_risk(times,flows,curve,MarketScenario(rate_bp=25))
    assert up['pnl']<0
    down=cashflow_curve_risk(times,flows,curve,MarketScenario(rate_bp=-25))
    assert down['pnl']>0


def test_curve_preserves_twist_kink_and_signed_exposures():
    curve=ZeroCurve((1.,30.),(.03,.04));shock=curve_scenarios()['Bear steepener']
    assert curve.shocked(shock).zero(6)-curve.zero(6)==pytest.approx(.0025)
    long=cashflow_curve_risk([5.],[100.],curve,shock)
    short=cashflow_curve_risk([5.],[-100.],curve,shock)
    assert short['pnl']==pytest.approx(-long['pnl'])
    assert curve_spreads(ZeroCurve((1.,5.),(.02,.03)))['2s10s_bp'] is None


@pytest.mark.parametrize('tenors,rates',[((1,1),(.02,.03)),((0,1),(.02,.03)),((1,2),(.02,float('nan')))])
def test_bad_curves_rejected(tenors,rates):
    with pytest.raises(ValueError):ZeroCurve(tenors,rates)


def test_no_par_yields_silently_interpreted_as_zero_rates():
    data=sample_curve_table();data.loc[0,'rate_type']='par'
    with pytest.raises(ValueError):curve_from_table(data)


@pytest.mark.parametrize('weights',[[.4,.6],[1.2,-.2],[0.,1.],[0.,0.]])
def test_euler_var_volatility_and_pca_reconcile(weights):
    cov=np.array([[.0004,.00012],[.00012,.0009]])
    result=covariance_attribution(cov,weights,confidence=.99,horizon=10)
    c=result['contributions'];pca=result['pca']
    assert c.component_var.sum()==pytest.approx(result['parametric_var'])
    assert c.component_volatility.sum()==pytest.approx(result['volatility'])
    assert pca.portfolio_variance.sum()==pytest.approx(result['volatility']**2)
    assert pca.cumulative_variance.iloc[-1]==pytest.approx(1)
    for i in range(2):
        w=np.array(weights);eps=np.eye(2)[i]*1e-5
        up=covariance_attribution(cov,w+eps,confidence=.99,horizon=10)['parametric_var']
        down=covariance_attribution(cov,w-eps,confidence=.99,horizon=10)['parametric_var']
        assert (up-down)/2e-5==pytest.approx(c.marginal_var[i],abs=1e-7)


def test_correlation_stress_is_psd_and_preserves_variances():
    cov=np.array([[.0004,-.0003],[-.0003,.0009]])
    for blend in [-1,-.3,0,.3,1]:
        stress=correlation_stress(cov,blend)
        assert np.linalg.eigvalsh(stress).min()>-1e-12
        assert np.diag(stress)==pytest.approx(np.diag(cov))
    assert correlation_stress(cov,1)[0,1]==pytest.approx(.02*.03)


def test_existing_portfolio_engine_exposes_distinct_gaussian_attribution():
    returns=pd.DataFrame(np.random.default_rng(25).normal(0,.01,(100,2)),columns=['A','B'])
    result=calculate_portfolio_attribution(returns,{'A':.4,'B':.6},horizon=5,correlation_blend=.5)
    assert result['base']['contributions'].percentage_risk.sum()==pytest.approx(1)
    assert result['stressed']['parametric_var']>result['base']['parametric_var']
