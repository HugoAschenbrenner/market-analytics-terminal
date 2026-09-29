from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from engines.structured_products_valuation_engine import AutocallableValuationInputs
from engines.structured_risk_engine import correlation_factor, validate_note_inputs, value_note, bump_risk


@pytest.mark.parametrize('n', [2, 3, 5, 8])
@pytest.mark.parametrize('endpoint', ['lower', 'upper'])
def test_closed_psd_domain_and_bounded_common_random_risk(n, endpoint):
    rho = -1/(n-1) if endpoint == 'lower' else 1.
    factor = correlation_factor(n, rho)
    expected = np.full((n, n), rho); np.fill_diagonal(expected, 1.)
    np.testing.assert_allclose(factor @ factor.T, expected, atol=1e-14)
    i = AutocallableValuationInputs(initial_spots=(100.,)*n, volatilities=(.2,)*n, correlation=rho, simulations=500)
    result = value_note(i, (1.,)*n, 'Phoenix', True)
    risk = bump_risk(i, (1.,)*n, 'Phoenix', True)
    assert np.isfinite(result['paths']).all()
    assert np.isfinite(risk['correlation_1pct'])
    assert risk['correlation_method'] == 'bounded one-sided/secant bump'
    if endpoint == 'upper':
        np.testing.assert_allclose(result['paths'][:, :, 0], result['paths'][:, :, -1])
    value_note.cache_clear()
    np.testing.assert_array_equal(result['paths'], value_note(i, (1.,)*n, 'Phoenix', True)['paths'])
    with pytest.raises(ValueError):
        validate_note_inputs(replace(i, correlation=rho + (-.001 if endpoint == 'lower' else .001)))


@pytest.mark.parametrize('kwargs', [dict(simulations=1), dict(simulations=20001), dict(simulations=2.5),
                                   dict(maturity_years=31), dict(observations_per_year=13),
                                   dict(initial_spots=(100.,)*8, volatilities=(.2,)*8,
                                        simulations=20000, maturity_years=3, observations_per_year=12)])
def test_workload_and_input_limits_precede_allocation(kwargs):
    with pytest.raises(ValueError): validate_note_inputs(AutocallableValuationInputs(**kwargs))


@pytest.mark.parametrize('lang', ['en', 'fr'])
def test_independent_terms_and_modes_preserve_shared_book(monkeypatch, lang):
    from services import market_data
    monkeypatch.setattr(market_data, 'ensure_market', lambda *a, **k: pytest.fail('Independent route fetched book data'))
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=15)
    app.query_params.update(version='v2', page='structured-products', lang=lang)
    app.run()
    assert not app.exception and not app.error
    shared = deepcopy(app.session_state.terminal)
    assert app.get('plotly_chart')
    assert not any('update the book' in item.value or 'met à jour le portefeuille' in item.value for item in app.caption)
    assert app.slider[0].min == -.5 and app.slider[0].max == 1.
    product = next(w for w in app.selectbox if w.key and w.key.endswith('_kind'))
    product.set_value('Athena').run()
    assert not app.checkbox  # No meaningless memory control for Athena.
    apply = next(w for w in app.button if w.key and w.key.startswith('FormSubmitter:note_independent'))
    apply.click().run()
    assert not app.exception and not app.error
    assert next(iter(app.session_state.structured_lab.book.structured_terms.values()))['product'] == 'Athena'
    pd.testing.assert_frame_equal(app.session_state.terminal.book.positions, shared.book.positions)
    assert app.session_state.terminal.book.structured_terms == shared.book.structured_terms
    assert app.session_state.terminal.market == shared.market
    app.button_group(key='structured_mode').set_value('book').run()
    assert not app.exception and not app.error
    assert app.info  # Empty shared book is explicit; never replaced with a demo.
    app.button_group(key='structured_mode').set_value('lab').run()
    assert next(iter(app.session_state.structured_lab.book.structured_terms.values()))['product'] == 'Athena'


@pytest.mark.parametrize('correlation', [-.5, 1.])
def test_shared_book_zero_shock_is_zero_at_psd_endpoints(correlation):
    from services.structured_lab import demo_structured_lab
    from services.analytics import marked_positions
    from engines.desk_scenario_engine import DeskScenario, evaluate_scenario
    state = demo_structured_lab()
    next(iter(state.book.structured_terms.values()))['correlation'] = correlation
    result = evaluate_scenario(marked_positions(state), state.market, state.book, DeskScenario('zero'))
    assert result['pnl'] == pytest.approx(0., abs=1e-12)
    assert result['liquidity'] == 0.
