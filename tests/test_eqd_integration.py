from dataclasses import replace
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from services.lab import LabState,option_outputs,curve_outputs
from reports.lab_report import generate_lab_report,lab_report_tables
from engines.scenario_engine import MarketScenario


def app_at(page,version='v2',lang='en'):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=40)
    app.query_params.update(page=page,version=version,lang=lang,theme='light' if lang=='fr' else 'dark')
    return app


@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('view',['chain','position','scenario','hedge','greeks'])
def test_eqd_focused_views_render_offline(lang,view):
    app=app_at('equity-derivatives','v2',lang)
    app.session_state['eqd_view']=view
    app.run()
    assert not app.exception and not app.error
    assert app.get('plotly_chart')
    assert not any('Monte Carlo' in item.value for item in app.title)


@pytest.mark.parametrize('view',['surface','smile','term'])
def test_chain_visualizations_render(view):
    app=app_at('equity-derivatives');app.session_state['eqd_surface_view']=view;app.run()
    assert not app.exception and not app.error
    assert app.get('plotly_chart')


def test_v2_navigation_preserves_lab_inputs_and_dashboard_recomputes():
    app=app_at('equity-derivatives');app.session_state['eqd_view']='scenario';app.run()
    app.number_input(key='eqd_pos_quantity').set_value(-23.).run()
    app.number_input(key='lab_spot_shock').set_value(-8.).run()
    expected=option_outputs(app.session_state.analytics_lab)['scenario']['full']
    app.button_group(key='desk_section').set_value('portfolio').run()
    app.button_group(key='workspace').set_value('overview').run()
    assert not app.exception and not app.error
    assert app.query_params['page']==['overview']
    actual=next(m.value for m in app.metric if m.label=='Option scenario P&L')
    assert actual==f'{expected:,.2f}'
    app.button_group(key='desk_section').set_value('derivatives').run()
    app.button_group(key='workspace').set_value('equity-derivatives').run()
    assert app.session_state.analytics_lab.position.quantity==-23
    assert app.session_state.analytics_lab.scenario.equity==-.08


def test_v2_structured_products_has_dedicated_route():
    app=app_at('structured-products').run()
    assert not app.exception and not app.error
    assert app.session_state.terminal.ui.page=='structured-products'
    assert not any(item.key=='eqd_view' for item in app.button_group)
    app.button(key='load_structured_demo').click().run()
    assert not app.exception and not app.error
    assert app.get('plotly_chart')


def test_report_includes_computed_inputs_and_no_formula_injection():
    lab=LabState();lab.chain['underlying']='=2+2';lab.matrix_spots=(-.2,0,.2)
    lab.hedge_scenario=MarketScenario(equity=.1,volatility=.07)
    tables=lab_report_tables(lab);out=option_outputs(lab)
    assert tables['Spot_Vol_Matrix'].spot_shock.unique()==pytest.approx([-.2,0,.2])
    assert tables['Delta_Hedge'].set_index('metric').loc['net_pnl','value']==pytest.approx(out['hedge']['net_pnl'])
    binary=generate_lab_report(lab)
    from openpyxl import load_workbook
    workbook=load_workbook(BytesIO(binary))
    required=['Option_Chain','Cash_Greeks','Scenario_PnL','Delta_Hedge','Zero_Curve','Curve_DV01','Methodology','Sources']
    assert set(required).issubset(workbook.sheetnames)
    assert workbook['Option_Chain']['A2'].value=='=2+2'
    assert workbook['Option_Chain']['A2'].data_type=='s'


def test_curve_builder_and_report_button_render():
    app=AppTest.from_string('from components.curve_builder import render_curve_builder\nrender_curve_builder()',default_timeout=40).run()
    assert not app.exception and not app.error
    app.selectbox(key='lab_curve_scenario').set_value('Bear steepener').run()
    app.button(key='lab_prepare_export').click().run()
    assert not app.exception and not app.error
    assert app.get('download_button')
    assert app.session_state.analytics_lab.scenario.curve_twist==((2.,10.),(10.,40.))


def test_invalid_option_scenario_is_visible_and_recoverable():
    app=app_at('equity-derivatives');app.session_state['eqd_view']='scenario';app.run()
    app.number_input(key='lab_days').set_value(1000.).run()
    assert not app.exception and any('before expiry' in item.value for item in app.warning)
    app.number_input(key='lab_days').set_value(0.).run()
    assert not app.exception and not app.error and app.get('plotly_chart')


