"""Focused option-chain, volatility and signed-position analytics; no note pricing."""
from dataclasses import asdict,replace
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from components.lab_common import tr,plot,metrics,metric_value,table
from services.lab import get_lab,chain_analysis,option_outputs
from engines.option_chain_engine import empirical_smile,smile_metrics,term_structure
from engines.equity_derivatives_engine import OptionPosition,position_analytics,option_scenario,delta_hedge,scenario_matrix,greek_grid
from engines.scenario_engine import MarketScenario


def _load_quote(row: dict):
    lab=get_lab()
    lab.position=OptionPosition(row['option_type'],row['spot'],row['strike'],row['time_to_maturity'],
        row['rate'],row['implied_volatility'],row['dividend'],lab.position.quantity,lab.position.multiplier)
    lab.position_source=f"{lab.source} · {row['underlying']} · {row['maturity']} · K={row['strike']:g}"
    for key in list(st.session_state):
        if key.startswith('eqd_pos_'):
            del st.session_state[key]


def _mark_position_input():
    get_lab().position_source='USER INPUT'


def render(state):
    st.title('Equity Derivatives')
    st.caption(tr('Volatility & Risk Lab · European options · Input → Calculation → Scenario → Interpretation → Export',
                  'Volatilité et risque · Options européennes · Saisie → Calcul → Scénario → Interprétation → Export'))
    lab=get_lab()
    st.caption(tr('Independent analytical position, not added to the shared portfolio. The dashboard and lab workbook reuse these inputs.',
                  'Position analytique indépendante, non ajoutée au portefeuille partagé. Le dashboard et le rapport du labo reprennent ces saisies.'))
    with st.expander(tr('Option-chain inputs · CSV or editable demo','Chaîne d’options · CSV ou démo éditable')):
        st.caption(tr('One underlying and spot. Rates/IV are decimals: 0.215 = 21.5%; +3 vol points = +0.03. Expiry minus valuation date uses ACT/365. Optional rate/dividend default to 3.5%/1%.',
            'Un sous-jacent et un spot. Taux/IV en décimal : 0,215 = 21,5 % ; +3 points de vol = +0,03. Échéance moins date de valorisation en ACT/365. Taux/dividende facultatifs : 3,5 % / 1 % par défaut.'))
        upload=st.file_uploader(tr('Option chain CSV','CSV chaîne d’options'),type='csv',key='eqd_upload')
        try:
            inputs=pd.read_csv(upload) if upload is not None else lab.chain
        except (ValueError,UnicodeError) as exc:
            st.warning(str(exc));inputs=lab.chain
        with st.form('eqd_chain_form'):
            a,b=st.columns(2)
            as_of=a.date_input(tr('Valuation date','Date de valorisation'),value=lab.as_of,key='eqd_as_of')
            mode_labels={'iv':tr('Implied volatility (decimal)','Volatilité implicite (décimal)'),
                         'price':tr('Option prices → implied volatility','Prix d’options → volatilité implicite')}
            mode=b.selectbox(tr('Input workflow','Type de saisie'),['iv','price'],index=['iv','price'].index(lab.mode),
                format_func=mode_labels.get,key='eqd_chain_mode')
            edited=st.data_editor(inputs,num_rows='dynamic',width='stretch',key='eqd_chain_edit',height=260)
            if st.form_submit_button(tr('Apply chain inputs','Appliquer la chaîne'),key='eqd_apply_chain'):
                try:
                    candidate=chain_analysis(edited,as_of,mode)
                    if candidate['chain'].empty:raise ValueError(tr('No usable quotes; check the rows and dates.','Aucune cotation exploitable : vérifiez lignes et dates.'))
                    lab.chain=edited.copy();lab.as_of=as_of;lab.mode=mode;lab.source='USER INPUT'
                    st.success(tr('Chain applied. Rejected rows remain visible below.','Chaîne appliquée. Les lignes rejetées restent visibles ci-dessous.'))
                except (ValueError,TypeError) as exc:st.warning(str(exc))
        st.download_button(tr('Download input template','Télécharger le modèle CSV'),lab.chain.to_csv(index=False),'option_chain.csv','text/csv')
    try:
        result=chain_analysis(lab.chain,lab.as_of,lab.mode);chain=result['chain']
        if chain.empty:raise ValueError('No valid option-chain observations.')
    except (ValueError,TypeError) as exc:
        st.warning(str(exc));return
    st.caption(f"{lab.source} · {lab.as_of.isoformat()} · {len(chain)} "+tr('usable quotes · European BSM; no live chain or American exercise model.','cotations exploitables · BSM européen ; aucune chaîne temps réel ni exercice américain.'))
    if not result['rejected'].empty:
        st.warning(tr(f"{len(result['rejected'])} rows excluded; they are not treated as zero volatility.",f"{len(result['rejected'])} lignes exclues ; elles ne sont pas assimilées à une volatilité nulle."))
        table(result['rejected'],tr('Rejected rows','Lignes rejetées'))
    labels={'chain':tr('Smile & surface','Smile et surface'),'position':tr('Price & cash Greeks','Prix et cash Greeks'),
            'scenario':tr('Scenario P&L','P&L de scénario'),'hedge':tr('Delta hedge','Couverture delta'),'greeks':tr('Greeks maps','Cartes des Greeks')}
    view=st.segmented_control(tr('Analysis','Analyse'),list(labels),default=lab.view,required=True,format_func=labels.get,key='eqd_view',width='stretch')
    lab.view=view
    if view=='chain':
        render_chain(lab,chain)
    else:
        render_position_inputs(lab)
        try:
            if view=='position':render_position(lab)
            elif view=='scenario':render_scenario(lab)
            elif view=='hedge':render_hedge(lab)
            else:render_greeks(lab)
        except (ValueError,TypeError,OverflowError) as exc:
            st.warning(str(exc))
    with st.expander(tr('Workbook & conventions','Rapport et conventions')):
        st.caption(tr('Cash Delta = quantity × multiplier × Delta × spot. Cash Gamma = quantity × multiplier × Gamma × spot²; 1% Gamma P&L = ½ × cash Gamma × 0.01². Vega is per vol point, Theta per calendar day, Rho per +1 percentage point (100 bp).',
            'Cash Delta = quantité × multiplicateur × Delta × spot. Cash Gamma = quantité × multiplicateur × Gamma × spot² ; P&L Gamma à 1 % = ½ × cash Gamma × 0,01². Vega par point de vol, Theta par jour calendaire, Rho par +1 point de taux (100 pb).'))
        from components.lab_report import render_lab_export
        render_lab_export()
    with st.expander(tr('Additional option tools', 'Outils options complémentaires')):
        from components.global_header import navigate
        st.button(tr('Open book options, strategies & Interactive Greeks', 'Ouvrir les options du portefeuille, stratégies et Greeks interactifs'),
                  key='eqd_legacy_tools',on_click=navigate,args=('derivatives',))


