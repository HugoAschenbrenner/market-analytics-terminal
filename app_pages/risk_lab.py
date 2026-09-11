from dataclasses import replace
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.book_editor import book_editor
from components.kpi_card import kpis
from components.formula_panel import view_data,formula_panel
from services.book_risk import book_risk
from engines.risk_factor_engine import backtest_var,curve_pca
from engines.rates_tools_engine import key_rate_ladder
from engines.desk_scenario_engine import PRESETS,DeskScenario,evaluate_scenario,scenario_summary

def risk_controls(state):
    a,b,c=st.columns(3)
    state.risk.estimator=a.selectbox(t('covariance'),['sample','ewma','ledoit_wolf'],index=['sample','ewma','ledoit_wolf'].index(state.risk.estimator),format_func=lambda x,lang=state.ui.language:t(x,lang))
    state.risk.confidence=b.selectbox(t('confidence'),[.95,.975,.99],index=[.95,.975,.99].index(state.risk.confidence),format_func=lambda x:f'{x:.1%}')
    state.risk.horizon=int(c.selectbox(t('horizon'),[1,5,10],index=[1,5,10].index(state.risk.horizon)))

def render(state):
    tabs=st.tabs([t(k) for k in ['book_exposure','risk_var','factor','stress','validation']],key='risk_tabs',on_change='rerun')
    if tabs[0].open:
        with tabs[0]:
            book_editor(state)
            risk=book_risk(state);frame=risk['marks']
            weights=frame.market_value.abs()/frame.market_value.abs().sum()
            kpis([('hhi',float((weights**2).sum())),('effective_assets',float(1/(weights**2).sum()))])
            chart(px.bar(frame,x='id',y='market_value',color='asset_class',title=t('exposure'),labels={'id':t('position'),'market_value':t('value'),'asset_class':t('asset_class')}))
    if tabs[1].open:
        with tabs[1]:
            risk_controls(state);risk=book_risk(state)
            kpis([(k,float(risk[k])) for k in ['var','es','parametric_var','parametric_es']])
            st.caption(t('risk.synthetic')+f" · {t('ann_vol')}: {risk['volatility']:.2%}")
            a,b=st.columns(2)
            with a:
                fig=go.Figure(go.Histogram(x=risk['horizon_pnl'],nbinsx=45,name=t('pnl')))
                fig.add_vline(x=-risk['var'],line_color='#eabc63',annotation_text='VaR')
                fig.add_vline(x=-risk['es'],line_color='#ff6b7b',annotation_text='ES')
                chart(fig.update_layout(title=t('distribution'),xaxis_title=t('pnl'),yaxis_title=t('observations')))
            with b: chart(px.bar(risk['contributions'],x='id',y='component_var',title=t('component_var'),labels={'id':t('position'),'component_var':t('component_var')}))
            a,b=st.columns(2)
            with a:
                chart(go.Figure(go.Scatter(x=risk['returns'].index,y=risk['returns'].rolling(60).std()*np.sqrt(252))).update_layout(title=t('rolling_vol'),xaxis_title=t('date'),yaxis_title=t('volatility')))
                chart(go.Figure(go.Scatter(x=risk['drawdown'].index,y=risk['drawdown'],fill='tozeroy')).update_layout(title=t('drawdown'),xaxis_title=t('date'),yaxis_title=t('drawdown')))
            with b:
                chart(px.imshow(risk['pnl'].corr(),color_continuous_scale='RdBu',zmin=-1,zmax=1,title=t('correlation')))
                active=risk['pnl'].columns[risk['pnl'].std()>0].tolist()
                if len(active)>=2:
                    pair=st.multiselect(t('rolling_corr'),active,default=active[:2],max_selections=2)
                    if len(pair)==2:
                        corr=risk['pnl'][pair[0]].rolling(60).corr(risk['pnl'][pair[1]])
                        chart(go.Figure(go.Scatter(x=corr.index,y=corr)).update_layout(title=t('rolling_corr'),xaxis_title=t('date'),yaxis_title=t('correlation')))
            view_data(risk['contributions']);formula_panel('risk.method',[r'\mathrm{VaR}_\alpha=z_\alpha\sqrt{w^\top\Sigma w}',r'\mathrm{CVaR}_i=w_i z_\alpha\frac{(\Sigma w)_i}{\sqrt{w^\top\Sigma w}}'])
    if tabs[2].open:
        with tabs[2]:
            currency=st.selectbox(t('currency'),['USD','EUR'],key='pca_currency')
            payload=state.market.curves[currency];pca=curve_pca(payload['history'])
            st.caption(f'{t(payload["source"])} · {payload["provider"]} · {payload["as_of"]}')
            loadings=pd.DataFrame(pca['loadings'].T,index=payload['history'].columns,columns=['PC1','PC2','PC3'])
            a,b=st.columns(2)
            with a: chart(px.line(loadings,title=t('loadings'),labels={'index':t('tenor'),'value':t('loadings'),'variable':t('factor')}))
            with b: chart(go.Figure(go.Bar(x=['PC1','PC2','PC3'],y=pca['explained'])).update_layout(title=t('explained'),yaxis_title=t('explained')))
            marks=book_risk(state)['marks'];bonds=marks.query("asset_class=='Bond' and currency==@currency")
            ladder=key_rate_ladder(bonds,state)
            if len(ladder):
                exposure=-ladder.iloc[:,2:].sum().to_numpy()@pca['loadings'].T*np.sqrt(pca['variance'])
                chart(go.Figure(go.Bar(x=['PC1','PC2','PC3'],y=exposure)).update_layout(title=t('factor_exposure'),yaxis_title=t('pnl')))
                view_data(ladder)
            formula_panel('pca.method')
    if tabs[3].open:
        with tabs[3]: render_scenarios(state)
    if tabs[4].open:
        with tabs[4]:
            from components.r_companion import render_r_companion
            render_r_companion()
            risk=book_risk(state);bt=backtest_var(risk['total'],state.risk.confidence)
            fig=go.Figure(go.Scatter(x=bt.index,y=bt.pnl,name=t('pnl')))
            fig.add_scatter(x=bt.index,y=-bt['var'],name='VaR')
            fig.add_scatter(x=bt.index[bt.exceedance],y=bt.loc[bt.exceedance,'pnl'],mode='markers',name=t('exceedances'))
            chart(fig.update_layout(title=t('exceedances'),xaxis_title=t('date'),yaxis_title=t('pnl')),height=350)
            st.caption(t('risk.synthetic'));view_data(bt);formula_panel('risk.method')
            with st.expander(t('pnl_explain')):
                from components.option_risk import render_explain
                options=risk['marks'].query("asset_class=='Option'")
                if not options.empty:
                    selected=st.selectbox(t('option.select'),options.id.tolist(),key='risk_option')
                    render_explain(options.set_index('id').loc[selected],state,prefix='risk_explain')
                else:st.info(t('option.none'))

