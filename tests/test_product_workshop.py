from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from core.i18n import TRANSLATIONS
from core.models import TerminalState
from core.state import demo_book
from engines.options_payoff_engine import SUPPORTED_STRATEGIES
from engines.strategy_workshop_engine import strategy_workshop


def strategy_args(name):
    return dict(strategy=name,spot=100.,strike=100.,strike_2=90. if name=='Bear Put Spread' else 110.,
                maturity=.75,rate=.03,volatility=.25)


@pytest.mark.parametrize('name',SUPPORTED_STRATEGIES)
def test_model_strategy_greeks_against_repricing_and_quantity_scaling(name):
    args=strategy_args(name)
    base=strategy_workshop(**args)
    scaled=strategy_workshop(**args,units=100.)
    assert scaled['net_debit']==pytest.approx(100*base['net_debit'])
    assert scaled['table'].pnl.to_numpy()==pytest.approx(100*base['table'].pnl.to_numpy())
    assert scaled['breakevens']==pytest.approx(base['breakevens'])
    for key,value in base['greeks'].items():
        assert scaled['greeks'][key]==pytest.approx(100*value)
    def value(**bumps):
        return strategy_workshop(**(args|bumps))['net_debit']
    up,down=value(spot=100.01),value(spot=99.99)
    assert base['greeks']['delta']==pytest.approx((up-down)/.02,abs=2e-7)
    assert base['greeks']['gamma']==pytest.approx((up-2*value()+down)/.01**2,abs=2e-6)
    assert base['greeks']['vega_1pct']==pytest.approx((value(volatility=.25001)-value(volatility=.24999))/.00002/100,abs=2e-6)


def test_manual_premiums_exact_pnl_and_no_double_multiplier():
    args=strategy_args('Bull Call Spread')
    result=strategy_workshop(**args,units=100.,premiums=[3.,1.])
    assert result['net_debit']==200
    assert result['risk_profile']['max_gain']==800
    assert result['risk_profile']['max_loss']==200
    assert result['breakevens']==[102.]
    assert result['greeks']==strategy_workshop(**args,units=100.)['greeks']
    repriced=strategy_workshop(**(args|dict(volatility=.4)),units=100.,premiums=[3.,1.])
    assert repriced['table'].pnl.to_numpy()==pytest.approx(result['table'].pnl.to_numpy())
    assert repriced['greeks']['delta']!=result['greeks']['delta']


def test_zero_premium_regions_and_unlimited_loss():
    free_call=strategy_workshop(**strategy_args('Long Call'),premiums=[0.])
    free_put=strategy_workshop(**strategy_args('Long Put'),premiums=[0.])
    assert free_call['zero_intervals']==[(0.,100.)]
    assert free_put['zero_intervals']==[(100.,np.inf)]
    short=strategy_workshop(**strategy_args('Short Call'),premiums=[5.])
    assert short['risk_profile']['max_loss']=='Unlimited'
    assert short['risk_profile']['max_gain']==5


@pytest.mark.parametrize('premiums',[[],[1.,2.],[-1.],[float('nan')]])
def test_strategy_rejects_invalid_premiums(premiums):
    with pytest.raises(ValueError):
        strategy_workshop(**strategy_args('Long Call'),premiums=premiums)


def workshop_app(tool,lang='en',theme='dark',**values):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',page='derivatives',lang=lang,theme=theme)
    app.session_state['derivative_tabs']=TRANSLATIONS[lang]['workshop']
    app.session_state['workshop_tool']=tool
    for key,value in values.items():
        app.session_state[key]=value
    return app


@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('name',SUPPORTED_STRATEGIES)
def test_all_strategy_presets_and_manual_mode_render(lang,name):
    app=workshop_app('strategies',lang,workshop_strategy=name).run()
    assert not app.exception and not app.error and not app.warning
    assert len(app.get('plotly_chart'))==1
    assert len(app.metric)==6
    app.radio(key='strategy_mode').set_value('manual').run()
    assert not app.exception and not app.error
    if app.warning:
        assert name=='Collar'  # Positive nominal P&L before funding at these rates.
        assert app.warning[0].value==TRANSLATIONS[lang]['workshop.premium_warning']
    assert any(x.key.startswith('strategy_premium_') for x in app.number_input)


@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('direction',['up','down'])
@pytest.mark.parametrize('activation',['in','out'])
def test_all_barrier_variants_and_touch_switch_render(kind,direction,activation):
    app=workshop_app('barriers','fr',barrier_kind=kind,barrier_direction=direction,barrier_activation=activation).run()
    assert not app.exception and not app.error and not app.warning
    app.checkbox(key='barrier_touched').check().run()
    assert not app.exception and not app.error and not app.warning
    assert app.metric[2].value=='100.00%'
    assert app.metric[0].value==('0.0000' if activation=='out' else app.metric[1].value)


