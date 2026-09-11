from dataclasses import asdict
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import formula_panel,view_data
from services.analytics import marked_positions
from services.financing import repo_margin,repo_stress
from engines.sec_lending_engine import calculate_securities_lending_trade


def render(state):
    tabs=st.tabs([t(k) for k in ['repo','lending','collateral']],key='financing_tabs',on_change='rerun')
    marks=marked_positions(state)
    if tabs[1].open:
        with tabs[1]:render_lending(state,marks)
    if tabs[0].open or tabs[2].open:
        with tabs[0] if tabs[0].open else tabs[2]:
            b=state.book;bonds=marks.query("asset_class=='Bond' and market_value>0")
            if bonds.empty:st.info(t('financing.no_collateral'));return
            ids=bonds.id.tolist()
            b.collateral_id=st.selectbox(t('collateral.position'),ids,index=ids.index(b.collateral_id) if b.collateral_id in ids else 0,key='repo_collateral')
            collateral=float(bonds.set_index('id').loc[b.collateral_id,'market_value'])
            a,c,d,e=st.columns(4)
            b.repo_cash=a.number_input(t('financing.cash'),min_value=0.,value=b.repo_cash,step=10000.)
            b.repo_rate=c.number_input(t('financing.rate'),min_value=-10.,max_value=50.,value=b.repo_rate*100)/100
            b.repo_haircut=d.number_input(t('financing.haircut'),min_value=0.,max_value=90.,value=b.repo_haircut*100)/100
            b.repo_days=int(e.number_input(t('financing.days'),min_value=1,max_value=3650,value=b.repo_days))
            with st.expander(t('contract.terms')):
                terms=b.financing_terms;a,c,d=st.columns(3)
                terms['basis']=a.selectbox(t('day_count'),[360,365],index=0 if terms.get('basis',360)==360 else 1)
                terms['elapsed']=int(c.number_input(t('elapsed'),min_value=0,max_value=b.repo_days,value=min(terms.get('elapsed',0),b.repo_days)))
                terms['threshold']=d.number_input(t('threshold'),min_value=0.,value=terms.get('threshold',0.))
                a,c=st.columns(2)
                terms['mta']=a.number_input(t('mta'),min_value=0.,value=terms.get('mta',0.))
                terms['rounding']=c.number_input(t('rounding'),min_value=0.,value=terms.get('rounding',1.))
            if tabs[0].open:
                cost=b.repo_cash*b.repo_rate*b.repo_days/b.financing_terms.get('basis',360)
                kpis([('financing.cash',b.repo_cash),('financing.cost',cost),('repayment',b.repo_cash+cost)])
                a,c=st.columns(2);rates=np.linspace(-.01,.1,30);days=np.arange(1,366)
                with a:chart(px.line(x=rates*100,y=b.repo_cash*rates*b.repo_days/b.financing_terms.get('basis',360),title=t('funding.rate'),labels={'x':t('financing.rate'),'y':t('financing.cost')}))
                with c:chart(px.line(x=days,y=b.repo_cash*b.repo_rate*days/b.financing_terms.get('basis',360),title=t('funding.maturity'),labels={'x':t('financing.days'),'y':t('financing.cost')}))
                view_data(pd.DataFrame({'date':[state.valuation_date,state.valuation_date+pd.Timedelta(days=b.repo_days)],'borrower_cashflow':[b.repo_cash,-b.repo_cash-cost]}))
            else:
                a,c=st.columns(2)
                shock=a.slider(t('collateral_shock'),-70.,20.,-10.)/100
                haircut=c.slider(t('refinancing.haircut'),0.,95.,min(95.,(b.repo_haircut+.05)*100))/100
                margin=repo_margin(state,collateral);stress,shortfall=repo_stress(state,collateral,haircut,shock)
                prices=np.linspace(-.5,.2,31);haircuts=np.linspace(0,.8,31)
                a,c=st.columns(2)
                with a:chart(px.line(x=prices*100,y=[max(0,repo_margin(state,collateral,x).contractual_margin_transfer) if b.repo_cash else 0 for x in prices],title=t('margin.price'),labels={'x':t('collateral_shock'),'y':t('financing.margin')}))
                with c:chart(px.line(x=haircuts*100,y=[repo_stress(state,collateral,h,shock)[1] for h in haircuts],title=t('margin.haircut'),labels={'x':t('refinancing.haircut'),'y':t('liquidity')}))
                kpis([('financing.margin',margin.contractual_margin_transfer if b.repo_cash else 0.),('securities.transfer',margin.collateral_transfer_amount if b.repo_cash else 0.),('liquidity',shortfall)])
                chart(go.Figure(go.Bar(x=[t('current'),t('stressed')],y=[max(0,b.repo_cash-collateral*(1-b.repo_haircut)),shortfall])).update_layout(title=t('liquidity'),yaxis_title=b.base_currency),height=230)
                view_data(pd.DataFrame([asdict(margin),asdict(stress)]))
            formula_panel('financing.method',[r'I=C r d/B',r'VM_{cash}=C+I_{accrued}-V_{dirty}(1-h_0)',r'VM_{securities}=|VM_{cash}|/(1-h_0)'])


