"""Reproducible local timings, isolated from provider availability and CI tests.

Run from the repository root: python scripts/benchmark_workstation.py
The controlled outage sleeps 0.15s per request before failing. These are local
AppTest/service timings, not browser paint times or Streamlit Cloud promises.
"""
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
started = time.perf_counter()
from streamlit.testing.v1 import AppTest
from services import market_monitor, market_data
from services.lab import LabState
from reports.lab_report import generate_lab_report
from engines.equity_derivatives_engine import scenario_matrix, OptionPosition
from engines.structured_products_valuation_engine import AutocallableValuationInputs
from engines.structured_risk_engine import value_note
from core.state import position, validate_book
from core.models import PositionBook, TerminalState
from services.book_risk import book_risk
import pandas as pd


def measure(action):
    start = time.perf_counter()
    result = action()
    return result, round(time.perf_counter() - start, 4)


def main():
    results = {'imports_seconds': round(time.perf_counter() - started, 4),
               'provider_fixture': '0.15 seconds per request then OSError; no network'}
    calls = []

    def unavailable(url):
        calls.append(url)
        time.sleep(.15)
        raise OSError('Controlled provider outage')

    with patch.object(market_monitor, 'request_text', unavailable), patch.object(market_data, 'load_public_context', return_value={}):
        for page in ('welcome', 'equity-derivatives', 'structured-products'):
            market_monitor.get_market_service.clear()
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=60)
            app.query_params.update(version='v2', page=page)
            _, cold = measure(app.run)
            assert not app.exception, app.exception
            _, warm = measure(app.run)
            assert not app.exception, app.exception
            results[page] = {'cold_seconds': cold, 'warm_seconds': warm}
            current = market_monitor.get_market_service()
            if hasattr(current, 'close'): current.close()
        service = market_monitor.MarketService()
        _, failed = measure(lambda: service.quotes(('SPX', 'NVDA', 'DE10Y')))
        _, cached = measure(lambda: service.quotes(('SPX', 'NVDA', 'DE10Y')))
        results['market_failure'] = {'cold_seconds': failed, 'cached_seconds': cached}
        # Drain only benchmark-created background jobs, while the outage fixture
        # is still installed. This does not add their wait to UI timings.
        if hasattr(service, 'close'): service.close()
        current = market_monitor.get_market_service()
        if hasattr(current, 'close'): current.close()
    rows = [position(f'e{i}', f'DEMO{i}', 'Equity', 10, 100, mark_mode='Book') for i in range(100)]
    state = TerminalState(PositionBook(validate_book(pd.DataFrame(rows))))
    _, results['portfolio_100_seconds'] = measure(lambda: book_risk(state))
    _, results['option_matrix_35_cells_seconds'] = measure(lambda: scenario_matrix(OptionPosition()))
    inputs = AutocallableValuationInputs(initial_spots=(100., 100., 100.), volatilities=(.2, .25, .3), simulations=10000)
    value_note.cache_clear()
    _, results['structured_10000_paths_seconds'] = measure(lambda: value_note(inputs, (1., 1., 1.), 'Phoenix', True))
    report, results['lab_report_seconds'] = measure(lambda: generate_lab_report(LabState()))
    results['report_bytes'] = len(report)
    results['provider_requests'] = len(calls)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
