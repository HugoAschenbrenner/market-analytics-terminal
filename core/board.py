"""Personal monitoring IDs only: no positions, credentials or provider data stored."""
import streamlit as st
from core.securities import SECURITIES
DEFAULT_BOARD=['SPX','NVDA','EURUSD','US10Y','GOLD']

def validate_board(value):
    if not isinstance(value,list) or len(value)>30 or any(not isinstance(v,str) or v not in SECURITIES for v in value):raise ValueError('Use up to 30 supported instrument IDs.')
    return list(dict.fromkeys(value))

def board_ids():
    if 'board_ids' not in st.session_state:st.session_state.board_ids=list(DEFAULT_BOARD)
    return st.session_state.board_ids

def set_board(value):
    st.session_state.board_ids=validate_board(value)
    st.session_state.board_revision=st.session_state.get('board_revision',0)+1
    st.session_state.board_ready=True

def add_to_board(id):
    values=board_ids()
    if id not in values and len(values)<30:set_board([*values,id])

def remove_from_board(id):set_board([v for v in board_ids() if v!=id])

def reorder_board(id,direction):
    values=list(board_ids());i=values.index(id);j=i+direction
    if 0<=j<len(values):values[i],values[j]=values[j],values[i];set_board(values)
