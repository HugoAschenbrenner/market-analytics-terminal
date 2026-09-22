"""V2-only dataframe surfaces; keep existing numeric values and interaction APIs."""
import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler
from core.v2_theme import TOKENS
from core.state import get_state


def compact_table(data,*,index=False):
    """Small read-only market tables with theme-aware headers and safe text."""
    frame=data if isinstance(data,pd.DataFrame) else pd.DataFrame(data)
    markup=frame.to_html(index=index,escape=True,border=0,classes='workshop-table')
    st.markdown('<div class="workshop-table-wrap">'+markup+'</div>',unsafe_allow_html=True)


def themed_dataframe(data=None,**kwargs):
    # Retain intentional conditional color maps provided by existing analytics.
    if data is not None and not isinstance(data,Styler):
        try:
            frame=data if isinstance(data,pd.DataFrame) else pd.DataFrame(data)
            colors=TOKENS[get_state().ui.theme]
            data=frame.style.set_properties(**{'background-color':colors['surface'],'color':colors['text_primary'],'border-color':colors['border']})
        except (ValueError,TypeError):pass
    return st.dataframe(data,**kwargs)
