"""V1 is frozen at a68b64c; all subsequent product work belongs to V2."""
import ast
import hashlib
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'tests/v1_frozen_manifest.json').read_text())


@pytest.mark.parametrize('path', MANIFEST['files'])
def test_v1_file_matches_frozen_reference(path):
    actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert actual == MANIFEST['files'][path], (
        f'{path} belongs to stable V1 at {MANIFEST["reference_commit"]}. '
        'Implement V2 changes in V2 modules; changing the freeze needs explicit V1 authorization.'
    )


def test_v1_import_closure_stays_inside_frozen_files():
    pending = ['terminal_v1.py']
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        assert path in MANIFEST['files'], f'Unfrozen V1 dependency: {path}'
        tree = ast.parse((ROOT / path).read_text())
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
                modules.extend(node.module + '.' + alias.name for alias in node.names)
        for module in modules:
            for candidate in (module.replace('.', '/') + '.py', module.replace('.', '/') + '/__init__.py'):
                if (ROOT / candidate).is_file():
                    pending.append(candidate)
    assert 'app_pages/equity_derivatives.py' not in seen
    assert 'services/lab.py' not in seen
    assert 'core/i18n.py' not in seen


@pytest.mark.parametrize('version', [None, 'v1', 'invalid'])
@pytest.mark.parametrize('language', ['en', 'fr'])
def test_v2_only_route_cannot_activate_lab_in_v1(version, language):
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=40)
    app.query_params.update(page='equity-derivatives', lang=language)
    if version is not None:
        app.query_params['version'] = version
    app.run()
    assert not app.exception and not app.error
    assert any(item.value == 'Multi-Asset Desk Utility Platform' for item in app.title)
    assert 'terminal' not in app.session_state and 'analytics_lab' not in app.session_state
    assert not any(item.key == 'eqd_view' for item in app.button_group)
    assert not any('Equity Derivatives' in item.value for item in app.markdown)


@pytest.mark.parametrize('page', ['home', 'fixed-income-risk', 'repo-sec-lending',
                                  'structured-products', 'portfolio-risk', 'cross-asset-dashboard'])
def test_all_frozen_v1_routes_render_without_v2_lab(page, monkeypatch):
    from engines import market_data_engine as quotes, rates_market_data_engine as rates
    # Deterministic unavailable quotes + labelled sample Treasury curve. The UI
    # still renders its complete original market panels without network requests.
    def empty_quotes(symbols, **kwargs):
        return quotes._empty_payload(list(symbols), 'unavailable', 'Offline test')
    monkeypatch.setattr(quotes, 'fetch_yfinance_quotes', empty_quotes)
    monkeypatch.setattr(rates, 'fetch_yfinance_quotes', empty_quotes)
    monkeypatch.setattr(rates, 'fetch_treasury_yield_curve', lambda **kwargs: rates.build_sample_treasury_curve_payload())
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=40)
    app.query_params.update(page=page)
    app.run()
    assert not app.exception and not app.error
    assert 'terminal' not in app.session_state and 'analytics_lab' not in app.session_state
    assert not any((item.key or '').startswith('lab_') or (item.key or '').startswith('eqd_')
                   for item in [*app.number_input, *app.selectbox, *app.slider, *app.button])
    if page == 'structured-products':
        assert any(item.value == 'Black-Scholes-Merton Pricer & Greeks' for item in app.subheader)
        assert app.number_input(key='bsm_spot').value == 100.
