from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from services import cases
from services.lab import LabState, option_outputs, curve_outputs
from services.structured_lab import demo_structured_lab
from services.market_data import ensure_market
from services.analytics import marked_positions


def fixture_case():
    state=TerminalState(demo_book('options'),valuation_date=date(2026,9,9));ensure_market(state)
    state.ui.language='fr';state.ui.theme='light';state.ui.page='equity-derivatives'
    lab=LabState();lab.position=replace(lab.position,quantity=-7,multiplier=50)
    lab.view='scenario';lab.scenario=replace(lab.scenario,equity=-.08,curve_twist=((2.,10.),(10.,40.)))
    lab.risk_tables={'Risk_Stress':pd.DataFrame([dict(source='SYNTHETIC',base_var=12.,stressed_var=15.)])}
    lab.risk_source='SYNTHETIC · fixed example'
    return state,lab,demo_structured_lab()


def raw_case():return cases.export_case(*fixture_case(),board=['SPX','NVDA'],views={'eqd_view':'scenario'},interactive=dict(S=110,K=100,T=1,sigma=.2,r=.03,q=.01))


def test_full_round_trip_preserves_values_units_provenance_and_snapshots():
    state,lab,structured=fixture_case()
    decoded=cases.import_case(cases.export_case(state,lab,structured,board=['NVDA','SPX']))
    pd.testing.assert_frame_equal(decoded.terminal.book.positions,state.book.positions)
    for currency,curve in state.market.curves.items():
        pd.testing.assert_frame_equal(decoded.terminal.market.curves[currency]['history'],curve['history'],check_freq=False)
    assert decoded.terminal.market.provenance==state.market.provenance
    assert decoded.lab.position==lab.position and decoded.lab.scenario==lab.scenario
    assert decoded.terminal.valuation_date==state.valuation_date
    assert decoded.lab.as_of==lab.as_of and decoded.lab.risk_source==lab.risk_source
    pd.testing.assert_frame_equal(decoded.lab.risk_tables['Risk_Stress'],lab.risk_tables['Risk_Stress'])
    assert option_outputs(decoded.lab)['scenario']['full']==pytest.approx(option_outputs(lab)['scenario']['full'])
    assert curve_outputs(decoded.lab)['risk']['base_value']==pytest.approx(curve_outputs(lab)['risk']['base_value'])
    pd.testing.assert_frame_equal(marked_positions(decoded.terminal),marked_positions(state))
    assert decoded.board==['NVDA','SPX'] and decoded.structured.book.repo_cash==0


@pytest.mark.parametrize('mutation', [
    lambda d:d.update(version=999),
    lambda d:d.update(executable='os.system'),
    lambda d:d['terminal']['market']['fx'].update(USD=0),
    lambda d:d['terminal']['market']['fx'].update(EUR=-1),
    lambda d:d['terminal']['risk'].update(confidence=2),
    lambda d:d['lab']['position'].update(multiplier=0),
    lambda d:d['lab']['position'].update(spot=None),
    lambda d:d['lab']['scenario'].update(elapsed_days=100000),
    lambda d:d['terminal']['book']['positions']['data'][0].__setitem__(3,'XYZ'),
    lambda d:d['structured']['book']['structured_terms']['note'].update(correlation=-.8),
    lambda d:d['structured']['book']['structured_terms']['note'].update(simulations=100000000),
    lambda d:d['lab']['curve']['data'][0].__setitem__(0,0),
    lambda d:d.update(board=['NOT-A-SECURITY']),
    lambda d:d.update(interactive=dict(S=0)),
    lambda d:d['terminal']['ui'].update(theme='invisible'),
    lambda d:d['lab']['chain'].update(dtypes=['eval']*len(d['lab']['chain']['columns'])),
])
def test_rejected_case_is_atomic(mutation):
    document=json.loads(raw_case());mutation(document)
    session={'keep':'unchanged','terminal':object()}; before=session.copy();query={'page':'welcome'}
    with pytest.raises(ValueError):cases.apply_case(json.dumps(document),session,query)
    assert session==before and query=={'page':'welcome'}


@pytest.mark.parametrize('raw',[b'{"format":"x","format":"y"}',b'{"x":NaN}',b'{"x":Infinity}',b'not json',b'\xff',b' '*5_000_001,b'['*2000+b']'*2000])
def test_malformed_oversized_duplicate_nonfinite_and_deep_input_rejected(raw):
    with pytest.raises(ValueError):cases.import_case(raw)


def test_restore_invalidates_widgets_results_and_keeps_saved_market_context(monkeypatch):
    from services import market_data
    session={'eqd_pos_quantity':999,'lab_curve_editor':'obsolete','terminal':'old','secret_unsaved':'old'};query={}
    restored=cases.apply_case(raw_case(),session,query)
    assert 'eqd_pos_quantity' not in session and 'lab_curve_editor' not in session
    assert session['board_ready'] and session['board_ids']==['SPX','NVDA']
    assert session['eqd_view']=='scenario' and session['interactive_case']['S']==110
    assert restored.terminal.risk.results=={} and restored.terminal.market.mode=='saved'
    monkeypatch.setattr(market_data,'load_public_context',lambda *a:pytest.fail('Restored case fetched public data'))
    market_data.ensure_market(restored.terminal)
    assert query==dict(version='v2',page='cases',lang='fr',theme='light')


@pytest.mark.parametrize('lang',['en','fr'])
def test_saved_case_route_export_and_restore_callback(lang):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=20)
    app.query_params.update(version='v2',page='cases',lang=lang)
    app.run();app.button(key='case_prepare').click().run()
    assert not app.exception and not app.error
    assert app.get('download_button')
    raw=app.session_state.case_download
    cases.import_case(raw)
    app.session_state.case_pending=raw
    app.session_state.case_preview=dict(positions=6,date='2026-09-09',currency='USD',created='2026-09-09')
    app.run();app.button(key='case_restore').click().run()
    assert not app.exception and not app.error and app.success
    assert app.session_state.terminal.market.mode=='saved'
    app.button(key='case_go_equity-derivatives').click().run()
    assert not app.exception and not app.error and app.get('plotly_chart')
