from datetime import datetime,timezone
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core.market_sessions import SESSIONS,session_state

@pytest.mark.parametrize('date,opened,hour',[('2026-01-15T14:45:00',True,9),('2026-07-15T13:45:00',True,9),('2026-07-18T13:45:00',False,9)])
def test_new_york_local_session_handles_dst_and_weekends(date,opened,hour):
    result=session_state(SESSIONS[0],datetime.fromisoformat(date).replace(tzinfo=timezone.utc))
    assert result['scheduled_open']==opened and result['local'].hour==hour
    assert result['minutes']>0

def test_tokyo_lunch_break_and_close_extension():
    assert not session_state(SESSIONS[3],datetime(2026,9,21,3,tzinfo=timezone.utc))['scheduled_open']
    assert session_state(SESSIONS[3],datetime(2026,9,21,6,20,tzinfo=timezone.utc))['scheduled_open']

def test_search_preserves_book_and_opens_common_security_page():
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',page='overview');app.run()
    app.selectbox(key='demo_selector').set_value('options').run()
    before=app.session_state.terminal.book.positions.copy()
    app.selectbox(key='security_search').set_value('NVDA').run()
    assert not app.error and not app.exception
    assert app.query_params['security']==['NVDA']
    assert app.query_params['page']==['security']
    assert app.session_state.terminal.book.positions.equals(before)
    assert not any(w.key=='demo_selector' for w in app.selectbox)

@pytest.mark.parametrize('group',['Equities','Indexes','FX','Rates','Commodities','ETFs','Volatility','Crypto'])
def test_each_asset_class_has_safe_offline_empty_states(group):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',page='markets');app.run()
    app.button_group(key='market_asset_class').set_value(group).run()
    assert not app.error and not app.exception

def test_navigation_from_component_result_after_header_widgets():
    app=AppTest.from_string('''import streamlit as st
from core.state import get_state
from components.global_header import global_header,open_security
global_header(get_state())
open_security('SPX')
''',default_timeout=30).run()
    assert not app.exception and app.query_params['page']==['security']
