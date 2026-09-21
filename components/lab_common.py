"""Small bilingual presentation helpers; existing chart theme stays authoritative."""
import streamlit as st
from core.charting import style_figure


def language() -> str:
    state=st.session_state.get('terminal')
    return state.ui.language if state and st.query_params.get('version')=='v2' else st.query_params.get('lang','en')


def tr(en: str, fr: str) -> str:
    return fr if language()=='fr' else en


def plot(figure,key: str,height: int=330):
    state=st.session_state.get('terminal')
    theme=state.ui.theme if state and st.query_params.get('version')=='v2' else 'light'
    st.plotly_chart(style_figure(figure,theme,height),key=key,width='stretch',theme=None,
                   config={'displayModeBar':False,'responsive':True,'scrollZoom':False})


def metric_value(value,percent=False):
    return 'N/A' if value is None else f'{value:.2%}' if percent else f'{value:.5g}' if 0<abs(value)<.01 else f'{value:,.4f}' if abs(value)<1 else f'{value:,.2f}'


def metrics(items):
    for column,(label,value) in zip(st.columns(len(items)),items):
        column.metric(label,value)


def table(data,label=None):
    with st.expander(label or tr('Data & calculation details','Données et détails du calcul')):
        st.dataframe(data,width='stretch',hide_index=True)
