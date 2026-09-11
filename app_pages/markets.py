import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import formula_panel,view_data
from components.chart_card import curve_chart
from components.data_status import data_status,market_strip
from services.market_data import ensure_market,curve_overlay
from services.analytics import marked_positions

def render(state):
    if st.button(t('refresh')):
        ensure_market(state,refresh=True); st.rerun()
    tabs=st.tabs([t('rates'),t('fx'),t('equity_vol')],key='markets_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            from components.rates_workspace import render_rates
            render_rates(state)
    if tabs[1].open:
        with tabs[1]:
            from components.fx_workspace import render_fx
            render_fx(state)
    if tabs[2].open:
        with tabs[2]:
            market_strip(state)
            frame=pd.DataFrame([dict(ticker=k,**v) for k,v in state.market.provenance.items() if k in ['SPY','QQQ','VIX']])
            chart(px.bar(frame.assign(change=frame.change*100),x='ticker',y='change',title=t('quote.change'),labels={'ticker':t('position'),'change':t('quote.change')}))
            formula_panel('quote.method');view_data(frame)
