from datetime import datetime, timedelta, timezone
from threading import Event, Lock
from pathlib import Path
import json
import os
import shutil
import subprocess

import pytest
from core.market_contracts import DataResult
from core.securities import TICKER_IDS
from services.market_monitor import MarketCache, MarketService
from tests.test_market_monitor import fixture_chart


def test_shared_quote_pool_is_nonblocking_bounded_and_single_flight(monkeypatch):
    service = MarketService()
    release, six_started = Event(), Event()
    calls, active, peak = [], [0], [0]
    lock = Lock()

    def fetch(id):
        with lock:
            calls.append(id); active[0] += 1; peak[0] = max(peak[0], active[0])
            if active[0] == 6: six_started.set()
        assert release.wait(5)
        with lock: active[0] -= 1
        return DataResult(status='unavailable')

    monkeypatch.setattr(service, 'quote', fetch)
    try:
        result = service.quote_snapshot(TICKER_IDS)
        assert all(r.status == 'loading' and r.value is None for r in result.values())
        assert six_started.wait(2)
        for _ in range(12): service.quote_snapshot(TICKER_IDS)
        assert len(calls) == 6  # Remaining requests are queued, never duplicated.
        release.set()
        service.quotes(TICKER_IDS)
        service.quote_snapshot(TICKER_IDS)
        assert peak[0] == 6 and len(calls) == len(set(TICKER_IDS))
        service.quote_snapshot(TICKER_IDS)
        assert len(calls) == len(set(TICKER_IDS))  # Failure cooldown.
    finally:
        release.set(); service.close()


def test_refresh_retains_observation_and_success_time_then_recovers(monkeypatch):
    from services import market_monitor
    clock = [datetime(2026, 9, 29, tzinfo=timezone.utc)]
    service = MarketService(MarketCache(clock=lambda: clock[0]))
    calls = []

    def fetch(url):
        calls.append(url)
        if len(calls) == 2: raise OSError('private provider response')
        return json.dumps(fixture_chart())

    monkeypatch.setattr(market_monitor, 'request_text', fetch)
    try:
        first = service.quotes(['NVDA'])['NVDA']
        service.quote_snapshot(['NVDA'])
        clock[0] += timedelta(minutes=6)
        refreshing = service.quote_snapshot(['NVDA'])['NVDA']
        assert refreshing.status == 'refreshing' and refreshing.value == first.value
        service.quotes(['NVDA'])
        stale = service.quote_snapshot(['NVDA'])['NVDA']
        assert stale.status == 'stale'
        assert stale.value.observed_at == first.value.observed_at
        assert stale.retrieved_at == first.retrieved_at
        assert 'private' not in stale.message
        service.quote_snapshot(['NVDA'])
        assert len(calls) == 2
        clock[0] += timedelta(seconds=61)
        recovered = service.quotes(['NVDA'])['NVDA']
        assert recovered.status == 'fresh' and len(calls) == 3
    finally: service.close()


@pytest.mark.parametrize('page', ['welcome', 'equity-derivatives'])
def test_independent_pages_finish_while_provider_is_still_blocked(monkeypatch, page):
    from streamlit.testing.v1 import AppTest
    from services.market_monitor import get_market_service
    release = Event()
    service = get_market_service()

    def blocked(id):
        release.wait(15)
        return DataResult()

    monkeypatch.setattr(service, 'quote', blocked)
    try:
        app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=5)
        app.query_params.update(version='v2', page=page)
        app.run()
        assert not app.exception and not app.error
        assert any(button.key == 'welcome-start' for button in app.button) if page == 'welcome' else app.get('plotly_chart')
        assert not release.is_set()
    finally: release.set()


def test_ticker_poll_updates_prices_without_restarting_animation():
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    assert node, 'Node.js is required.'
    subprocess.run([node, 'tests/js/ticker.test.mjs'], check=True, capture_output=True, text=True)
