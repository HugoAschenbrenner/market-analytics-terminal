import html
import plotly.express as px
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import view_data
from components.data_status import market_strip
from components.chart_card import curve_chart
from services.book_risk import book_risk
from engines.desk_scenario_engine import scenario_summary

def render(state):
    market_strip(state)
    risk=book_risk(state); frame=risk['marks']
    stress=scenario_summary(frame,state.market,state.book)
    worst=stress.loc[stress.pnl.idxmin()]
    kpis([('nav',risk['nav']),('es',float(risk['es'])),('dv01',float(frame.dv01.sum())),('vega',float(frame.vega.sum())),('worst_loss',float(worst.pnl)),('liquidity',float(stress.liquidity.max()))])
    st.caption(t('risk.synthetic')+f" · {state.risk.confidence:.1%}")
    a,b=st.columns(2)
    with a: curve_chart(state,height=250)
    with b:
        chart(px.bar(risk['contributions'],x='id',y='contribution',title=t('risk_contribution'),labels={'id':t('position'),'contribution':t('risk_contribution')}),height=250)
    a,b=st.columns(2)
    with a:
        display=stress.assign(scenario=stress.scenario.map(t))
        chart(px.bar(display,x='scenario',y='pnl',title=t('stress'),labels={'scenario':t('scenario'),'pnl':t('pnl')}),height=250)
    with b:
        chart(px.bar(frame,x='ticker',y='delta_cash',title=t('delta_cash'),labels={'ticker':t('position'),'delta_cash':t('delta_cash')}),height=250)
    st.subheader(t('top_risks'))
    gross=frame.market_value.abs().sum(); largest=frame.loc[frame.market_value.abs().idxmax()]
    insights=[t('insight.concentration',asset=largest.ticker,weight=abs(largest.market_value)/gross),t('insight.stress',scenario=t(worst.scenario),loss=worst.pnl/risk['nav'])]
    total_dv=frame.dv01.abs().sum()
    if total_dv: insights.append(t('insight.dv01',share=frame.loc[frame.maturity>=10,'dv01'].abs().sum()/total_dv))
    if (frame.asset_class=='Option').any(): insights.append(t('insight.gamma',gamma=frame.gamma.sum()))
    for insight in insights: st.markdown(f'<div class="risk-line">{html.escape(insight)}</div>',unsafe_allow_html=True)
    view_data(frame)
