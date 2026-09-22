from components.themed_table import themed_dataframe
import streamlit as st
from core.i18n import t

def formula_panel(key, formulas=()):
    with st.expander(t("methodology")):
        st.write(t(key))
        for formula in formulas:
            st.latex(formula)

def view_data(frame):
    with st.expander(t("data")):
        themed_dataframe(frame, width="stretch")