def render_scenarios(state):
    selected=st.selectbox(t('scenario'),[s.name for s in PRESETS]+['custom'],format_func=lambda x,lang=state.ui.language:t(x,lang),key='scenario_select')
    state.scenario.name=selected
    if selected=='custom':
        a,b,c=st.columns(3)
        eq=a.slider(t('equity'),-50.,50.,-10.)/100
        fx=b.slider(t('fx'),-40.,40.,0.)/100
        rate=c.slider(t('rate_shock'),-200.,300.,0.)
        a,b,c=st.columns(3)
        credit=a.slider(t('credit'),-100.,500.,50.)
        vol=b.slider(t('volatility'),-15.,50.,5.)/100
        corr=c.slider(t('correlation'),-.8,.8,0.)
        a,b=st.columns(2)
        haircut=a.slider(t('haircut'),-10.,80.,5.)/100
        collateral=b.slider(t('collateral_shock'),-80.,30.,-10.)/100
        rates=(rate,)*5
        if st.checkbox(t('nonparallel')):
            rates=tuple(col.number_input(f'{year}Y / bp',value=float(rate),min_value=-500.,max_value=1000.,key=f'curve_shock_{year}') for col,year in zip(st.columns(5),[1,2,5,10,30]))
        scenario=DeskScenario('custom',eq,fx,rates,credit,vol,corr,haircut,collateral)
    else:scenario=next(s for s in PRESETS if s.name==selected)
    marks=book_risk(state)['marks'];result=evaluate_scenario(marks,state.market,state.book,scenario)
    state.scenario.shocks=scenario.__dict__
    kpis([('pnl',result['pnl']),('liquidity',result['liquidity'])])
    a,b=st.columns(2)
    with a:chart(go.Figure(go.Waterfall(x=[t(k) for k in result['by_factor'].index],y=result['by_factor'],measure=['relative']*6)).update_layout(title=t('factor_pnl'),yaxis_title=t('pnl')))
    with b:chart(px.bar(result['positions'],x='id',y='pnl',color='asset_class',title=t('pnl'),labels={'id':t('position'),'pnl':t('pnl'),'asset_class':t('asset_class')}))
    matrix=pd.DataFrame({t(s.name):evaluate_scenario(marks,state.market,state.book,s)['positions'].set_index('id').pnl for s in PRESETS})
    chart(px.imshow(matrix,color_continuous_scale='RdBu',color_continuous_midpoint=0,title=t('stress')))
    view_data(result['positions']);formula_panel('scenario.method')