def render_chain(lab,chain):
    expiries=sorted(chain.maturity.unique());saved=lab.selected_maturity
    lab.selected_maturity=st.selectbox(tr('Maturity','Échéance'),expiries,index=expiries.index(saved) if saved in expiries else 0,key='eqd_expiry')
    chosen=chain[chain.maturity.eq(lab.selected_maturity)];m=smile_metrics(chosen)
    metrics([(tr('ATM IV (K/S = 1)','IV ATM (K/S = 1)'),metric_value(m['atm_iv'],True)),
             (tr('90% − ATM · vol pt','90 % − ATM · pt vol'),metric_value(None if m['downside_skew'] is None else m['downside_skew']*100)),
             (tr('25Δ RR · Call − Put','RR 25Δ · Call − Put'),metric_value(None if m['risk_reversal_25'] is None else m['risk_reversal_25']*100))])
    if m['downside_skew'] is not None:
        skew=m['downside_skew']*100
        st.write(tr(f'90% strike IV is {skew:+.2f} vol points versus ATM. This slice prices downside protection '+('more' if skew>0 else 'less')+' richly in volatility terms; it does not establish the cause or predict returns.',
                    f'L’IV au strike 90 % est à {skew:+.2f} points de vol de l’ATM. La protection baissière est '+('plus' if skew>0 else 'moins')+' chère en volatilité sur cette tranche ; cela n’établit ni la cause ni une prévision de rendement.'))
    views={'heatmap':tr('Surface heatmap','Surface en heatmap'),'surface':tr('3D surface','Surface 3D'),
           'smile':tr('Smile by maturity','Smile par échéance'),'term':tr('ATM term structure','Structure par terme ATM')}
    view=st.selectbox(tr('Volatility view','Vue volatilité'),list(views),index=list(views).index(lab.volatility_view),format_func=views.get,key='eqd_surface_view')
    lab.volatility_view=view
    if view in ('heatmap','surface'):
        data=empirical_smile(chain);grid=data.pivot(index='time_to_maturity',columns='moneyness',values='implied_volatility')*100
        fig=go.Figure(go.Heatmap(x=grid.columns,y=grid.index,z=grid.values,colorbar_title='IV %',colorscale='Blues',connectgaps=False)) if view=='heatmap' else go.Figure(go.Surface(x=grid.columns,y=grid.index,z=grid.values,colorbar_title='IV %',colorscale='Blues',connectgaps=False))
        fig.update_layout(title=tr('Empirical implied volatility · %','Volatilité implicite empirique · %'),xaxis_title='K / S',yaxis_title=tr('Years','Années'),scene=dict(xaxis_title='K / S',yaxis_title=tr('Years','Années'),zaxis_title='IV %'))
        plot(fig,'eqd_surface',380)
        st.caption(tr('OTM put below the forward, call above; opposite type only if preferred quote is missing. Missing cells remain gaps. No arbitrage-free calibration is claimed.',
            'Put sous le forward, call au-dessus ; autre type uniquement si la cotation préférée manque. Les cellules manquantes restent vides. Aucune calibration sans arbitrage revendiquée.'))
    elif view=='smile':
        axis=st.radio(tr('Horizontal axis','Axe horizontal'),['moneyness','strike'],horizontal=True,key='eqd_smile_axis')
        plot(px.line(chosen.assign(iv_pct=chosen.implied_volatility*100),x=axis,y='iv_pct',color='option_type',markers=True,
            labels={'iv_pct':'IV %','moneyness':'K / S','strike':'Strike'}),'eqd_smile')
    else:
        term=term_structure(chain)
        plot(px.line(term['data'].assign(iv_pct=term['data'].atm_iv*100),x='time_to_maturity',y='iv_pct',markers=True,
            labels={'time_to_maturity':tr('Years','Années'),'iv_pct':'ATM IV %'}),'eqd_term')
        shapes={'insufficient maturities':'échéances insuffisantes','approximately flat':'quasi plate','upward-sloping':'croissante','downward-sloping':'décroissante','mixed / humped':'mixte / en bosse'}
        st.caption(tr('Descriptive shape: '+term['shape'],'Forme descriptive : '+shapes[term['shape']]))
        table(term['data'])
    rows=[{'metric':k,'value_decimal':v,'method':m['methods'].get(k,'difference of the stated IV observations')} for k,v in m.items() if k!='methods']
    table(pd.DataFrame(rows),tr('Skew metrics & interpolation','Mesures de skew et interpolation'))
    table(chosen,tr('Chain and Greeks per option unit','Chaîne et Greeks par unité d’option'))
    indices=chosen.index.tolist()
    selected=st.selectbox(tr('Quote to use as position input','Cotation à utiliser pour la position'),indices,
        format_func=lambda i:f"{chosen.loc[i,'option_type']} · K {chosen.loc[i,'strike']:g} · IV {chosen.loc[i,'implied_volatility']:.2%}",key='eqd_quote')
    st.button(tr('Load quote into position','Charger la cotation dans la position'),key='eqd_load_quote',on_click=_load_quote,args=(chosen.loc[selected].to_dict(),))


