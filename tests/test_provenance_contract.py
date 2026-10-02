from datetime import datetime, timedelta, timezone
import json
import pandas as pd
import pytest
from core.models import TerminalState
from core.state import demo_book
from core.provenance import metadata, observation_status
from services import market_data as md
from services.market_monitor import MarketCache


def test_demo_curve_is_fixed_and_labelled_at_the_actual_fixed_end_date():
    for ccy in ('USD', 'EUR'):
        first=md.synthetic_curve(ccy); second=md.synthetic_curve(ccy)
        pd.testing.assert_frame_equal(first,second)
        assert str(first.index[-1].date())=='2026-09-09'
    state=TerminalState(demo_book());md.ensure_market(state)
    for entry in [*state.market.curves.values(),*state.market.provenance.values()]:
        assert entry['observed_at']=='2026-09-09'
        assert entry['status']=='synthetic' and entry['retrieved_at'] is None
        assert 'fixed' in entry['frequency']


def test_failed_refresh_preserves_success_and_observation_but_advances_attempt(monkeypatch):
    state=TerminalState(demo_book());md.ensure_market(state)
    quote=dict(price=120.,source='PUBLIC',provider='fixture',as_of='2026-09-01',
               retrieved_at='2026-09-02T10:00:00+00:00',frequency='daily observation',status='available')
    state.market.provenance['SPY']=quote.copy()
    state.market.curves['USD'].update({k:v for k,v in quote.items() if k!='price'})
    state.market.curves['USD']['observed_at']='2026-09-01'
    md.ensure_market(state,refresh=True)
    for entry in [state.market.provenance['SPY'],state.market.curves['USD']]:
        assert entry['as_of']=='2026-09-01' and entry['retrieved_at']==quote['retrieved_at']
        assert entry['status']=='stale' and entry['attempted_at']>entry['retrieved_at']
    quote['as_of']='2026-09-28';quote['retrieved_at']='2026-09-29T09:00:00+00:00'
    monkeypatch.setattr(md,'load_public_context',lambda *a:{('quote','SPY'):quote})
    md.ensure_market(state,refresh=True)
    assert state.market.provenance['SPY']['status']=='available'
    assert state.market.provenance['SPY']['observed_at']=='2026-09-28'


def test_old_observation_stays_old_despite_recent_retrieval():
    info=dict(source='PUBLIC',as_of='2020-01-01',retrieved_at='2026-09-29T09:00:00Z',frequency='daily',status='available')
    assert observation_status(info,datetime(2026,9,29,tzinfo=timezone.utc))=='old'
    assert metadata(info)['observed_at']=='2020-01-01'
    assert metadata({'source':'PUBLIC','as_of':'2026-09-29'})['retrieved_at'] is None


def test_cache_times_distinguish_fetch_start_from_success_completion():
    now=[datetime(2026,9,29,tzinfo=timezone.utc)]
    cache=MarketCache(clock=lambda:now[0])
    def loader():
        now[0]+=timedelta(seconds=2)
        return 100.
    data=cache.get('price',loader)
    assert data.retrieved_at-data.attempted_at==timedelta(seconds=2)
    assert cache.get('price',lambda:pytest.fail('Cached success')).retrieved_at==data.retrieved_at


@pytest.mark.parametrize('timestamps', [[1,1],[2,1],[1,999999999999]])
def test_book_quote_rejects_duplicate_reversed_and_future_observations(monkeypatch,timestamps):
    fixture={'chart':{'result':[{'timestamp':timestamps,'indicators':{'quote':[{'close':[100.,102.]}]}}]}}
    monkeypatch.setattr(md,'read_url',lambda u:json.dumps(fixture))
    with pytest.raises(ValueError):md.fetch_quote('X')