def test_zero_risk_attribution_and_export_remain_usable():
    source='''import pandas as pd
from components.risk_attribution import render_attribution
render_attribution(pd.DataFrame({'A':[0.,0.,0.],'B':[0.,0.,0.]}),[.5,.5])'''
    app=AppTest.from_string(source,default_timeout=40).run()
    assert not app.exception and not app.error
    tables=app.session_state.analytics_lab.risk_tables
    assert np.isfinite(tables['Risk_Attribution'].select_dtypes('number')).all().all()
    app.button(key='lab_prepare_export').click().run()
    assert app.get('download_button') and not app.exception


def test_price_workflow_applies_quotes_and_exports_diagnostics():
    lab=LabState()
    # An impossible quote must remain visible and not contaminate the IV grid.
    lab.chain.loc[0,'market_price']=10000.
    app=app_at('equity-derivatives');app.session_state.analytics_lab=lab;app.run()
    app.selectbox(key='eqd_chain_mode').set_value('price')
    app.button(key='eqd_apply_chain').click().run()
    assert not app.exception and not app.error
    assert app.session_state.analytics_lab.mode=='price'
    tables=lab_report_tables(app.session_state.analytics_lab)
    row=tables['Rejected_Quotes'].set_index('row').loc['0']
    assert row.iv_status=='out_of_bounds' and row.upper_price_bound<10000
    assert len(tables['Option_Chain'])<len(lab.chain)


def test_quote_selection_changes_position_without_changing_signed_size():
    lab=LabState();lab.position=replace(lab.position,quantity=-7,multiplier=50)
    app=app_at('equity-derivatives');app.session_state.analytics_lab=lab;app.run()
    app.selectbox(key='eqd_quote').set_value(15).run()
    app.button(key='eqd_load_quote').click().run()
    app.button_group(key='eqd_view').set_value('position').run()
    assert not app.exception and not app.error
    p=app.session_state.analytics_lab.position
    assert p.option_type=='Put' and p.quantity==-7 and p.multiplier==50
    assert p.strike==pytest.approx(100) and p.maturity==pytest.approx(30/365)


def test_matrix_and_hedge_inputs_survive_navigation_and_match_workbook():
    app=app_at('equity-derivatives');app.session_state.eqd_view='scenario';app.run()
    app.slider(key='eqd_matrix_spot').set_value(25).run()
    app.slider(key='eqd_matrix_vol').set_value(6).run()
    app.button_group(key='eqd_view').set_value('hedge').run()
    app.slider(key='eqd_hedge_spot').set_value(12.).run()
    app.number_input(key='eqd_hedge_vol').set_value(4.).run()
    visible=float(next(m.value for m in app.metric if m.label=='Net hedged P&L').replace(',',''))
    tables=lab_report_tables(app.session_state.analytics_lab)
    assert tables['Delta_Hedge'].set_index('metric').loc['net_pnl','value']==pytest.approx(visible,abs=.005)
    app.button_group(key='desk_section').set_value('markets').run()
    app.button_group(key='workspace').set_value('welcome').run()
    app.button(key='welcome-open-equity-derivatives').click().run()
    app.button_group(key='eqd_view').set_value('scenario').run()
    assert not app.exception and not app.error
    assert app.slider(key='eqd_matrix_spot').value==25
    assert app.slider(key='eqd_matrix_vol').value==6
    assert app.session_state.analytics_lab.hedge_scenario.equity==pytest.approx(.12)


def test_additional_tools_remain_discoverable_and_allow_return():
    app=app_at('equity-derivatives').run()
    app.button(key='eqd_legacy_tools').click().run()
    assert not app.exception and app.session_state.terminal.ui.page=='derivatives'
    app.button_group(key='desk_section').set_value('derivatives').run()
    app.button_group(key='workspace').set_value('equity-derivatives').run()
    assert not app.exception and app.session_state.terminal.ui.page=='equity-derivatives'


def test_language_change_preserves_lab_view_and_inputs():
    app=app_at('equity-derivatives');app.session_state.eqd_view='scenario';app.run()
    assert app.session_state.analytics_lab.position_source=='Independent synthetic example'
    app.number_input(key='eqd_pos_quantity').set_value(-12.).run()
    app.number_input(key='lab_spot_shock').set_value(-8.).run()
    app.selectbox(key='global_language').set_value('fr').run()
    assert not app.exception and not app.error
    assert app.button_group(key='eqd_view').value=='scenario'
    assert app.number_input(key='eqd_pos_quantity').value==-12
    assert app.number_input(key='lab_spot_shock').value==-8
    assert app.session_state.analytics_lab.position_source=='USER INPUT'