def render_position_inputs(lab):
    p=lab.position
    with st.expander(tr('Position inputs','Paramètres de la position'),expanded=True):
        a,b,c,d=st.columns(4)
        kind=a.selectbox('Call / Put',['Call','Put'],index=['Call','Put'].index(p.option_type),key='eqd_pos_kind',on_change=_mark_position_input)
        spot=b.number_input('Spot',min_value=.01,value=float(p.spot),key='eqd_pos_spot',on_change=_mark_position_input)
        strike=c.number_input('Strike',min_value=.01,value=float(p.strike),key='eqd_pos_strike',on_change=_mark_position_input)
        years=d.number_input(tr('Remaining years · ACT/365','Années restantes · ACT/365'),min_value=.0001,max_value=50.,value=float(p.maturity),format='%.6f',key='eqd_pos_time',on_change=_mark_position_input)
        a,b,c,d=st.columns(4)
        vol=a.number_input('IV %',min_value=.01,max_value=6400.,value=float(p.volatility*100),key='eqd_pos_vol',on_change=_mark_position_input)/100
        rate=b.number_input(tr('Continuous rate %','Taux continu %'),min_value=-50.,max_value=100.,value=float(p.rate*100),key='eqd_pos_rate',on_change=_mark_position_input)/100
        dividend=c.number_input(tr('Dividend yield %','Rendement dividende %'),min_value=-50.,max_value=100.,value=float(p.dividend*100),key='eqd_pos_div',on_change=_mark_position_input)/100
        quantity=d.number_input(tr('Signed contracts','Contrats signés'),value=float(p.quantity),key='eqd_pos_quantity',on_change=_mark_position_input)
        a,b=st.columns(2)
        multiplier=a.number_input(tr('Units per contract','Unités par contrat'),min_value=.01,value=float(p.multiplier),key='eqd_pos_multiplier',on_change=_mark_position_input)
        lab.currency=b.selectbox(tr('Quote currency','Devise de cotation'),['USD','EUR','GBP','JPY'],index=['USD','EUR','GBP','JPY'].index(lab.currency),key='eqd_pos_currency')
        st.caption(tr('Currency labels option and curve-lab amounts; changing it does not perform FX conversion.', 'La devise libelle les montants des labos options et courbe ; la modifier ne réalise aucune conversion FX.'))
        lab.position=OptionPosition(kind,spot,strike,years,rate,vol,dividend,quantity,multiplier)
        st.caption(tr('Input source','Source des saisies')+': '+lab.position_source)


