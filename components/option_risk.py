import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t,error_message
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import formula_panel,view_data
from engines.pnl_explain_engine import pnl_explain,simulate_hedge


def option_args(row,state):
    return row.option_type,float(row.spot),float(row.strike),float(row.maturity),state.market.rates[row.currency],float(row.volatility)


def render_explain(row,state,prefix='explain'):
    a,b,c,d=st.columns(4)
    ds=a.slider(t('equity'),-30.,30.,1.,key=prefix+'s')/100*row.spot
    dv=b.slider(t('shock.vol'),-min(15.,row.volatility*99),30.,1.,key=prefix+'v')/100
    days=c.number_input(t('elapsed'),min_value=0.,max_value=max(0.,row.maturity*365-.001),value=min(1.,row.maturity*180),key=prefix+'t')
    dr=d.slider(t('rate_shock'),-200.,200.,0.,key=prefix+'r')/10000
    advanced=st.toggle(t('advanced'),value=True,key=prefix+'a')
    units=row.quantity*row.multiplier*state.market.fx[row.currency]/state.market.fx[state.book.base_currency]
    result=pnl_explain(*option_args(row,state),ds=ds,dv=dv,days=days,dr=dr,units=units,advanced=advanced)
    parts=result['parts'];keys=list(parts)+['total']
    chart(go.Figure(go.Waterfall(x=[t(k) for k in keys],y=list(parts.values())+[result['full']],measure=['relative']*len(parts)+['total'])).update_layout(title=t('pnl_explain'),yaxis_title=state.book.base_currency),height=330)
    kpis([('full_reprice',result['full']),('approximation',result['approximation']),('residual',parts['residual'])])
    formula_panel('explain.method',[r'\Delta V\approx\Delta\Delta S+\tfrac12\Gamma(\Delta S)^2+V_\sigma\Delta\sigma+\Theta\Delta t+V_r\Delta r+V_{S\sigma}\Delta S\Delta\sigma+\tfrac12V_{\sigma\sigma}(\Delta\sigma)^2'])
    view_data(pd.DataFrame({'factor':[t(k) for k in parts],'pnl':parts.values()}))


def render_hedge(row,state):
    a,b,c,d=st.columns(4)
    kind=a.selectbox(t('hedge.instrument'),[row.option_type,'Straddle'],key='sim_kind',format_func=lambda x,lang=state.ui.language:t(x,lang))
    realized=b.slider(t('realized.assumed'),1.,80.,float(row.volatility*100),key='sim_rv')/100
    frequency=c.selectbox(t('hedge.frequency'),[1,5,21],key='sim_freq')
    costs=d.number_input(t('cost.bps'),min_value=0.,max_value=100.,value=2.,key='sim_cost')
    result=simulate_hedge(kind,row.spot,row.strike,row.maturity,state.market.rates[row.currency],row.volatility,realized,frequency=frequency,cost_bps=costs)
    data=result['path'];last=data.iloc[-1]
    view=st.segmented_control(t('hedge.view'),['hedge.components','hedge.path'],default='hedge.components',format_func=lambda x,lang=state.ui.language:t(x,lang),key='hedge_view')
    if view=='hedge.path':
        fig=go.Figure(go.Scatter(x=data.time,y=data.spot,name=t('spot')))
        fig.add_scatter(x=data.time,y=data.delta_hedge,name=t('delta_hedge'),yaxis='y2')
        chart(fig.update_layout(title=t('hedge.path'),xaxis_title=t('maturity'),yaxis2=dict(overlaying='y',side='right',title=t('delta_hedge'))))
    else:
        plot=data.rename(columns={k:t(k) for k in ['option_pnl','hedge_pnl','funding','costs','total']})
        chart(px.line(plot,x='time',y=[t(k) for k in ['option_pnl','hedge_pnl','funding','costs','total']],title=t('hedge.components'),labels={'time':t('maturity'),'value':t('value'),'variable':t('component')}))
    kpis([('hedge.error',last.total),('costs',last.costs),('realized.vol',result['realized_vol']*100),('implied.vol',row.volatility*100)])
    formula_panel('hedge.sim.method');view_data(data)
