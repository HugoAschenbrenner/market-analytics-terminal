from dataclasses import replace
import numpy as np
import pytest
from engines.structured_products_valuation_engine import AutocallableValuationInputs,evaluate_autocallable_cashflows,simulate_correlated_gbm_performance_paths
from engines.structured_risk_engine import cashflows,value_note,bump_risk
from engines.structured_products_engine import AutocallableTerms,calculate_phoenix_payoff


def test_vectorized_athena_matches_audited_cashflows_with_stub():
    i=AutocallableValuationInputs(simulations=200,maturity_years=2.3,observations_per_year=4)
    paths=simulate_correlated_gbm_performance_paths(i)
    expected=evaluate_autocallable_cashflows(paths,i);actual=cashflows(paths,i)
    for col in ['payoff','discounted_payoff','coupon_paid','event_time_years']:
        assert actual[col].to_numpy()==pytest.approx(expected[col].to_numpy(),abs=1e-6)

@pytest.mark.parametrize('memory',[True,False])
def test_phoenix_coupon_memory_matches_audited_payoff(memory):
    i=AutocallableValuationInputs(notional=100,simulations=100,maturity_years=2,observations_per_year=4)
    paths=simulate_correlated_gbm_performance_paths(i);actual=cashflows(paths,i,'Phoenix',memory)
    terms=AutocallableTerms('Phoenix',100,.08/4,0.,-.3,-.4,memory)
    for n,path in enumerate(paths):
        expected=calculate_phoenix_payoff(terms,(path[:,0]-1).tolist())
        assert actual.iloc[n].payoff==pytest.approx(expected.total_payoff,abs=1e-6)
        assert actual.iloc[n].coupon_paid==pytest.approx(expected.total_coupons_paid,abs=1e-6)


def test_bumps_preserve_fixings_and_match_common_seed_revaluation():
    i=AutocallableValuationInputs(notional=100,initial_spots=(100.,110.),volatilities=(.2,.25),simulations=3000)
    ratios=(.9,1.);r=bump_risk(i,ratios)
    v=lambda ii=i,rr=ratios:value_note(ii,rr)['summary']['value']
    assert r['deltas'][0]==pytest.approx((v(rr=(.909,1.))-v(rr=(.891,1.)))/1.8)
    assert r['deltas'][0]!=0
    assert r['vega']==pytest.approx((v(replace(i,volatilities=(.21,.26)))-v(replace(i,volatilities=(.19,.24))))/2)
    assert r==bump_risk(i,ratios)
    assert value_note(i,ratios)['summary']['mc_error']>0


def test_shared_note_mark_scenario_and_probabilities_reconcile():
    from core.models import TerminalState
    from core.state import demo_book
    from services.analytics import marked_positions
    from engines.desk_scenario_engine import evaluate_scenario,DeskScenario
    state=TerminalState(demo_book('structured'));marks=marked_positions(state)
    row=marks.query("asset_class=='Structured'").iloc[0]
    assert 0<=row.autocall_probability<=1
    assert row.market_value==pytest.approx(row.mark*row.quantity*row.multiplier)
    zero=evaluate_scenario(marks,state.market,state.book,DeskScenario('custom'))
    assert zero['pnl']==pytest.approx(0)
    result=evaluate_scenario(marks,state.market,state.book,DeskScenario('custom',correlation=.1))
    assert result['by_factor'].sum()==pytest.approx(result['pnl'])
    assert result['pnl']!=0

@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('sub',['product','risk','simulation','advanced'])
def test_structured_workspace_tabs(lang,sub):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from core.models import TerminalState
    from core.state import demo_book
    from core.i18n import TRANSLATIONS
    state=TerminalState(demo_book('structured'));state.ui.language=lang
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.session_state['terminal']=state;app.query_params.update(page='derivatives',lang=lang)
    app.session_state['derivative_tabs']=TRANSLATIONS[lang]['structured'];app.session_state['structured_tabs']=TRANSLATIONS[lang][sub]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0