def render_position(lab):
    p=lab.position;a=position_analytics(p)
    metrics([(tr('Price / option unit','Prix / unité option'),metric_value(a['price'])),('Cash Delta · '+lab.currency,metric_value(a['cash_delta'])),('Vega / vol pt · '+lab.currency,metric_value(a['vega_1vol_point'])),('Theta / day · '+lab.currency,metric_value(a['theta_daily']))])
    from engines.options_pricing_engine import black_scholes_price
    spots=np.linspace(.7*p.spot,1.3*p.spot,51)
    values=[black_scholes_price(p.option_type,s,p.strike,p.maturity,p.rate,p.volatility,p.dividend) for s in spots]
    plot(go.Figure(go.Scatter(x=spots,y=values)).update_layout(xaxis_title='Spot',yaxis_title=lab.currency,title=tr('Option price versus spot','Prix d’option selon le spot')),'eqd_price')
    table(pd.DataFrame([a]).T.reset_index().rename(columns={'index':'metric',0:'value'}),tr('All per-unit and position Greeks','Tous les Greeks unitaires et de position'))


def render_scenario(lab):
    s=lab.scenario;p=lab.position
    a,b,c,d=st.columns(4)
    equity=a.number_input(tr('Spot shock %','Choc spot %'),min_value=-99.,max_value=200.,value=float(s.equity*100),key='lab_spot_shock')/100
    vol=b.number_input(tr('Vol shock · points','Choc vol · points'),value=float(s.volatility*100),key='lab_vol_shock')/100
    rate=c.number_input(tr('Parallel rate shock · bp','Choc parallèle de taux · pb'),min_value=-500.,max_value=1000.,value=float(s.rate_bp),key='lab_rate_shock')
    days=d.number_input(tr('Elapsed calendar days','Jours calendaires écoulés'),min_value=0.,value=float(s.elapsed_days),key='lab_days')
    lab.scenario=replace(s,name='Custom',equity=equity,volatility=vol,rate_bp=rate,elapsed_days=days)
    st.caption(tr('Rates and the curve twist are shared with Curves. Time must remain before expiry; shocked IV must be positive.',
        'Les taux et le twist de courbe sont partagés avec Courbes. Le temps doit rester avant l’échéance ; l’IV choquée doit être positive.'))
    if lab.scenario.curve_twist:st.caption(f"Twist (tenor years, bp): {lab.scenario.curve_twist}")
    result=option_scenario(p,lab.scenario)
    metrics([(tr('Full revaluation','Revalorisation complète'),metric_value(result['full'])),(tr('Greek approximation','Approximation Greeks'),metric_value(result['approximation'])),(tr('Residual','Résidu'),metric_value(result['residual']))])
    plot(go.Figure(go.Waterfall(x=['Delta','Gamma','Vega','Theta','Rho',tr('Residual','Résidu'),tr('Full P&L','P&L total')],
        y=[*result['parts'].values(),result['residual'],result['full']],measure=['relative']*6+['total'])).update_layout(yaxis_title=lab.currency),'eqd_waterfall')
    st.caption(tr('Residual = full revaluation − local Greek approximation. Cross terms and higher orders are not included in the five-Greek approximation.',
        'Résidu = revalorisation complète − approximation locale. Les termes croisés et d’ordre supérieur ne figurent pas dans l’approximation à cinq Greeks.'))
    a,b=st.columns(2)
    extent=a.slider(tr('Matrix spot range ± %','Amplitude spot de matrice ± %'),5,40,int(round(max(lab.matrix_spots)*100)),5,key='eqd_matrix_spot')
    vol_extent=b.slider(tr('Matrix vol range ± points','Amplitude vol de matrice ± points'),2,30,int(max(lab.matrix_vol_points)),2,key='eqd_matrix_vol')
    lab.matrix_spots=tuple(np.linspace(-extent/100,extent/100,7));lab.matrix_vol_points=tuple(np.linspace(-vol_extent,vol_extent,5))
    grid=scenario_matrix(p,lab.matrix_spots,lab.matrix_vol_points)
    matrix=grid.pivot(index='vol_points',columns='spot_shock',values='pnl')
    fig=go.Figure(go.Heatmap(x=matrix.columns*100,y=matrix.index,z=matrix.values,colorscale='RdBu',zmid=0,colorbar_title=lab.currency,connectgaps=False))
    fig.add_scatter(x=[0],y=[0],mode='markers',marker=dict(symbol='diamond-open',size=16,color='#eabc63'),name=tr('Base = 0','Base = 0'))
    plot(fig.update_layout(xaxis_title=tr('Spot shock %','Choc spot %'),yaxis_title=tr('Vol points','Points de vol'),title=tr('Instantaneous spot / vol P&L','P&L instantané spot / vol')),'eqd_matrix')
    st.caption(tr('Matrix holds rates and time fixed; its zero-shock cell is marked with a diamond.', 'La matrice garde taux et temps fixes ; la cellule sans choc est repérée par un losange.'))
    if grid.pnl.isna().any():st.caption(tr('Blank cells: shocked IV is nonpositive; no volatility floor is imposed.','Cellules vides : IV choquée non positive ; aucun plancher de vol imposé.'))
    table(grid)


