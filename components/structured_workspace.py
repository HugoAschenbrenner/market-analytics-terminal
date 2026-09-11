from dataclasses import replace
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t,error_message
from core.charting import chart
from services.structured import contract_for
from engines.structured_risk_engine import value_note,bump_risk,cashflows
from components.formula_panel import view_data,formula_panel
from components.kpi_card import kpis


def render_structured(state):
    notes=state.book.positions.query("asset_class=='Structured'")
    if notes.empty:st.info(t('structured.none'));return
    selected=st.selectbox(t('structured.select'),notes.id.tolist(),key='note_select')
    row=notes.set_index('id',drop=False).loc[selected].to_dict()
    inputs,ratios,product,memory,names=contract_for(row,state.market,state.book.structured_terms)
    with st.expander(t('structured.terms')):
        with st.form('note_terms'):
            a,b,c=st.columns(3)
            kind=a.selectbox(t('product'),['Athena','Phoenix'],index=['Athena','Phoenix'].index(product))
            mem=b.checkbox(t('memory'),value=memory)
            count=c.selectbox(t('simulations'),[1000,3000,10000],index=[1000,3000,10000].index(inputs.simulations))
            a,b,c=st.columns(3)
            ac=a.number_input(t('autocall_barrier'),min_value=.5,max_value=2.,value=inputs.autocall_barrier)
            cb=b.number_input(t('coupon_barrier'),min_value=.1,max_value=2.,value=inputs.coupon_barrier)
            pb=c.number_input(t('protection_barrier'),min_value=.01,max_value=1.,value=inputs.protection_barrier)
            a,b,c=st.columns(3)
            coupon=a.number_input(t('coupon_rate'),min_value=0.,max_value=40.,value=inputs.coupon_rate*100)/100
            corr=b.slider(t('correlation'),-.9,.95,float(inputs.correlation))
            freq=c.selectbox(t('observations_year'),[1,2,4,12],index=[1,2,4,12].index(inputs.observations_per_year))
            chosen=st.multiselect(t('underlyings'),[k for k in state.market.spots if k not in ['VIX','EURUSD']],default=list(names),max_selections=3)
            detail=pd.DataFrame(dict(underlying=names,fixing=inputs.initial_spots,volatility=inputs.volatilities))
            edited=st.data_editor(detail,disabled=['underlying'],hide_index=True,column_config={'underlying':t('underlying'),'fixing':t('fixing'),'volatility':t('vol.decimal')})
            if st.form_submit_button(t('book.apply')):
                try:
                    old=edited.set_index('underlying')
                    fixings=tuple(float(old.loc[n,'fixing']) if n in old.index else state.market.spots[n] for n in chosen)
                    vols=tuple(float(old.loc[n,'volatility']) if n in old.index else row['volatility'] for n in chosen)
                    candidate=dict(underlyings=tuple(chosen),fixings=fixings,volatilities=vols,product=kind,memory=mem,simulations=count,autocall=ac,coupon_barrier=cb,protection=pb,coupon=coupon,correlation=corr,frequency=freq)
                    ci,cr,cp,cm,_=contract_for(row,state.market,{selected:candidate});value_note(ci,cr,cp,cm)
                    state.book.structured_terms[selected]=candidate;state.book.revision+=1;state.risk.results.clear();st.rerun()
                except (ValueError,ZeroDivisionError) as exc:st.error(error_message(exc))
    tabs=st.tabs([t(k) for k in ['product','risk','simulation','advanced']],key='structured_tabs',on_change='rerun')
    result=value_note(inputs,ratios,product,memory);summary=result['summary'];flows=result['cashflows']
    if tabs[0].open:
        with tabs[0]:
            levels=np.linspace(.25,1.5,126)
            paths=np.broadcast_to(levels[:,None,None],(len(levels),len(result['times']),len(names)))
            payoff=cashflows(paths,inputs,product,memory)
            fig=go.Figure(go.Scatter(x=levels*100,y=payoff.payoff))
            for value,key in [(inputs.autocall_barrier,'autocall_barrier'),(inputs.coupon_barrier,'coupon_barrier'),(inputs.protection_barrier,'protection_barrier')]:fig.add_vline(x=value*100,line_dash='dot',annotation_text=t(key))
            chart(fig.update_layout(title=t('structured.payoff'),xaxis_title=t('fixing.percent'),yaxis_title=t('payoff')))
            kpis([('proxy_value',summary['value']),('mc_error',summary['mc_error']),('coupon_rate',inputs.coupon_rate*100),('maturity',inputs.maturity_years)])
    if tabs[1].open:
        with tabs[1]:
            risk=bump_risk(inputs,ratios,product,memory)
            a,b=st.columns(2)
            with a:
                distances=pd.DataFrame({t('autocall_barrier'):(np.array(ratios)-inputs.autocall_barrier)*100,t('coupon_barrier'):(np.array(ratios)-inputs.coupon_barrier)*100,t('protection_barrier'):(np.array(ratios)-inputs.protection_barrier)*100},index=names)
                chart(px.bar(distances,barmode='group',title=t('barrier.distances'),labels={'value':t('fixing.points'),'index':t('underlying'),'variable':t('barrier')}))
            with b:chart(go.Figure(go.Bar(x=names,y=risk['deltas'])).update_layout(title=t('mc.delta'),yaxis_title=t('delta')))
            kpis([('autocall_probability',f"{summary['autocall_probability']:.1%}"),('loss_probability',f"{summary['loss_probability']:.1%}"),('coupon_probability',f"{summary['coupon_probability']:.1%}"),('expected_maturity',summary['expected_maturity'])])
            kpis([('vega',risk['vega']),('domestic_rho',risk['rho']),('corr_risk',risk['correlation_1pct'])])
    if tabs[2].open:
        with tabs[2]:
            view=st.selectbox(t('simulation.view'),['payoff','autocall.time','fan','coupon_paid','capital_loss'],format_func=lambda k,lang=state.ui.language:t(k,lang))
            if view=='fan':
                worst=result['paths'].min(axis=2);fig=go.Figure()
                for q in [.05,.25,.5,.75,.95]:fig.add_scatter(x=result['times'],y=np.quantile(worst,q,axis=0)*100,name=f'{q:.0%}')
                chart(fig.update_layout(title=t('fan'),xaxis_title=t('maturity'),yaxis_title=t('fixing.percent')))
            elif view=='autocall.time':
                called=flows[flows.autocalled].groupby('event_time_years').size()/len(flows)
                fig=go.Figure(go.Bar(x=called.index,y=called))
                chart(fig.update_layout(title=t(view),xaxis_title=t('maturity'),yaxis_title=t('probability')))
            else:
                values=flows.payoff if view=='payoff' else flows.coupon_paid if view=='coupon_paid' else np.maximum(0,inputs.notional-flows.redemption)
                chart(go.Figure(go.Histogram(x=values,nbinsx=40)).update_layout(title=t(view),xaxis_title=t('value'),yaxis_title=t('observations')))
            view_data(flows)
    if tabs[3].open:
        with tabs[3]:
            view=st.selectbox(t('sensitivity.grid'),['spot_vol','spot_corr','vol_corr'],format_func=lambda k,lang=state.ui.language:t(k,lang))
            spots=np.linspace(.8,1.2,5);vols=np.linspace(-.05,.10,5);corrs=np.linspace(max(-.1,-1/max(1,len(names)-1)+.01),.8,5)
            xs=vols if view=='vol_corr' else spots;ys=vols if view=='spot_vol' else corrs;z=[]
            for y in ys:
                values=[]
                for x in xs:
                    vi=x if view=='vol_corr' else y if view=='spot_vol' else 0.
                    ii=replace(inputs,volatilities=tuple(max(.001,v+vi) for v in inputs.volatilities),correlation=float(y) if view!='spot_vol' else inputs.correlation)
                    rr=tuple(r*x for r in ratios) if view!='vol_corr' else ratios
                    values.append(value_note(ii,rr,product,memory)['summary']['value']-summary['value'])
                z.append(values)
            chart(go.Figure(go.Heatmap(x=(xs-1)*100 if view!='vol_corr' else xs*100,y=ys*100,z=z,colorscale='RdBu',zmid=0)).update_layout(title=t(view),xaxis_title=t('shock.vol') if view=='vol_corr' else t('equity'),yaxis_title=t('shock.vol') if view=='spot_vol' else t('correlation')))
    formula_panel('structured.method')
