import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core.models import TerminalState
from core.state import demo_book
from core.i18n import TRANSLATIONS
from services.financing import repo_margin,repo_stress


def test_book_financing_distinguishes_capacity_loss_from_cash_need():
    state=TerminalState(demo_book());state.book.repo_cash=50.;state.book.repo_haircut=.1
    result,shortfall=repo_stress(state,100.,.2,0.)
    assert result.refinancing_liquidity_shortfall==pytest.approx(10.)
    assert shortfall==0
    state.book.repo_cash=90.
    assert repo_stress(state,100.,.2,0.)[1]==pytest.approx(10.)
    assert repo_margin(state,90.).collateral_transfer_amount==pytest.approx(10.)

@pytest.mark.parametrize('lang',['en','fr'])
@pytest.mark.parametrize('sub',['repo','lending','collateral'])
def test_financing_tabs_render(lang,sub):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page='financing',lang=lang);app.session_state['financing_tabs']=TRANSLATIONS[lang][sub]
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>0


def test_open_session_upgrade_preserves_positions():
    import streamlit as st
    from core.state import get_state
    state=TerminalState(demo_book())
    original=state.book.positions.copy()
    del state.book.structured_terms
    del state.book.financing_terms
    st.session_state['terminal']=state
    migrated=get_state()
    assert migrated.book.positions.equals(original)
    assert migrated.book.structured_terms=={}
    assert migrated.book.financing_terms=={}
    del st.session_state['terminal']
