import ast
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core.i18n import TRANSLATIONS


def test_all_literal_translation_keys_exist():
    for folder in ['core','components','app_pages']:
        for p in Path(folder).glob('*.py'):
            for n in ast.walk(ast.parse(p.read_text())):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='t' and n.args and isinstance(n.args[0],ast.Constant):
                    assert n.args[0].value in TRANSLATIONS['en'],(p,n.args[0].value)

@pytest.mark.parametrize('lang',['en','fr'])
def test_custom_scenario_survives_navigation(lang):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30)
    app.query_params.update(page='risk',lang=lang);app.session_state['risk_tabs']=TRANSLATIONS[lang]['stress'];app.run()
    app.selectbox(key='scenario_select').set_value('custom').run()
    equity=next(x for x in app.slider if x.label==TRANSLATIONS[lang]['equity']);equity.set_value(-23.).run()
    app.button_group(key='workspace').set_value('overview').run()
    app.button_group(key='workspace').set_value('risk').run()
    app.session_state['risk_tabs']=TRANSLATIONS[lang]['stress'];app.run()
    assert not app.error
    assert app.session_state.terminal.scenario.shocks['equity']==-.23

@pytest.mark.parametrize('view',['price_surface','gamma_surface','vega_surface'])
def test_greek_heatmaps_render(view):
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=30);app.query_params['page']='derivatives';app.session_state['derivative_tabs']=TRANSLATIONS['en']['greeks'];app.run()
    next(x for x in app.selectbox if x.label==TRANSLATIONS['en']['greeks.view']).set_value(view).run()
    assert not app.exception
    assert not app.error
