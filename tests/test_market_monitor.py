from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import pandas as pd
import pytest
from core.securities import SECURITIES, search_securities
from core.market_formatting import level, move, large
from core.market_contracts import Quote
from services.market_monitor import MarketCache, MarketService, parse_chart, parse_fred, chart_quote, observation_is_old

UTC=timezone.utc


@pytest.mark.parametrize('query,expected',[('Nvidia','NVDA'),('Apple','AAPL'),('S&P 500','SPX'),('CAC 40','CAC'),('EUR/USD','EURUSD'),('US 10Y','US10Y'),('Gold','GOLD'),('BNP.PA','BNP')])
def test_search_has_stable_security_identity(query,expected):
    assert expected in [s.id for s in search_securities(query)]


def fixture_chart():
    return {'chart':{'result':[{'meta':{'chartPreviousClose':50.,'regularMarketPrice':103.,'regularMarketTime':int(datetime(2026,9,18,18,tzinfo=UTC).timestamp())},
        'timestamp':[int(datetime(2026,9,d,14,tzinfo=UTC).timestamp()) for d in (16,17,18)],
        'indicators':{'quote':[{'open':[99,100,102],'high':[101,103,105],'low':[98,99,101],'close':[100,102,104],'volume':[1000,1100,1200]}],
                      'adjclose':[{'adjclose':[50,51,52]}]}}]}}


def test_daily_move_does_not_use_start_of_range_close():
    s=SECURITIES['NVDA'];parsed=parse_chart(fixture_chart(),s)
    q=chart_quote(s,parsed)
    assert q.price==103 and q.previous_close==102
    assert q.change_pct==pytest.approx(100/102)
    assert parsed[0].adjusted_close.iloc[-1]==52
    assert q.observed_at.hour==18


def test_invalid_last_bar_uses_last_real_observation_without_fabrication():
    data=fixture_chart();result=data['chart']['result'][0]
    result['meta']={};result['indicators']['quote'][0]['close'][-1]=None
    q=chart_quote(SECURITIES['NVDA'],parse_chart(data,SECURITIES['NVDA']))
    assert q.price==102 and q.observed_at.day==17


def test_yield_preserves_negative_levels_and_basis_point_change():
    s=SECURITIES['US10Y']
    raw=parse_fred('observation_date,DGS10\n2026-09-17,-0.10\n2026-09-18,-0.057\n',s)
    q=chart_quote(s,raw)
    assert level(s,q.price)=='-0.06%'
    assert move(s,q)=='+4.3 bp'
    assert q.frequency=='daily observation'


def test_formatting_distinguishes_fx_price_yield_and_large_values():
    assert level(SECURITIES['EURUSD'],1.1742)=='1.1742'
    assert level(SECURITIES['US10Y'],4.12)=='4.12%'
    assert large(3.12e12)=='3.12T'
    assert large(None)=='—'


def test_failure_keeps_last_success_timestamp_and_avoids_retries():
    clock=[datetime(2026,9,21,tzinfo=UTC)];cache=MarketCache(lambda:clock[0])
    calls=[]
    first=cache.get('x',lambda:123.,ttl=300)
    clock[0]+=timedelta(minutes=6)
    def fail():calls.append(1);raise OSError('private provider detail')
    stale=cache.get('x',fail,ttl=300)
    assert stale.value==123 and stale.status=='stale'
    assert stale.retrieved_at==first.retrieved_at
    assert 'private' not in stale.message
    assert cache.get('x',fail).status=='stale' and len(calls)==1
    clock[0]+=timedelta(minutes=2)
    assert cache.get('x',lambda:125).value==125


def test_cold_failure_does_not_produce_price():
    cache=MarketCache()
    def fail():raise ValueError('invalid')
    result=cache.get('x',fail)
    assert result.status=='unavailable' and result.value is None


def test_single_flight_and_bounded_cache():
    cache=MarketCache(capacity=3);calls=[]
    def load():calls.append(1);return 42
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(lambda _:cache.get('same',load),range(12)))
    assert len(calls)==1 and all(r.value==42 for r in results)
    for i in range(10):cache.get(i,load)
    assert len(cache.entries)==3


def test_quotes_and_daily_history_share_request(monkeypatch):
    from services import market_monitor as m
    calls=[]
    monkeypatch.setattr(m,'request_text',lambda url:(calls.append(url),json.dumps(fixture_chart()))[1])
    service=MarketService();a=service.quote('NVDA');service.quotes(['NVDA']);service.history('NVDA','1Y')
    assert len(calls)==1 and a.value.price==103


def test_old_observation_detected_separately_from_cache_freshness():
    q=Quote('NVDA',100,None,datetime(2026,9,1,tzinfo=UTC),'USD','fixture')
    assert observation_is_old(SECURITIES['NVDA'],q,datetime(2026,9,21,tzinfo=UTC))
    assert not observation_is_old(SECURITIES['DE10Y'],q,datetime(2026,9,21,tzinfo=UTC))


def test_treasury_tenors_share_year_reads_and_use_dated_previous_observation(monkeypatch):
    from services import market_monitor
    from urllib.parse import urlparse,parse_qs
    calls=[]
    def request(url):
        year=int(parse_qs(urlparse(url).query)['field_tdr_date_value'][0]);calls.append(year)
        return f'''<feed xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><m:properties><d:NEW_DATE>{year}-01-02</d:NEW_DATE><d:BC_2YEAR>4.00</d:BC_2YEAR><d:BC_10YEAR>4.20</d:BC_10YEAR></m:properties><m:properties><d:NEW_DATE>{year}-01-03</d:NEW_DATE><d:BC_2YEAR>3.95</d:BC_2YEAR><d:BC_10YEAR>4.10</d:BC_10YEAR></m:properties></feed>'''
    monkeypatch.setattr(market_monitor,'request_text',request)
    service=market_monitor.MarketService()
    first=service.quote('US2Y');second=service.quote('US10Y')
    assert len(calls)==2 and len(set(calls))==2
    assert first.value.change==pytest.approx(-.05)
    assert second.value.change==pytest.approx(-.1)
    assert 'US Treasury' in second.value.source
    assert service.history('US10Y','5Y').value is not None
    assert len(calls)==6  # Expanded history reuses the two already retrieved years.
