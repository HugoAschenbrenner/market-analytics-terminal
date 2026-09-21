"""Small bilingual copy helper for V2 monitoring, separate from pricing labels."""
import streamlit as st

def tr(en, fr):
    state=st.session_state.get('terminal')
    return fr if state and state.ui.language=='fr' else en

ASSETS={'Overview':'Vue globale','Equities':'Actions','Indexes':'Indices','FX':'Devises','Rates':'Taux','Commodities':'Matières premières','ETFs':'ETF','Volatility':'Volatilité','Crypto':'Crypto'}
def asset_label(value):return tr(value,ASSETS.get(value,value))