def render_lending(state,marks):
    eligible=marks.query("asset_class in ['Bond','Equity'] and market_value>0")
    if eligible.empty:st.info(t('financing.no_collateral'));return
    saved=state.book.lending_terms
    selected=st.selectbox(t('lending.security'),eligible.id.tolist(),key='lending_security')
    value=float(eligible.set_index('id').loc[selected,'market_value'])
    a,b,c=st.columns(3)
    ctype=a.selectbox(t('collateral.type'),['Non-cash','Cash'],format_func=lambda x,lang=state.ui.language:t(x,lang),index=['Non-cash','Cash'].index(saved.get('collateral_type','Non-cash')))
    fee=b.number_input(t('borrow.fee'),min_value=0.,max_value=100.,value=saved.get('borrow_fee_rate',.02)*100,disabled=ctype=='Cash')/100
    days=int(c.number_input(t('financing.days'),min_value=1,max_value=3650,value=saved.get('loan_days',30),key='lending_days'))
    with st.expander(t('contract.terms')):
        a,b,c=st.columns(3)
        rebate=a.number_input(t('rebate'),min_value=-20.,max_value=50.,value=saved.get('rebate_rate',.02)*100,disabled=ctype!='Cash')/100
        reinvest=b.number_input(t('reinvestment'),min_value=-20.,max_value=50.,value=saved.get('reinvestment_yield',.04)*100,disabled=ctype!='Cash')/100
        ratio=c.number_input(t('collateral.ratio'),min_value=100.,max_value=200.,value=saved.get('collateralization_rate',1.02)*100)/100
        a,b,c=st.columns(3)
        share=a.slider(t('agent.share'),0.,100.,saved.get('agent_fee_share',.15)*100)/100
        perspective=b.selectbox(t('perspective'),['Beneficial owner','Lending agent'],format_func=lambda x,lang=state.ui.language:t(x,lang))
        other=c.number_input(t('other.costs'),min_value=0.,value=saved.get('other_costs',0.))
    saved.update(security_market_value=value,collateral_type=ctype,borrow_fee_rate=fee if ctype=='Non-cash' else 0.,rebate_rate=rebate if ctype=='Cash' else 0.,reinvestment_yield=reinvest if ctype=='Cash' else 0.,collateralization_rate=ratio,loan_days=days,agent_fee_share=share,perspective=perspective,other_costs=other)
    result=calculate_securities_lending_trade(**saved)
    parts=[result.gross_lending_revenue,-result.agent_fee_amount if perspective=='Beneficial owner' else -(result.gross_lending_revenue-result.agent_fee_amount),-other,result.net_lending_revenue]
    chart(go.Figure(go.Waterfall(x=[t(k) for k in ['gross.revenue','revenue.share','other.costs','net.revenue']],y=parts,measure=['relative','relative','relative','total'])).update_layout(title=t('lending'),yaxis_title=state.book.base_currency))
    kpis([('collateral.required',result.collateral_required),('gross.revenue',result.gross_lending_revenue),('net.revenue',result.net_lending_revenue)])
    view_data(pd.DataFrame([asdict(result)]));formula_panel('lending.method')
