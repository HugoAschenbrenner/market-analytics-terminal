import numpy as np
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import formula_panel, view_data
from services.analytics import marked_positions
from engines.options_pricing_engine import black_scholes_price

def render(state):
    frame=marked_positions(state)
    options=frame[frame.asset_class=='Option']
    if options.empty:
        st.info(t('option.none'))
        return
    selected=st.selectbox(t('option.select'),options.id.tolist(),key='book_option')
    row=options.set_index('id').loc[selected]
    tabs=st.tabs([t('vanilla'),t('greeks')],key='derivative_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            kpis([('option.price',float(row.mark)),('delta',float(row.delta)),('vega',float(row.vega)),('gamma',float(row.gamma))])
            spots=np.linspace(row.spot*.65,row.spot*1.35,60)
            values=[black_scholes_price(row.option_type,s,row.strike,row.maturity,state.market.rates[row.currency],row.volatility) for s in spots]
            fig=go.Figure(go.Scatter(x=spots,y=values))
            fig.update_layout(title=t('option.price'),xaxis_title=t('spot'),yaxis_title=t('value'))
            chart(fig)
            formula_panel('option.method',[r'C=S e^{-qT}N(d_1)-K e^{-rT}N(d_2)',r'd_1=\frac{\ln(S/K)+(r-q+\sigma^2/2)T}{\sigma\sqrt T},\quad d_2=d_1-\sigma\sqrt T'])
    if tabs[1].open:
        with tabs[1]:
            chart(go.Figure(go.Bar(x=options.id,y=options.vega)).update_layout(title=t('vega'),xaxis_title=t('position'),yaxis_title=t('vega')))
            view_data(options)
