from dataclasses import replace
from datetime import date
import numpy as np
import pandas as pd
import pytest
from engines.option_chain_engine import (solve_implied_volatility, sample_option_chain, analyze_option_chain,
    smile_metrics, term_structure, interpolate_iv)
from engines.options_pricing_engine import black_scholes_price as price
from engines.equity_derivatives_engine import (OptionPosition,position_analytics,option_scenario,scenario_matrix,delta_hedge,greek_grid)
from engines.scenario_engine import MarketScenario,curve_scenarios


@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('spot,strike,time,rate,vol,div',[(100,100,1,.04,.215,.02),(110,100,.2,-.02,.4,.01),(80,100,2,.05,.8,.08),(100,100,.0001,0,.3,0)])
def test_brent_iv_recovers_bsm_and_price(kind,spot,strike,time,rate,vol,div):
    result=solve_implied_volatility(price(kind,spot,strike,time,rate,vol,div),kind,spot,strike,time,rate,div)
    assert result.status=='solved'
    assert result.volatility==pytest.approx(vol,abs=1e-8)
    assert abs(result.price_error)<1e-8


@pytest.mark.parametrize('value',[-1,100,101,float('nan'),float('inf')])
def test_iv_rejects_impossible_prices(value):
    assert solve_implied_volatility(value,'Call',100,100,1,0).volatility is None


def test_iv_discounted_bounds_and_lower_limit():
    result=solve_implied_volatility(0,'Call',100,100,1,0)
    assert result.volatility==0 and result.status=='lower_bound'
    assert solve_implied_volatility(99,'Call',100,100,1,0,.1).status=='out_of_bounds'
    assert solve_implied_volatility(5,'Put',100,100,0,.04).status=='invalid_input'


@pytest.mark.parametrize('mode',['iv','price'])
def test_chain_workflows_and_empirical_metrics(mode):
    data=sample_option_chain(); result=analyze_option_chain(data,'2026-09-09',mode)
    assert result['rejected'].empty
    chain=result['chain']; assert len(chain)==128
    assert np.isfinite(chain.select_dtypes('number').drop(columns='market_price',errors='ignore')).all().all()
    for expiry,frame in chain.groupby('maturity'):
        metrics=smile_metrics(frame)
        assert metrics['downside_skew']>0 and metrics['upside_wing']<0
        assert metrics['risk_reversal_25']==pytest.approx(-metrics['put_skew_25'])
        assert 'delta' in metrics['methods']['call25_iv']
    assert term_structure(chain)['shape']=='upward-sloping'


def test_bad_chain_rows_reported_and_delta_outside_chain_is_not_invented():
    data=sample_option_chain().iloc[:3].copy();data.loc[0,'market_price']=-1
    result=analyze_option_chain(data,'2026-09-09')
    assert len(result['rejected'])==1 and len(result['chain'])==2
    value,method=interpolate_iv(result['chain'],'moneyness',2.)
    assert value is None and 'no extrapolation' in method
    data['spot']=[100,101,100]
    with pytest.raises(ValueError):analyze_option_chain(data,'2026-09-09')


@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('quantity',[10,-10,0])
def test_position_scaling_and_local_pnl(kind,quantity):
    position=OptionPosition(option_type=kind,quantity=quantity,dividend=.02)
    a=position_analytics(position)
    assert a['cash_delta']==pytest.approx(a['position_delta']*position.spot)
    assert a['cash_gamma']==pytest.approx(a['position_gamma']*position.spot**2)
    assert a['gamma_pnl_1pct']==pytest.approx(.5*a['cash_gamma']*.01**2)
    zero=option_scenario(position,MarketScenario())
    assert zero['full']==zero['approximation']==zero['residual']==0
    small=option_scenario(position,MarketScenario(equity=.0001,volatility=.00001,rate_bp=.01,elapsed_days=.001))
    assert small['full']==pytest.approx(small['approximation'],abs=.0002)
    assert sum(small['parts'].values())+small['residual']==pytest.approx(small['full'])


def test_static_hedge_reconciliation_and_rebalance():
    p=OptionPosition();s=MarketScenario(equity=.05,volatility=.03)
    h=delta_hedge(p,s)
    assert h['option_pnl']+h['hedge_pnl']==pytest.approx(h['net_pnl'])
    assert h['hedge_units']==pytest.approx(-position_analytics(p)['position_delta'])
    assert h['new_net_delta']+h['rebalance_units']==pytest.approx(0)
    expected_gamma_pnl=.5*position_analytics(p)['position_gamma']*(p.spot*.0001)**2
    assert delta_hedge(p,MarketScenario(equity=.0001))['net_pnl']==pytest.approx(expected_gamma_pnl,rel=.001)
    with pytest.raises(ValueError):delta_hedge(p,MarketScenario(elapsed_days=1))


def test_scenario_grid_invalid_vols_are_flagged_not_clipped():
    grid=scenario_matrix(OptionPosition(volatility=.05))
    assert grid.loc[grid.vol_points<=-5,'pnl'].isna().all()
    assert grid.loc[grid.vol_points<=-5,'status'].str.startswith('invalid').all()
    assert grid.loc[(grid.spot_shock==0)&(grid.vol_points==0),'pnl'].item()==0
    with pytest.raises(ValueError):option_scenario(OptionPosition(),MarketScenario(volatility=-1))


def test_greek_surface_sensitivities_and_curve_preset_definitions():
    p=OptionPosition(rate=0,dividend=0)
    gamma=greek_grid(p,'gamma');vega=greek_grid(p,'vega_1pct')
    assert (gamma>=0).all().all()
    assert gamma.iloc[0].idxmax()==pytest.approx(100,abs=3)
    assert vega.loc[vega.index[-1],100]>vega.loc[vega.index[0],100]
    presets=curve_scenarios()
    assert presets['Bear steepener'].rate_at([1,2,6,10,30])==pytest.approx([10,10,25,40,40])
    assert presets['Bull flattener'].rate_at([2,10])==pytest.approx([-10,-40])
