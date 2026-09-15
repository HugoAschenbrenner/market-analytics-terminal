from copy import deepcopy
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from core.i18n import TRANSLATIONS
from core.formatting import compact
from components.education import source_inventory, PAGE_TERMS


@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('topic',['read','sources','changes','terms'])
def test_guidance_topics_render_without_changing_positions(lang,topic):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(lang=lang,page='overview')
    app.run();before=deepcopy(app.session_state.terminal.book)
    app.selectbox(key='guide_topic').set_value(topic).run()
    assert not app.exception and not app.error
    pd.testing.assert_frame_equal(before.positions,app.session_state.terminal.book.positions)
    assert before.repo_cash==app.session_state.terminal.book.repo_cash
    if topic=='sources':
        assert any('SYNTH' in item.value for item in app.markdown)


def test_all_workspaces_have_complete_guidance_and_metric_definitions():
    for page,terms in PAGE_TERMS.items():
        for lang in ['en','fr']:
            assert TRANSLATIONS[lang]['guide.'+page+'.intro']
            assert TRANSLATIONS[lang]['guide.'+page+'.read']
            for term in terms:
                assert TRANSLATIONS[lang][term]
                assert TRANSLATIONS[lang]['help.'+term]


def test_source_inventory_retains_actual_observation_source_and_date():
    state=TerminalState(demo_book())
    state.market.as_of='2026-09-15 08:00 UTC'
    state.market.provenance['SPY']=dict(source='PUBLIC',provider='Yahoo Finance',as_of='2026-09-11',price=550.)
    state.market.provenance['EURUSD']=dict(source='USER INPUT',provider='<user>',as_of='2026-09-14',price=1.1)
    rows={r['item']:r for r in source_inventory(state)}
    assert rows['SPY']['as_of']=='2026-09-11'
    assert rows['EURUSD']['source']=='USER INPUT'
    assert rows['EURUSD']['use']=='fx'
    assert rows['VIX']['use']=='vix'
    assert rows['SX5E']['source']=='SYNTHETIC' and rows['SX5E']['as_of']=='—'


@pytest.mark.parametrize('value',[.00123,-.000000015,0.])
def test_small_greeks_do_not_disappear_in_display_rounding(value):
    rendered=compact(value)
    assert float(rendered)==pytest.approx(value,rel=.005)


def test_kpi_help_exposes_precision_and_meaning():
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30).run()
    nav=next(metric for metric in app.metric if metric.label=='NAV')
    assert 'repo borrowing' in nav.proto.help
    assert 'Value before display rounding' in nav.proto.help or 'More precise value' in nav.proto.help
