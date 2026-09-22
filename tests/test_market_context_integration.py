from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.market_contracts import Quote,HistoricalPrices,DataResult,Fundamentals
from core.board import validate_board
from core.securities import SECURITIES
from services.market_monitor import MarketService

NOW=datetime.now(timezone.utc)
@pytest.fixture
def observed(monkeypatch):
    def raw(self,id,period='1Y'):
        dates=pd.date_range(end=pd.Timestamp.now(tz='UTC')-pd.Timedelta(days=1),periods=700)
        values=100*np.exp(np.cumsum(np.sin(np.arange(700))*.005+.001))
        frame=pd.DataFrame({k:values for k in ('open','high','low','close','adjusted_close')},index=dates)
        frame['volume']=100000
        return DataResult((frame,{'currency':SECURITIES[id].currency},{}),'fresh',NOW,NOW)
    monkeypatch.setattr(MarketService,'raw_chart',raw)
    monkeypatch.setattr(MarketService,'fundamentals',lambda self,id:DataResult(Fundamentals(id,{'marketCap':1e9,'sector':'Technology'},'fixture'),'fresh',NOW,NOW))

def app_at(page,lang='en',theme='dark',**state):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(version='v2',page=page,lang=lang,theme=theme,security='NVDA')
    for k,v in state.items():app.session_state[k]=v
    return app.run()

@pytest.mark.parametrize('view',['summary','volatility','correlation','news','events','fundamentals'])
@pytest.mark.parametrize('lang,theme',[('en','dark'),('fr','light')])
def test_security_sections_with_observed_fixture(observed,view,lang,theme):
    app=app_at('security',lang,theme,security_view=view)
    assert not app.exception and not app.error
    if view in ('summary','volatility'):assert app.get('plotly_chart')

@pytest.mark.parametrize('page',['news','world','board'])
@pytest.mark.parametrize('lang,theme',[('en','dark'),('fr','light')])
def test_context_routes_render_offline(page,lang,theme):
    app=app_at(page,lang,theme)
    assert not app.exception and not app.error

@pytest.mark.parametrize('view',['quotes','news','events','sessions','portfolio'])
def test_board_views(view):
    app=app_at('board',board_view=view)
    assert not app.exception and not app.error


def test_board_add_remove_reorder_and_book_preservation(observed):
    app=app_at('security',board_ids=['SPX','AAPL'],board_ready=True)
    before=app.session_state.terminal.book.positions.copy()
    app.button(key='security_add_board').click().run()
    assert app.session_state.board_ids==['SPX','AAPL','NVDA']
    app.button_group(key='desk_section').set_value('board').run()
    app.selectbox(key='board_manage').set_value('NVDA').run()
    app.button(key='board_up').click().run()
    assert app.session_state.board_ids==['SPX','NVDA','AAPL']
    app.button(key='board_remove').click().run()
    assert app.session_state.board_ids==['SPX','AAPL']
    assert app.session_state.terminal.book.positions.equals(before)


def test_board_event_selection_reaches_the_selected_instrument(monkeypatch):
    from components import market_context
    called=[]
    monkeypatch.setattr(market_context,'corporate_events',lambda id:(called.append(id) or [],DataResult()))
    app=app_at('board',board_view='events',board_ids=['NVDA','AAPL'],board_ready=True)
    app.selectbox(key='board_event_id').set_value('AAPL').run()
    assert not app.exception and called[-1]=='AAPL'


def test_partial_calendar_failure_discloses_incomplete_coverage(monkeypatch):
    from components import market_context
    monkeypatch.setattr(market_context,'macro_events',lambda:([],{'BLS':DataResult(),'BEA':DataResult([],'fresh')}))
    app=app_at('world',world_view='events')
    assert not app.exception
    assert any('Calendar feeds unavailable: BLS' in item.value and 'incomplete' in item.value for item in app.caption)

@pytest.mark.parametrize('value',[None,{},['INVALID'],['NVDA']*31,[1],'<script>'])
def test_board_rejects_bad_configuration(value):
    with pytest.raises(ValueError):validate_board(value)


def test_options_transfer_preserves_chain_and_labels_assumptions(observed):
    from services.lab import LabState
    lab=LabState();before=lab.chain.copy()
    app=app_at('security',analytics_lab=lab)
    app.number_input(key='security_assumed_vol').set_value(31.).run()
    app.button(key='security_open_options').click().run()
    assert not app.exception and not app.error
    assert app.query_params['page']==['equity-derivatives']
    assert app.session_state.analytics_lab.position.volatility==.31
    assert 'NVDA' in app.session_state.analytics_lab.position_source
    assert 'user-assumed' in app.session_state.analytics_lab.position_source
    assert app.session_state.analytics_lab.chain.equals(before)
    app.button(key='return_security').click().run()
    assert app.query_params['security']==['NVDA']


def test_fx_transfer_opens_existing_workspace_with_pair_and_spot(observed):
    app=app_at('security');app.selectbox(key='security_search').set_value('EURUSD').run()
    quote=MarketService().quote('EURUSD').value
    app.button(key='security_open_fx').click().run()
    assert not app.exception and not app.error
    assert app.query_params['page']==['analytics']
    assert app.selectbox(key='fx_foreign').value=='EUR' and app.selectbox(key='fx_domestic').value=='USD'
    assert app.number_input(key='fx_spot_EUR_USD').value==pytest.approx(quote.price)
