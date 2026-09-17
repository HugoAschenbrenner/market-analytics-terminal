from streamlit.testing.v1 import AppTest


def test_responsive_controls_render_with_the_installed_streamlit():
    # V2 pins Streamlit 1.63. Exercise its API instead of the legacy source-text
    # ban: width="stretch" is supported and already used by shared components.
    app = AppTest.from_string('''
import streamlit as st
with st.container(height="stretch"):
    st.button("Open workspace", width="stretch")
st.segmented_control("Workspace", ["Start", "Markets"], width="stretch")
st.dataframe({"Value": [1, 2]}, width="stretch")
''').run()
    assert not app.exception
    assert len(app.button) == len(app.button_group) == len(app.dataframe) == 1
