"""Fixed demonstrations reconcile to financial engines and never edit the book."""
from copy import deepcopy
from pathlib import Path
from dataclasses import replace
from datetime import date
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from services.demonstrations import collar_demo,eqd_demo,autocallable_demo
from engines.structured_risk_engine import cashflows
from services.cases import valid_views
from services.lab import LabState


def test_collar_payoff_is_capped_and_floored_and_shocks_reconcile():
    d=collar_demo()
    assert d['payoff'].collar.min()==90000
    assert d['payoff'].collar.max()==110000
    assert d['after']['nav']-d['before']['nav']==pytest.approx(d['premium'])
    assert d['scenarios'].query('spot_shock==0').collar.iloc[0]==pytest.approx(0)
    assert d['scenarios'].query('spot_shock==-.3').collar.iloc[0]>d['scenarios'].query('spot_shock==-.3').unprotected.iloc[0]
    assert d['before']['pnl'].index.equals(d['after']['pnl'].index)
    assert d['after']['var']<d['before']['var']


def test_eqd_attribution_hedge_and_post_shock_delta_reconcile():
    d=eqd_demo();p=d['pnl'];h=d['hedge']
    assert sum(p['parts'].values())+p['residual']==pytest.approx(p['full'])
    assert h['hedge_units']==pytest.approx(-d['greeks']['position_delta'])
    assert h['net_pnl']==pytest.approx(p['full']+h['hedge_units']*100*(-.08))
    assert h['new_net_delta']==pytest.approx(d['after']['position_delta']+h['hedge_units'])
    assert h['rebalance_units']==pytest.approx(-h['new_net_delta'])


@pytest.mark.parametrize('product',['Athena','Phoenix'])
@pytest.mark.parametrize('memory',[False,True])
def test_timeline_exactly_reconciles_to_cashflows(product,memory):
    d=autocallable_demo();i=d['inputs'];paths=d['paths']
    plain=cashflows(paths,i,product,memory)
    flows,timeline=cashflows(paths,i,product,memory,capture_timeline=True)
    pd.testing.assert_frame_equal(plain,flows)
    totals=timeline.groupby('path')[['coupon_paid','principal_paid','discounted_payment','payment']].sum()
    np.testing.assert_allclose(totals,flows[['coupon_paid','redemption','discounted_payoff','payoff']])
    assert (timeline.loc[~timeline.alive_before,'payment']==0).all()
    assert not timeline.groupby('path').tail(1).alive_after.any()
    assert flows.redemption.tolist()==[100,100,45]
    if product=='Phoenix' and memory:
        assert timeline.query('path==0').coupon_paid.iloc[:4].tolist()==[2,0,4,2]
    elif product=='Phoenix':
        assert timeline.query('path==0').coupon_paid.iloc[:4].tolist()==[2,0,2,2]


def test_timeline_barrier_equality_and_final_stub():
    d=autocallable_demo();i=replace(d['inputs'],maturity_years=.6)
    paths=np.full((1,3,3),i.coupon_barrier)
    paths[0,-1,:]=i.protection_barrier
    flows,timeline=cashflows(paths,i,'Phoenix',True,capture_timeline=True)
    assert flows.redemption.iloc[0]==100  # protection is strict below
    assert timeline.coupon_paid.tolist()==[2,2,0]
    assert timeline.time_years.tolist()==[.25,.5,.6]
    assert timeline.coupon_arrears.iloc[-1]==pytest.approx(.8)


def test_timeline_workload_limit():
    d=autocallable_demo()
    with pytest.raises(ValueError,match='20 paths'):
        cashflows(np.tile(d['paths'][:1],(21,1,1)),d['inputs'],capture_timeline=True)


@pytest.mark.parametrize('choice',['collar','eqd','autocallable'])
@pytest.mark.parametrize('lang,theme',[('en','dark'),('fr','light')])
def test_demo_from_welcome_and_export_preserves_shared_book(choice,lang,theme):
    state=TerminalState(demo_book('options'));state.ui.language=lang;state.ui.theme=theme
    before=deepcopy(state.book)
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',lang=lang,theme=theme)
    app.session_state.terminal=state
    app.run().button(key='welcome-demo-'+choice).click().run()
    assert not app.exception and not app.error
    assert app.query_params['page']==['demonstrations']
    assert app.session_state.demo_choice==choice
    assert app.metric and app.get('plotly_chart')
    assert not any(x.key=='demo_selector' for x in app.selectbox)
    app.button(key='demo_report').click().run()
    assert not app.exception and not app.error
    assert app.get('download_button')
    pd.testing.assert_frame_equal(app.session_state.terminal.book.positions,before.positions)
    assert app.session_state.terminal.book.repo_cash==before.repo_cash
    assert app.session_state.terminal.book.structured_terms==before.structured_terms


def test_demo_option_transfer_preserves_custom_chain_date():
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30);app.query_params.update(version='v2',page='demonstrations')
    lab=LabState(as_of=date(2026,9,1),currency='EUR');chain=lab.chain.copy()
    app.session_state.analytics_lab=lab;app.session_state.demo_choice='eqd'
    app.run().button(key='demo_open_eqd').click().run()
    assert not app.exception and not app.error
    assert app.session_state.analytics_lab.position==eqd_demo()['position']
    assert app.session_state.analytics_lab.as_of==date(2026,9,1)
    pd.testing.assert_frame_equal(app.session_state.analytics_lab.chain,chain)
    assert app.session_state.analytics_lab.currency=='USD'


def test_demonstration_choice_is_validated_for_case_restore():
    assert valid_views({'demo_choice':'eqd'},'en')=={'demo_choice':'eqd'}
    assert valid_views({'demo_choice':'unknown'},'en')=={}
