from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.i18n import TRANSLATIONS
from core.models import TerminalState
from core.state import demo_book, validate_book, replace_book
from services.analytics import marked_positions

@pytest.mark.parametrize('name',['balanced','macro','options','structured'])
def test_demo_books_have_valid_positions(name):
    state=TerminalState(demo_book(name))
    assert np.isfinite(marked_positions(state).market_value).all()

def test_translation_catalog_is_complete_and_formats_match():
    import string
    assert TRANSLATIONS['en'].keys()==TRANSLATIONS['fr'].keys()
    for key in TRANSLATIONS['en']:
        fields=lambda s:{v for _,v,_,_ in string.Formatter().parse(s) if v}
        assert fields(TRANSLATIONS['en'][key])==fields(TRANSLATIONS['fr'][key])

def test_100_asset_book_and_theme_invariance():
    state=TerminalState(demo_book())
    row=state.book.positions.query("asset_class == 'Equity'").iloc[0]
    frame=pd.DataFrame([dict(row,id=f'asset-{i}',ticker=f'EQ{i}',mark_mode='Book') for i in range(100)])
    replace_book(state,frame)
    dark=marked_positions(state)
    state.ui.theme='light'; state.ui.language='fr'
    pd.testing.assert_frame_equal(dark,marked_positions(state))
    assert len(dark)==100

@pytest.mark.parametrize('field,value',[('price',0),('quantity',np.inf),('currency','ZZZ'),('asset_class','Unknown')])
def test_invalid_book_is_rejected_without_mutating_state(field,value):
    state=TerminalState(demo_book()); before=state.book.positions.copy(deep=True)
    frame=before.copy(); frame.loc[0,field]=value
    with pytest.raises(ValueError): replace_book(state,frame)
    pd.testing.assert_frame_equal(before,state.book.positions)

@pytest.mark.parametrize('page',['overview','markets','risk','derivatives','financing'])
@pytest.mark.parametrize('lang,theme',[('en','dark'),('fr','light')])
def test_workspaces_render(page,lang,theme):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page=page,lang=lang,theme=theme)
    app.run()
    assert not app.exception
    assert not app.error
    assert app.session_state.terminal.ui.language==lang
    assert app.session_state.terminal.ui.theme==theme

def test_one_shared_book_feeds_all_calculations():
    state=TerminalState(demo_book())
    before=marked_positions(state)
    edited=state.book.positions.copy(); edited.loc[edited.id=='spy-put','quantity']*=2
    replace_book(state,edited)
    after=marked_positions(state)
    assert after.set_index('id').loc['spy-put','vega']==pytest.approx(2*before.set_index('id').loc['spy-put','vega'])
    assert state.book.revision==1

def test_navigation_keeps_shared_book_language_and_theme():
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30).run()
    app.selectbox(key='demo_selector').set_value('options').run()
    app.selectbox(key='global_language').set_value('fr').run()
    app.selectbox(key='global_theme').set_value('light').run()
    app.button_group(key='workspace').set_value('risk').run()
    assert not app.exception
    assert app.session_state.terminal.book.name=='options'
    assert app.session_state.terminal.ui.language=='fr'
    assert app.session_state.terminal.ui.theme=='light'
    assert app.query_params['page']==['risk']
    assert app.session_state.terminal.ui.page=='risk'
