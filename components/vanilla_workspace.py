import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t,error_message
from core.charting import chart
from components.formula_panel import formula_panel
from components.kpi_card import kpis
from components.option_risk import option_args,render_explain,render_hedge
from engines.options_pricing_engine import black_scholes_price as price,black_scholes_greeks as greeks
from engines.pnl_explain_engine import advanced_greeks,implied_volatility,volatility_surface,fx_vol_quotes

FORMULAS=[r'd_1=\frac{\log(S/K)+(r-q+\sigma^2/2)T}{\sigma\sqrt T},\quad d_2=d_1-\sigma\sqrt T',
 r'C=Se^{-qT}N(d_1)-Ke^{-rT}N(d_2),\quad P=Ke^{-rT}N(-d_2)-Se^{-qT}N(-d_1)',
 r'\Delta_C=e^{-qT}N(d_1),\quad\Delta_P=e^{-qT}[N(d_1)-1],\quad\Gamma=\frac{e^{-qT}\phi(d_1)}{S\sigma\sqrt T}',
 r'V_\sigma=Se^{-qT}\phi(d_1)\sqrt T',
 r'\Theta_C=-\frac{Se^{-qT}\phi(d_1)\sigma}{2\sqrt T}-rKe^{-rT}N(d_2)+qSe^{-qT}N(d_1)',
 r'\Theta_P=-\frac{Se^{-qT}\phi(d_1)\sigma}{2\sqrt T}+rKe^{-rT}N(-d_2)-qSe^{-qT}N(-d_1)',
 r'\rho_C=TK e^{-rT}N(d_2),\quad\rho_P=-TK e^{-rT}N(-d_2)']


def render_vanilla(row,state):
    tabs=st.tabs([t(k) for k in ['option.price','pnl_explain','hedge.sim']],key='vanilla_tabs',on_change='rerun')
    args=option_args(row,state)
    if tabs[0].open:
        with tabs[0]:
            kpis([('option.price',row.mark),('strike',row.strike),('implied.vol',row.volatility*100),('maturity',row.maturity)])
            spots=np.linspace(.65*row.spot,1.35*row.spot,81)
            fig=go.Figure(go.Scatter(x=spots,y=[price(args[0],s,*args[2:]) for s in spots],name=t('option.price')))
            fig.add_scatter(x=spots,y=np.maximum(0,spots-row.strike) if row.option_type=='Call' else np.maximum(0,row.strike-spots),name=t('intrinsic'))
            chart(fig.update_layout(title=t('option.price'),xaxis_title=t('spot'),yaxis_title=row.currency))
            formula_panel('option.units',FORMULAS)
    if tabs[1].open:
        with tabs[1]:render_explain(row,state)
    if tabs[2].open:
        with tabs[2]:render_hedge(row,state)


def render_greeks(row,state):
    args=option_args(row,state);g=greeks(*args)
    view=st.selectbox(t('greeks.view'),['delta','gamma','vega_1pct','theta_daily','price_surface','gamma_surface','vega_surface'],format_func=lambda x,lang=state.ui.language:t(x,lang))
    spots=np.linspace(row.spot*.65,row.spot*1.35,41);times=np.linspace(max(.001,row.maturity*.02),row.maturity*1.5,30)
    if view.endswith('surface'):
        ys=np.linspace(.05,.65,25) if view=='price_surface' else times
        z=[[price(args[0],s,args[2],args[3],args[4],y) if view=='price_surface' else greeks(args[0],s,args[2],y,args[4],args[5])['gamma' if view=='gamma_surface' else 'vega_1pct'] for s in spots] for y in ys]
        chart(go.Figure(go.Heatmap(x=spots,y=ys,z=z)).update_layout(title=t(view),xaxis_title=t('spot'),yaxis_title=t('volatility') if view=='price_surface' else t('maturity')))
    else:
        x=times if view=='theta_daily' else spots
        y=[greeks(args[0],args[1] if view=='theta_daily' else v,args[2],v if view=='theta_daily' else args[3],*args[4:])[view] for v in x]
        chart(px.line(x=x,y=y,title=t(view),labels={'x':t('maturity') if view=='theta_daily' else t('spot'),'y':t(view)}))
    kpis([('delta',g['delta']),('gamma',g['gamma']),('vega',g['vega_1pct']),('theta',g['theta_daily']),('domestic_rho',g['rho_1pct'])])
    if st.toggle(t('advanced'),key='advanced_greeks'):
        a=advanced_greeks(*args);kpis([(k,a[k]) for k in a])
        formula_panel('advanced.method',[r'V_{S\sigma}=-e^{-qT}\phi(d_1)d_2/\sigma',r'V_{\sigma\sigma}=V_\sigma d_1d_2/\sigma',r'\mathrm{Charm}=q\Delta-e^{-qT}\phi(d_1)\frac{2(r-q)T-d_2\sigma\sqrt T}{2T\sigma\sqrt T}'])
    else:formula_panel('option.units',FORMULAS)


def render_volatility(row,state):
    args=option_args(row,state)
    with st.expander(t('iv.solver')):
        observed=st.number_input(t('observed.price'),min_value=0.,value=float(row.mark),format='%.8f')
        try:st.metric(t('implied.vol'),f'{implied_volatility(observed,*args[:5])*100:.4f}%')
        except ValueError as exc:st.warning(error_message(exc))
        st.caption(t('iv.method'))
    a,b,c=st.columns(3)
    skew=a.slider(t('skew'),-.3,.3,-.08)
    term=b.slider(t('vol.term'),-.04,.1,.015)
    view=c.selectbox(t('vol.view'),['vol.surface','vol.smile','vol.term','fx.quotes'],format_func=lambda x,lang=state.ui.language:t(x,lang))
    m,times,z=volatility_surface(row.volatility,skew=skew,term=term)
    if view=='vol.surface':chart(go.Figure(go.Surface(x=m,y=times,z=z*100)).update_layout(title=t(view),scene=dict(xaxis_title=t('moneyness'),yaxis_title=t('maturity'),zaxis_title=t('vol'))),height=390)
    elif view=='vol.smile':
        fig=go.Figure()
        for i in [2,4,6]:fig.add_scatter(x=m,y=z[i]*100,name=f'{times[i]:g}Y')
        chart(fig.update_layout(title=t(view),xaxis_title=t('moneyness'),yaxis_title=t('vol')))
    elif view=='vol.term':chart(px.line(x=times,y=z[:,15]*100,title=t(view),labels={'x':t('maturity'),'y':t('vol')}))
    else:
        a,b=st.columns(2);rr=a.slider('25Δ RR / vol pt',-10.,10.,-2.)/100;bf=b.slider('25Δ BF / vol pt',0.,10.,1.)/100
        q=fx_vol_quotes(row.volatility,rr,bf)
        chart(go.Figure(go.Bar(x=['ATM','25Δ Call','25Δ Put'],y=[q[k]*100 for k in ['atm','call25','put25']])).update_layout(title=t(view),yaxis_title=t('vol')))
    formula_panel('vol.method',[r'\sigma_{25C}=\sigma_{ATM}+BF+RR/2,\quad\sigma_{25P}=\sigma_{ATM}+BF-RR/2'])
