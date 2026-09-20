"""Public entry point: V1 remains the default; V2 is an explicit opt-in."""
import streamlit as st


version = "v2" if st.query_params.get("version") == "v2" else "v1"
st.set_page_config(
    page_title="Market Analytics Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" if version == "v2" else "auto",
)

# Import only the selected interface. Both versions share the audited engines.
if version == "v2":
    from terminal_v2 import render
else:
    from terminal_v1 import render

render()
