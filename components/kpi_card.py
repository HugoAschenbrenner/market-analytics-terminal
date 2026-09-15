from hashlib import sha1
import streamlit as st
from core.i18n import t
from core.formatting import compact

def kpis(items):
    key = sha1("|".join(key for key, _ in items).encode()).hexdigest()[:12]
    with st.container(key="metrics-"+key):
        for col, (key, value) in zip(st.columns(len(items)), items):
            col.metric(t(key), compact(value) if isinstance(value, (float,int)) else value)
