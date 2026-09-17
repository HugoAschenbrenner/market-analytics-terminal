"""Streamlit shell for the self-contained, offline Interactive Greeks Lab.

Ship reviewed ES modules as one inline v2 component: no build step, CDN, iframe,
Python callback or external asset dependency in the live interaction loop.
Node is only needed to run cross-runtime financial tests, not to deploy MAT.
"""
from pathlib import Path
import re

import streamlit.components.v2 as components

from core.greeks_lab_copy import lab_copy
from core.theme import TOKENS

ASSETS = Path(__file__).with_name('greeks_lab')


def component_source():
    modules = ['engine', 'state', 'curves', 'format', 'render']
    # All imports are our static one-line relative module imports. Their exports
    # remain valid within the resulting ES module, with one default lifecycle.
    return '\n'.join(re.sub(r'^import .*?;\n', '', (ASSETS/f'{name}.mjs').read_text(), flags=re.M)
                     for name in modules)


def lab_component():
    # Registration is idempotent for identical content in Streamlit 1.63.
    # Bind to the active runtime, including fresh AppTest runtimes; do not retain
    # an import-time callable whose registration belongs to a previous runtime.
    return components.component('mat_interactive_greeks',
        html='<div class="lab"></div>', css=(ASSETS/'lab.css').read_text(),
        js=component_source(), isolate_styles=True)


def render_interactive_greeks(state):
    lab_component()(key='interactive_greeks_lab', height='content', data={
        'copy': lab_copy(state.ui.language), 'language': state.ui.language,
        'theme': state.ui.theme, 'tokens': TOKENS[state.ui.theme],
    })
