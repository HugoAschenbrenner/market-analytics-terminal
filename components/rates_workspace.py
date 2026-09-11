import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.chart_card import curve_chart
from components.data_status import data_status
from components.formula_panel import formula_panel,view_data
from components.kpi_card import kpis
from components.curve_trade import render_curve_trade
from services.market_data import curve_overlay
from services.analytics import marked_positions
from engines.rates_tools_engine import carry_roll,yield_price_curve,key_rate_ladder

def render_rates(state):
    tabs=st.tabs([t('curve'),t('curve.bucket'),t('curve_trade')],key='rates_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            curve_chart(state,history=True,height=300)
            for col,(currency,payload) in zip(st.columns(2),state.market.curves.items()):
                with col:
                    data_status(payload);last=curve_overlay(payload);prior=curve_overlay(payload,7)
                    st.metric(f'{currency} 2s10s / 5s30s',f'{(last[10]-last[2])*100:.1f} / {(last[30]-last[5])*100:.1f} bp')
                    st.caption(t('curve.regime')+' · '+t('curve.normal' if last[10]>=last[2] else 'curve.inverted'))
                    if prior is not None:chart(go.Figure(go.Bar(x=last.index,y=(last-prior)*100)).update_layout(title=t('curve.change'),xaxis_title=t('tenor'),yaxis_title='bp'),height=210)
            formula_panel('rates.method')
    if tabs[1].open:
        with tabs[1]:
            bonds=marked_positions(state).query("asset_class == 'Bond'")
            if bonds.empty:
                st.info(t('financing.none'));return
            ladder=key_rate_ladder(bonds,state)
            a,b=st.columns(2)
            with a:chart(px.bar(ladder.set_index('id').drop(columns='currency').T,title=t('curve.bucket'),labels={'index':t('tenor'),'value':t('dv01'),'id':t('position')}))
            with b:chart(px.bar(bonds,x='ticker',y='cs01',title=t('cs01'),labels={'ticker':t('position'),'cs01':t('cs01')}))
            estimates=carry_roll(bonds,state.market.curves)
            kpis([('carry',float(estimates.carry.sum())),('roll',float(estimates['roll'].sum()))])
            selected=st.selectbox(t('position'),bonds.id.tolist(),key='convexity_bond')
            curve=yield_price_curve(bonds.set_index('id').loc[selected],state)
            chart(px.line(curve,x='yield',y='price',title=t('bond.convexity'),labels={'yield':t('yield'),'price':t('value')}))
            formula_panel('carry.method');view_data(bonds)
    if tabs[2].open:
        with tabs[2]:render_curve_trade(state)
