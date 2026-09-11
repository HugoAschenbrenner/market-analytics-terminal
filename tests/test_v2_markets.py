import json
import numpy as np
import pandas as pd
import pytest
from core.state import demo_book
from core.models import TerminalState
from services import market_data as md
from services.book_risk import book_risk
from engines.desk_scenario_engine import DeskScenario,evaluate_scenario,scenario_summary

def test_fred_and_ecb_parsers_preserve_dates_units_and_curve_basis():
    fred='observation_date,DGS1,DGS2,DGS5,DGS10,DGS30\n2026-09-07,4,4.1,4.2,4.3,4.4\n2026-09-08,4.1,4.2,4.3,4.4,4.5\n'
    us=md.parse_fred_csv(fred)
    assert us.iloc[-1][10]==4.4
    ecb='TIME_PERIOD,DATA_TYPE_FM,OBS_VALUE\n'+'\n'.join(f'{d},SR_{y}Y,{2+y/100}' for d in ['2026-09-07','2026-09-08'] for y in md.TENORS)
    euro=md.parse_ecb_csv(ecb)
    assert euro.iloc[-1][10]==2.1
    assert euro.index[-1]==us.index[-1]

def test_market_fallback_is_labelled_and_refresh_preserves_old_public_dates(monkeypatch):
    state=TerminalState(demo_book());md.ensure_market(state)
    assert state.market.source=='SYNTHETIC'
    state.market.provenance['SPY']=dict(price=100,source='PUBLIC',as_of='2020-01-01',provider='fixture',change=None)
    md.ensure_market(state,refresh=True)
    assert state.market.provenance['SPY']['as_of']=='2020-01-01'
    assert state.market.source=='MIXED'

def test_quote_rejects_bad_latest_and_keeps_missing_change(monkeypatch):
    fixture={'chart':{'result':[{'timestamp':[1,2],'indicators':{'quote':[{'close':[None,100.]}]}}]}}
    monkeypatch.setattr(md,'read_url',lambda u:json.dumps(fixture))
    assert md.fetch_quote('X')['change'] is None
    fixture['chart']['result'][0]['indicators']['quote'][0]['close'][-1]=None
    with pytest.raises((ValueError,TypeError)):md.fetch_quote('X')

def test_risk_and_scenarios_use_current_book_and_separate_liquidity():
    state=TerminalState(demo_book());risk=book_risk(state)
    assert risk['es']>=risk['var']>=0
    zero=evaluate_scenario(risk['marks'],state.market,state.book,DeskScenario('zero'))
    assert zero['pnl']==pytest.approx(0,abs=1e-8)
    assert zero['positions'].pnl.sum()==pytest.approx(zero['by_factor'].sum())
    assert scenario_summary(risk['marks'],state.market,state.book).liquidity.eq(0).all()
    state.book.repo_cash=100000;state.book.collateral_id='ust10'
    shock=evaluate_scenario(risk['marks'],state.market,state.book,DeskScenario('liquidity',haircut=.8))
    assert shock['liquidity']>0
    assert shock['pnl']==pytest.approx(0,abs=1e-8)
