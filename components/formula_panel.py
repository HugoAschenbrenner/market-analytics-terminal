import streamlit as st
from core.i18n import t

def formula_panel(key, formulas=()):
    with st.expander(t("methodology")):
        st.write(t(key))
        for formula in formulas:
            st.latex(formula)

def view_data(frame):
    with st.expander(t("data")):
        st.dataframe(frame, width="stretch")
