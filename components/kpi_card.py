import streamlit as st
from core.i18n import t
from core.formatting import compact

def kpis(items):
    for col, (key, value) in zip(st.columns(len(items)), items):
        col.metric(t(key), compact(value) if isinstance(value, (float,int)) else value)
