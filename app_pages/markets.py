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
            curve_chart(state,history=True,height=310)
            a,b=st.columns(2)
            for col,(currency,payload) in zip([a,b],state.market.curves.items()):
                with col:
                    data_status(payload)
                    last=curve_overlay(payload); prior=curve_overlay(payload,7)
                    st.metric(f'{currency} 2s10s / 5s30s',f'{(last[10]-last[2])*100:.1f} / {(last[30]-last[5])*100:.1f} bp')
                    st.caption(t('curve.regime')+' · '+t('curve.normal' if last[10]>=last[2] else 'curve.inverted'))
                    if prior is not None: chart(go.Figure(go.Bar(x=last.index,y=(last-prior)*100)).update_layout(title=t('curve.change'),xaxis_title=t('tenor'),yaxis_title='bp'),height=210)
            bonds=marked_positions(state).query("asset_class == 'Bond'")
            if not bonds.empty:
                a,b=st.columns(2)
                with a: chart(px.bar(bonds,x='maturity',y='dv01',color='ticker',title=t('curve.bucket'),labels={'maturity':t('tenor'),'dv01':t('dv01')}))
                with b: chart(px.bar(bonds,x='ticker',y='cs01',title=t('cs01'),labels={'ticker':t('position'),'cs01':t('cs01')}))
                view_data(bonds)
            formula_panel('rates.method')
    if tabs[1].open:
        with tabs[1]:
            market_strip(state)
            frame=pd.DataFrame([dict(ticker=k,**v) for k,v in state.market.provenance.items() if k in ['EURUSD','GBPUSD','USDJPY']])
            chart(px.bar(frame,x='ticker',y='change',title=t('fx'),labels={'ticker':t('position'),'change':t('exposure')}))
            formula_panel('quote.method');view_data(frame)
    if tabs[2].open:
        with tabs[2]:
            market_strip(state)
            frame=pd.DataFrame([dict(ticker=k,**v) for k,v in state.market.provenance.items() if k in ['SPY','QQQ','VIX']])
            chart(px.bar(frame,x='ticker',y='change',title=t('equity_vol'),labels={'ticker':t('position'),'change':t('exposure')}))
            formula_panel('quote.method');view_data(frame)