def render_hedge(lab):
    a,b=st.columns(2)
    equity=a.slider(tr('Hedge test · spot %','Test couverture · spot %'),-40.,40.,float(np.clip(lab.hedge_scenario.equity*100,-40,40)),key='eqd_hedge_spot')/100
    vol=b.number_input(tr('Hedge test · vol points','Test couverture · points de vol'),value=float(lab.hedge_scenario.volatility*100),key='eqd_hedge_vol')/100
    shock=MarketScenario('Instantaneous hedge',equity=equity,volatility=vol)
    result=delta_hedge(lab.position,shock)
    # Persist the tested hedge assumptions explicitly for the workbook/dashboard.
    lab.hedge_scenario=shock
    metrics([(tr('Hedge units','Unités de couverture'),metric_value(result['hedge_units'])),(tr('Hedge cash value','Valeur de la couverture'),metric_value(result['hedge_cash_value'])),(tr('Unhedged P&L','P&L non couvert'),metric_value(result['unhedged_pnl'])),(tr('Net hedged P&L','P&L net couvert'),metric_value(result['net_pnl']))])
    plot(go.Figure(go.Bar(x=['Option',tr('Underlying hedge','Couverture sous-jacent'),tr('Net','Net')],y=[result['option_pnl'],result['hedge_pnl'],result['net_pnl']])).update_layout(yaxis_title=lab.currency),'eqd_hedge')
    st.caption(tr('Instantaneous spot/vol shock, unchanged rates and time; excludes transaction costs and funding. Delta is neutral only at the initial spot. Gamma, Vega and Theta remain.',
        'Choc instantané spot/vol, taux et temps fixes ; sans coûts de transaction ni financement. Le delta est neutre seulement au spot initial. Gamma, Vega et Theta subsistent.'))
    table(pd.DataFrame([result]).T.reset_index().rename(columns={'index':'metric',0:'value'}))


def render_greeks(lab):
    name=st.selectbox(tr('Greek map','Carte de Greek'),['delta','gamma','vega_1pct'],key='eqd_greek')
    data=greek_grid(lab.position,name)
    plot(go.Figure(go.Heatmap(x=data.columns,y=data.index,z=data.values,colorbar_title=name,colorscale='Blues')).update_layout(xaxis_title='Spot',yaxis_title=tr('Remaining years','Années restantes'),title=tr('Per-option-unit sensitivity','Sensibilité par unité d’option')),'eqd_greek_map')
    st.caption(tr('Gamma typically concentrates near ATM at short maturities; Vega usually grows with maturity near ATM. All other inputs are held fixed.',
        'Le Gamma se concentre généralement près de l’ATM à courte échéance ; le Vega croît généralement avec la maturité près de l’ATM. Les autres paramètres restent fixes.'))
