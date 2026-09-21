from copy import deepcopy
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from core.i18n import TRANSLATIONS
from services import market_data


def app_test(**query):
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=30)
    app.query_params.update(query, version='v2')
    return app


@pytest.mark.parametrize('lang', ['en', 'fr'])
@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_welcome_renders_in_both_languages_and_themes(lang, theme):
    app = app_test(lang=lang, theme=theme).run()
    assert not app.exception and not app.error
    assert app.session_state.terminal.ui.page == 'welcome'
    assert any(TRANSLATIONS[lang]['welcome.title'] in item.value for item in app.markdown)
    assert len(app.button) == 7  # Start plus six focused workspace cards.
    assert not app.metric and not app.get('plotly_chart')
    assert not any(box.key == 'demo_selector' for box in app.selectbox)


@pytest.mark.parametrize('page', ['overview', 'markets', 'risk', 'equity-derivatives', 'structured-products', 'financing'])
def test_menu_enters_workspace_and_returns_without_resetting_edits(page):
    state = TerminalState(demo_book('options'))
    state.book.positions.loc[state.book.positions.id == 'spy-put', 'quantity'] = -7
    state.book.source = 'USER INPUT'
    before = deepcopy(state.book)
    app = app_test(lang='fr', theme='light')
    app.session_state.terminal = state
    # Existing sessions keep their language/theme in state.
    state.ui.language = 'fr'; state.ui.theme = 'light'
    app.run()
    app.button(key='welcome-open-' + page).click().run()
    assert not app.exception and not app.error
    assert app.query_params['page'] == [page]
    assert app.session_state.terminal.ui.page == page
    pd.testing.assert_frame_equal(before.positions, app.session_state.terminal.book.positions)
    app.button_group(key='desk_section').set_value('markets').run()
    app.button_group(key='workspace').set_value('welcome').run()
    assert not app.exception and not app.error
    assert app.session_state.terminal.ui.page == 'welcome'
    assert app.session_state.terminal.ui.language == 'fr'
    assert app.session_state.terminal.ui.theme == 'light'
    assert app.session_state.terminal.book.source == 'USER INPUT'
    pd.testing.assert_frame_equal(before.positions, app.session_state.terminal.book.positions)
    assert app.session_state.terminal.book.repo_cash == before.repo_cash


def test_first_visit_defers_data_loading_until_start(monkeypatch):
    calls = []
    original = market_data.ensure_market
    def track(state):
        calls.append(state)
        return original(state)
    monkeypatch.setattr(market_data, 'ensure_market', track)
    app = app_test().run()
    assert not calls and not app.exception
    app.button(key='welcome-start').click().run()
    assert calls and not app.exception and not app.error
    assert app.session_state.terminal.ui.page == 'overview'
    assert app.query_params['page'] == ['overview']
    assert app.metric


def test_unknown_route_returns_to_welcome():
    app = app_test(page='missing-workspace').run()
    assert not app.exception and not app.error
    assert app.session_state.terminal.ui.page == 'welcome'
