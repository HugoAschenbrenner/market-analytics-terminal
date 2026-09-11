import numpy as np
import plotly.express as px
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.formula_panel import formula_panel,view_data
from components.kpi_card import kpis
from engines.rates_tools_engine import curve_trade

def render_curve_trade(state):
    st.subheader(t('curve_trade'))
    a,b,c=st.columns(3)
    structure=a.selectbox(t('trade_structure'),['2s10s','5s30s','2s5s10s'],key='curve_structure')
    view=b.selectbox(t('scenario'),['steepener','flattener'] if structure!='2s5s10s' else ['butterfly'],format_func=lambda x,lang=state.ui.language:t(x,lang))
    nominal=c.number_input(t('notional'),min_value=1000.,value=1e6,step=100000.,key='curve_notional')
    currency=st.selectbox(t('currency'),['USD','EUR'],key='curve_trade_currency')
    tenors={'2s10s':[2,10],'5s30s':[5,30],'2s5s10s':[2,5,10]}[structure]
    curve=state.market.curves[currency]['history'].iloc[-1]
    yields=np.interp(tenors,curve.index,curve.values)/100
    result=curve_trade(tenors,yields,nominal,state.valuation_date,view)
    kpis([('dv01',float(result['legs'].dv01.sum()))])
    a,b=st.columns(2)
    with a:chart(px.bar(result['legs'],x='tenor',y='dv01',title=t('curve_trade'),labels={'tenor':t('tenor'),'dv01':t('dv01')}))
    with b:
        frame=result['scenarios'].assign(scenario=result['scenarios'].scenario.map(t))
        chart(px.bar(frame,x='scenario',y='pnl',title=t('stress'),labels={'scenario':t('scenario'),'pnl':t('pnl')}))
    view_data(result['legs']);formula_panel('curve_trade.method')
