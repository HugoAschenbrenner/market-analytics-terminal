"""Editable zero curves and coherent single-bond discounting alongside YTM risk."""
from dataclasses import replace
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from components.lab_common import tr,plot,metrics,metric_value,table
from services.lab import get_lab,curve_outputs
from engines.scenario_engine import curve_scenarios
from engines.rates_tools_engine import curve_from_table


def render_curve_builder():
    lab=get_lab()
    st.subheader(tr('Zero curve & scenario lab','Labo courbe zéro et scénarios'))
    st.caption(tr('Direct continuously compounded zero rates. Linear interpolation in zero rates, flat outside the quoted tenors. This curve is separate from observed Treasury/par yields and from the portfolio’s YTM pricing.',
        'Taux zéro directement saisis, composés en continu. Interpolation linéaire des taux zéro, constante hors des piliers. Courbe distincte des rendements Treasury/par observés et de la valorisation YTM du portefeuille.'))
    with st.expander(tr('Edit curve · decimal rates','Modifier la courbe · taux décimaux')):
        with st.form('curve_input_form'):
            frame=st.data_editor(lab.curve,num_rows='dynamic',width='stretch',key='lab_curve_editor')
            if st.form_submit_button(tr('Apply zero curve','Appliquer la courbe zéro')):
                try:
                    curve_from_table(frame);lab.curve=frame.copy();lab.curve_source='USER INPUT'
                except (ValueError,TypeError) as exc:st.warning(str(exc))
    presets=curve_scenarios();choices=['Current shared scenario',*presets,'Custom twist']
    selected=st.selectbox(tr('Curve scenario','Scénario de courbe'),choices,key='lab_curve_scenario')
    current=lab.scenario
    if selected in presets:
        preset=presets[selected]
        lab.scenario=replace(current,name=preset.name,rate_bp=preset.rate_bp,curve_twist=preset.curve_twist)
    elif selected=='Custom twist':
        cols=st.columns(3)
        shifts=tuple(col.number_input(f'{tenor:g}Y / bp',value=float(current.rate_at(tenor)),key=f'lab_twist_{tenor}') for col,tenor in zip(cols,[2.,10.,30.]))
        lab.scenario=replace(current,name='Custom twist',rate_bp=0.,curve_twist=tuple(zip([2.,10.,30.],shifts)))
    st.caption(tr('Shared scenario','Scénario partagé')+f': {lab.scenario.name} · parallel {lab.scenario.rate_bp:+g} bp · twist {lab.scenario.curve_twist or "0"}')
    st.caption(tr('Twist = linear interpolation of the displayed tenor/bp nodes, flat beyond them; add the parallel shift. Equity/vol/correlation/time fields do not alter this curve-only valuation.',
        'Twist = interpolation linéaire des piliers années/pb affichés, constante au-delà ; ajouter le choc parallèle. Les champs action/vol/corrélation/temps ne modifient pas cette valorisation de courbe seule.'))
    a,b,c=st.columns(3)
    lab.curve_maturity=a.slider(tr('Illustrative bond maturity · years','Maturité obligation illustrative · années'),1,30,lab.curve_maturity,key='lab_curve_maturity')
    lab.curve_coupon=b.number_input(tr('Annual coupon %','Coupon annuel %'),min_value=0.,max_value=30.,value=float(lab.curve_coupon*100),key='lab_curve_coupon')/100
    lab.curve_notional=c.number_input(tr('Signed nominal · quote currency','Nominal signé · devise de cotation'),value=float(lab.curve_notional),key='lab_curve_notional')
    result=curve_outputs(lab);risk=result['risk'];spreads=result['spreads']
    st.caption(f"{lab.curve_source} · {lab.currency} · "+tr('Synthetic semiannual bond valued on a coupon date; no accrued interest, credit spread or funding. Not a position in the shared book.',
        'Obligation synthétique semestrielle valorisée à une date de coupon ; sans intérêts courus, spread ni financement. Hors portefeuille partagé.'))
    metrics([('2s10s · bp',metric_value(spreads['2s10s_bp'])),('5s30s · bp',metric_value(spreads['5s30s_bp'])),('DV01 / bp',metric_value(risk['dv01'])),(tr('Curve P&L','P&L de courbe'),metric_value(risk['pnl']))])
    chart=result['comparison']
    fig=go.Figure(go.Scatter(x=chart.tenor,y=chart.base_rate*100,name=tr('Base zero curve','Courbe zéro initiale')))
    fig.add_scatter(x=chart.tenor,y=chart.shocked_rate*100,name=tr('Shocked zero curve','Courbe zéro choquée'))
    plot(fig.update_layout(xaxis_title=tr('Tenor · years','Tenor · années'),yaxis_title='%'),'lab_curve')
    a,b=st.columns(2)
    with a:plot(px.bar(chart,x='tenor',y='change_bp',labels={'tenor':tr('Years','Années'),'change_bp':'bp'}),'lab_curve_diff',240)
    with b:plot(px.bar(risk['buckets'],x='tenor',y='dv01',labels={'tenor':tr('Years','Années'),'dv01':lab.currency+' / bp'}),'lab_curve_buckets',240)
    st.caption(tr(f"Full curve valuation {risk['base_value']:,.2f} → {risk['shocked_value']:,.2f}; parallel duration {risk['duration']:.3f} years. Bucket DV01 uses ±1 bp nodal bumps, interpolated with the same curve convention.",
        f"Valeur sur courbe {risk['base_value']:,.2f} → {risk['shocked_value']:,.2f} ; duration parallèle {risk['duration']:.3f} ans. DV01 par pilier calculée par chocs de ±1 pb avec la même interpolation."))
    table(result['table'],tr('Zero rates, discount factors & interval forwards','Taux zéro, facteurs d’actualisation et forwards par intervalle'))
    table(risk['cashflows'],tr('Cash flows & duration contributions','Flux et contributions à la duration'))
    with st.expander(tr('Export lab workbook','Exporter le rapport du labo')):
        from components.lab_report import render_lab_export
        render_lab_export()
