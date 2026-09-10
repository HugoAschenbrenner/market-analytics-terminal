import numpy as np
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis

def render(state):
    tabs = st.tabs([t('rates'),t('fx'),t('equity_vol')],key='markets_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            tenor=np.array([1,2,5,10,30])
            fig=go.Figure()
            for currency in ['USD','EUR']:
                fig.add_scatter(x=tenor,y=(state.market.rates[currency]+np.array([.002,0,-.001,.001,.005]))*100,name=currency)
            fig.update_layout(title=t('curve'),xaxis_title=t('tenor'),yaxis_title=t('yield'))
            chart(fig,height=350)
            st.caption(t('SYNTHETIC'))
    if tabs[1].open:
        with tabs[1]:
            kpis([('spot',state.market.fx['EUR']),('rate',100*state.market.rates['USD'])])
    if tabs[2].open:
        with tabs[2]:
            cols=st.columns(3)
            for col,ticker in zip(cols,['SPY','QQQ','VIX']):
                col.metric(ticker,str(state.market.spots[ticker]))
            st.caption(t(state.market.source))