@pytest.mark.parametrize('kind',['discount','bonus','capped_bonus'])
@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('theme',['light','dark'])
def test_certificate_variants_render(kind,lang,theme):
    app=workshop_app('certificates',lang,theme,certificate_kind=kind).run()
    assert not app.exception and not app.error and not app.warning
    assert len(app.get('plotly_chart'))==1
    assert float(app.metric[0].value)>0


@pytest.mark.parametrize('tool,values,key',[
    ('strategies',{'strategy_strike':120.},'workshop.strike_order'),
    ('certificates',{'certificate_kind':'bonus','certificate_barrier':120.},'workshop.barrier_below_bonus'),
    ('certificates',{'certificate_kind':'capped_bonus','certificate_cap':100.},'workshop.cap_above_bonus'),
])
def test_invalid_terms_show_localized_explanations(tool,values,key):
    app=workshop_app(tool,'fr',**values).run()
    assert not app.exception and not app.error
    assert app.warning[0].value==TRANSLATIONS['fr'][key]
    assert not app.get('plotly_chart')


def test_experiments_work_without_book_options_and_preserve_shared_state():
    state=TerminalState(demo_book('macro'))
    assert not (state.book.positions.asset_class=='Option').any()
    before=deepcopy(state.book)
    app=workshop_app('strategies')
    app.session_state.terminal=state
    app.run()
    app.number_input(key='strategy_spot').set_value(130.).run()
    app.selectbox(key='workshop_tool').select('barriers').run()
    app.checkbox(key='barrier_touched').check().run()
    app.selectbox(key='workshop_tool').select('certificates').run()
    app.selectbox(key='certificate_kind').select('bonus').run()
    app.number_input(key='certificate_dividend').set_value(4.).run()
    assert not app.exception and not app.error
    assert not any(x.key=='book_option' for x in app.selectbox)
    pd.testing.assert_frame_equal(app.session_state.terminal.book.positions,before.positions)
    assert app.session_state.terminal.book.repo_cash==before.repo_cash


def test_workshop_survives_language_change_without_losing_inputs():
    app=workshop_app('barriers').run()
    app.number_input(key='barrier_spot').set_value(105.).run()
    app.checkbox(key='barrier_touched').check().run()
    app.selectbox(key='global_language').select('fr').run()
    assert not app.exception and not app.error
    assert app.session_state['derivative_tabs']==TRANSLATIONS['fr']['workshop']
    assert app.selectbox(key='workshop_tool').value=='barriers'
    assert app.number_input(key='barrier_spot').value==105.
    assert app.checkbox(key='barrier_touched').value
    app.selectbox(key='global_theme').select('light').run()
    app.selectbox(key='workshop_tool').select('strategies').run()
    app.selectbox(key='workshop_tool').select('barriers').run()
    assert not app.exception and not app.error
    assert app.number_input(key='barrier_spot').value==105.
    assert app.checkbox(key='barrier_touched').value


def test_negative_rate_put_premium_can_exceed_strike_without_ui_failure():
    app=workshop_app('strategies',workshop_strategy='Long Put',strategy_mode='manual',
                    strategy_spot=1.,strategy_strike=100000.,strategy_time=10.,strategy_rate=-10.).run()
    assert not app.exception and not app.error
    assert app.number_input(key='strategy_premium_Long Put_0').value>100000.


def test_workshop_restores_after_inactive_widget_cleanup():
    app=workshop_app('certificates',certificate_kind='bonus').run()
    app.number_input(key='certificate_bonus').set_value(115.).run()
    # Simulate a rerun with only the non-widget values surviving. Deleting a
    # live widget from AppTest breaks its serialization before the app can run.
    saved=deepcopy(app.session_state['_workshop_inputs'])
    active=app.session_state['_derivative_active']
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',page='derivatives')
    app.session_state['_derivative_active']=active
    app.session_state['_workshop_inputs']=saved
    app.run()
    assert not app.exception and not app.error
    assert app.session_state['derivative_tabs']==TRANSLATIONS['en']['workshop']
    assert app.number_input(key='certificate_bonus').value==115.
    app.button_group(key='workspace').set_value('markets').run()
    app.button_group(key='workspace').set_value('derivatives').run()
    assert not app.exception and not app.error
    assert app.selectbox(key='workshop_tool').value=='certificates'
    assert app.number_input(key='certificate_bonus').value==115.
