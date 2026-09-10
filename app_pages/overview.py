import html
import plotly.express as px
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import view_data
from services.analytics import marked_positions, nav

def render(state):
    frame = marked_positions(state)
    kpis([('nav',nav(state,frame)),('gross',float(frame.market_value.abs().sum())),('dv01',float(frame.dv01.sum())),('vega',float(frame.vega.sum()))])
    a,b = st.columns(2)
    with a:
        grouped = frame.assign(exposure=frame.market_value.abs()).groupby('asset_class',as_index=False).exposure.sum()
        chart(px.bar(grouped,x='asset_class',y='exposure',title=t('concentration'),labels={'asset_class':t('asset_class'),'exposure':t('exposure')}))
    with b:
        chart(px.bar(frame,x='ticker',y='dv01',title=t('dv01'),labels={'ticker':t('position'),'dv01':t('dv01')}))
    st.subheader(t('top_risks'))
    gross = frame.market_value.abs().sum()
    largest = frame.loc[frame.market_value.abs().idxmax()]
    insights = [t('insight.concentration',asset=largest.ticker,weight=abs(largest.market_value)/gross)]
    total_dv = frame.dv01.abs().sum()
    if total_dv:
        insights.append(t('insight.dv01',share=frame.loc[frame.maturity>=10,'dv01'].abs().sum()/total_dv))
    if (frame.asset_class=='Option').any():
        insights.append(t('insight.gamma',gamma=frame.gamma.sum()))
    insights.append(t('insight.fx',share=frame.loc[frame.currency!=state.book.base_currency,'market_value'].abs().sum()/gross,currency=state.book.base_currency))
    for insight in insights:
        st.markdown(f'<div class="risk-line">{html.escape(insight)}</div>',unsafe_allow_html=True)
    view_data(frame)
