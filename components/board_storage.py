from pathlib import Path
import streamlit as st
import streamlit.components.v2 as components
from core.board import board_ids,validate_board

def render_board_storage():
    result=components.component('mat_board_storage',html='<span class="board-storage"></span>',js=(Path(__file__).with_name('monitor')/'board.mjs').read_text())(
        key='board_storage',height=0,data={'ids':board_ids(),'ready':st.session_state.get('board_ready',False)},on_loaded_change=lambda:None,on_error_change=lambda:None)
    if result.error:st.session_state.board_storage_error=True
    if result.loaded and not st.session_state.get('board_ready',False):
        try:
            ids=result.loaded.get('ids')
            if ids is not None:st.session_state.board_ids=validate_board(ids)
        except (ValueError,AttributeError):st.session_state.board_storage_error=True
        st.session_state.board_ready=True
        st.rerun()
