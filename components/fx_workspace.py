import numpy as np
import plotly.express as px
import streamlit as st
from core.i18n import t
from core.charting import chart
from core.models import CURRENCIES
from components.formula_panel import formula_panel,view_data
from components.kpi_card import kpis
from engines.fx_engine import fx_forward,cross_rate,garman_kohlhagen,fx_swap_points,client_hedges

def render_fx(state):
    a,b,c=st.columns(3)
    foreign=a.selectbox(t('foreign'),CURRENCIES,index=1,key='fx_foreign')
    domestic=b.selectbox(t('domestic'),[x for x in CURRENCIES if x!=foreign],key='fx_domestic')
    maturity=c.number_input(t('maturity'),min_value=.01,max_value=10.,value=1.,key='fx_maturity')
    spot=cross_rate(state.market.fx,foreign,domestic);rd=state.market.rates[domestic];rf=state.market.rates[foreign]
    with st.expander(t('market.inputs')):
        a,b,c=st.columns(3)
        s=a.number_input(t('spot'),min_value=.000001,value=float(spot),format='%.6f',key=f'fx_spot_{foreign}_{domestic}')
        dr=b.number_input(t('domestic_rate'),min_value=-10.,max_value=30.,value=rd*100,key=f'fx_rate_{domestic}')/100
        fr=c.number_input(t('foreign_rate'),min_value=-10.,max_value=30.,value=rf*100,key=f'fx_rate_{foreign}')/100
        if (s,dr,fr)!=(spot,rd,rf):
            state.market.fx[foreign]=s*state.market.fx[domestic]
            usd=state.market.fx['USD'];state.market.fx={k:v/usd for k,v in state.market.fx.items()}
            state.market.rates.update({domestic:dr,foreign:fr});state.market.revision+=1
            spot,rd,rf=s,dr,fr
    tabs=st.tabs([t('fx.forwards'),t('fx.options'),t('fx.hedge')],key='fx_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            pip=.01 if domestic=='JPY' else .0001
            f=fx_forward(spot,rd,rf,maturity,pip)
            kpis([('spot',spot),('forward',f['forward']),('forward_points',f['points']),('swap_points',fx_swap_points(spot,rd,rf,min(.25,maturity),maturity,pip))])
            times=np.linspace(0,maturity,50)
            chart(px.line(x=times,y=[fx_forward(spot,rd,rf,v,pip)['forward'] for v in times],labels={'x':t('maturity'),'y':t('forward')},title=t('forward')))
            formula_panel('fx.method',[r'F=S e^{(r_d-r_f)T}',r'S_{A/B}=S_{A/USD}/S_{B/USD}'])
    if tabs[1].open:
        with tabs[1]:
            a,b,c=st.columns(3)
            kind=a.selectbox(t('option.type'),['Call','Put'],key='gk_kind')
            strike=b.number_input(t('strike'),min_value=.000001,value=float(spot),format='%.6f',key=f'gk_strike_{foreign}_{domestic}')
            vol=c.slider(t('vol'),1.,80.,12.,key='gk_vol')/100
            result=garman_kohlhagen(kind,spot,strike,maturity,rd,rf,vol)
            kpis([('option.price',result['price']),('delta',result['delta']),('vega',result['vega_1pct']),('theta',result['theta_daily'])])
            kpis([('domestic_rho',result['rho_1pct']),('foreign_rho',result['foreign_rho_1pct']),('gamma',result['gamma'])])
            spots=np.linspace(.7*spot,1.3*spot,61)
            chart(px.line(x=spots,y=[garman_kohlhagen(kind,s,strike,maturity,rd,rf,vol)['price'] for s in spots],title=t('fx.options'),labels={'x':t('spot'),'y':t('option.price')}))
            formula_panel('gk.method',[r'C=S e^{-r_fT}N(d_1)-K e^{-r_dT}N(d_2)'])
    if tabs[2].open:
        with tabs[2]:
            a,b,c=st.columns(3)
            client=a.selectbox(t('client'),['exporter','importer'],format_func=lambda x,lang=state.ui.language:t(x,lang))
            nominal=b.number_input(t('notional'),min_value=1.,value=1e6,step=100000.)
            vol=c.slider(t('vol'),1.,80.,12.,key='hedge_vol')/100
            result=client_hedges(spot,rd,rf,maturity,vol,nominal,client)
            data=result['flows'].rename(columns={k:t(k) for k in ['unhedged','forward','option','collar']})
            chart(px.line(data,x='spot',y=[col for col in data if col!='spot'],title=t('fx.hedge'),labels={'spot':t('spot'),'value':t('proceeds'),'variable':t('strategy')}),height=360)
            details=result['details'].copy();details.strategy=details.strategy.map(t)
            st.dataframe(details.rename(columns={k:t(k) for k in details}),hide_index=True,width='stretch')
            if result['collar'] is None:st.info(t('collar.unavailable'))
            formula_panel('hedge.method');view_data(result['flows'])
