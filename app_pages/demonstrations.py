"""Three self-contained, fixed-date demonstrations, without shared-book mutation."""
from dataclasses import asdict
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.lab_common import tr,plot,metrics,metric_value,table
from components.workspace_context import context
from services.demonstrations import collar_demo,eqd_demo,autocallable_demo,DEMO_DATE


def open_demo(choice):
    from components.global_header import navigate
    st.session_state.demo_choice=choice
    navigate('demonstrations')


def _open_eqd():
    from services.lab import get_lab
    from components.global_header import navigate
    demo=eqd_demo();lab=get_lab()
    lab.position=demo['position'];lab.scenario=demo['scenario'];lab.hedge_scenario=demo['scenario'];lab.currency='USD'
    lab.position_source='SYNTHETIC fixed EQD demonstration · 2026-09-09';lab.view='scenario'
    for key in list(st.session_state):
        if key.startswith(('eqd_','lab_spot_','lab_vol_','lab_days','lab_rate_')):del st.session_state[key]
    navigate('equity-derivatives')


def _open_structured():
    from services.structured_lab import demo_structured_lab
    from components.global_header import navigate
    st.session_state.structured_lab=demo_structured_lab()
    st.session_state.structured_mode='lab'
    for key in list(st.session_state):
        if key.startswith('note_independent'):del st.session_state[key]
    navigate('structured-products')


def render(state):
    st.title(tr('Three guided demonstrations','Trois démonstrations guidées'))
    labels={'collar':tr('1 · Protect equity with a collar','1 · Protéger des actions par un collar'),
            'eqd':tr('2 · Option P&L and Delta hedge','2 · P&L option et couverture Delta'),
            'autocallable':tr('3 · Worst-of autocallable','3 · Autocallable worst-of')}
    choice=st.segmented_control(tr('Demonstration','Démonstration'),list(labels),default='collar',format_func=labels.get,required=True,key='demo_choice')
    context(labels[choice],str(DEMO_DATE),'USD','SYNTHETIC',tr('Fixed examples · no provider or upload required · your shared portfolio is unchanged.',
                'Exemples fixes · aucun fournisseur ni fichier requis · votre portefeuille partagé est inchangé.'))
    if choice=='collar': tables=render_collar()
    elif choice=='eqd': tables=render_eqd()
    else: tables=render_note()
    with st.expander(tr('Export this demonstration','Exporter cette démonstration')):
        if st.button(tr('Prepare demonstration workbook','Préparer le rapport de démonstration'),key='demo_report'):
            from reports.desk_report import write_workbook
            tables['Context']=pd.DataFrame([dict(demonstration=choice,valuation_date=str(DEMO_DATE),currency='USD',source='SYNTHETIC',scope='Independent fixed demonstration')])
            st.download_button(tr('Download Excel','Télécharger Excel'),write_workbook(tables),'MAT_demo_'+choice+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def render_collar():
    d=collar_demo();b,a=d['before'],d['after'];marks=a['marks']
    metrics([(tr('Equity position','Position actions'),'1,000 × 100 USD'),(tr('Option premium · debit (+), credit (−)','Prime options · débit (+), crédit (−)'),metric_value(d['premium'])),
             (tr('Cash Delta before → after','Cash Delta avant → après'),f"{b['marks'].delta_cash.sum():,.0f} → {marks.delta_cash.sum():,.0f}")])
    st.write(tr('Buy ten puts at strike 90 and sell ten calls at strike 110, each for 100 shares and six months. The put creates a floor at expiry; the covered call finances part of the put and caps upside.',
                'Achetez dix puts de strike 90 et vendez dix calls de strike 110, chacun pour 100 actions et six mois. Le put crée un plancher à échéance ; le call couvert finance une partie du put et plafonne la hausse.'))
    fig=go.Figure()
    for key,label in [('unprotected',tr('Shares only','Actions seules')),('collar','Collar')]:fig.add_scatter(x=d['payoff'].spot,y=d['payoff'][key],name=label)
    plot(fig.update_layout(xaxis_title=tr('Spot at expiry','Spot à échéance'),yaxis_title=tr('Gross expiry proceeds · USD','Produit brut à échéance · USD')),'demo_collar')
    st.caption(tr('Expiry proceeds exclude the initial share purchase, option premium, funding, fees and dividends. Initial marked cost = 100,000 USD + the signed option premium. Before expiry, spot and volatility still change the mark.',
                  'Le produit à échéance exclut achat initial des actions, prime, financement, frais et dividendes. Coût initial valorisé = 100 000 USD + la prime signée. Avant échéance, spot et volatilité changent encore la valeur.'))
    metrics([(tr('Synthetic 1-day VaR · before → after','VaR synthétique 1 jour · avant → après'),f"{b['var']:,.0f} → {a['var']:,.0f}"),
             (tr('Synthetic 1-day ES · before → after','ES synthétique 1 jour · avant → après'),f"{b['es']:,.0f} → {a['es']:,.0f}")])
    st.caption(tr('97.5% historical quantiles of the same fixed simulated factor shocks, ending 2026-09-09. Hypothetical risk illustration; this is neither observed nor realized portfolio P&L.',
                  'Quantiles historiques à 97,5 % des mêmes chocs de facteurs simulés fixes, finissant le 09/09/2026. Illustration hypothétique ; ce P&L n’est ni observé ni réalisé.'))
    table(d['scenarios'],tr('Instantaneous spot scenarios · USD','Scénarios instantanés de spot · USD'));table(marks,tr('Construction and Greeks','Construction et Greeks'))
    return dict(Positions=marks,Expiry_Proceeds=d['payoff'],Spot_Scenarios=d['scenarios'],Risk_Comparison=pd.DataFrame([dict(case=k,var=v['var'],es=v['es']) for k,v in [('before',b),('after',a)]]))


def render_eqd():
    d=eqd_demo();g=d['greeks'];pnl=d['pnl'];h=d['hedge']
    metrics([(tr('Full repricing P&L','P&L par revalorisation'),metric_value(pnl['full'])),(tr('Hedged P&L','P&L couvert'),metric_value(h['net_pnl'])),
             (tr('Delta after shock + initial hedge','Delta après choc + couverture initiale'),metric_value(h['new_net_delta']))])
    st.write(tr('Ten calls × 100 units, spot/strike 100, six months, 25% volatility and 3% continuous rate. Shock: spot −8%, volatility +4 points, no time passage. A Delta hedge offsets the initial local spot risk; Gamma and Vega remain.',
                'Dix calls × 100 unités, spot/strike 100, six mois, volatilité 25 % et taux continu 3 %. Choc : spot −8 %, vol +4 points, sans temps écoulé. La couverture Delta neutralise le risque local initial de spot ; Gamma et Vega subsistent.'))
    parts={**pnl['parts'],'residual':pnl['residual']}
    plot(go.Figure(go.Waterfall(x=list(parts),y=list(parts.values()),measure=['relative']*len(parts))).update_layout(yaxis_title='USD',title=tr('Local Greeks + residual = full repricing','Greeks locaux + résidu = revalorisation complète')),'demo_eqd')
    metrics([(tr('Initial cash Delta','Cash Delta initial'),metric_value(g['cash_delta'])),('Vega / +1 vol pt',metric_value(g['vega_1vol_point'])),
             (tr('Initial hedge · shares','Couverture initiale · actions'),metric_value(h['hedge_units']))])
    st.caption(tr(f"Rebalance after this shock: {h['rebalance_units']:+.2f} additional shares. Financing, dividends, transaction costs and execution constraints are excluded. The residual contains omitted cross terms and higher orders.",
                  f"Rééquilibrage après ce choc : {h['rebalance_units']:+.2f} actions supplémentaires. Financement, dividendes, coûts et contraintes d’exécution exclus. Le résidu contient les termes croisés omis et les ordres supérieurs."))
    table(pd.DataFrame([g,d['after']],index=['initial','shocked']).reset_index(),tr('Greeks before and after shock','Greeks avant et après choc'))
    st.button(tr('Load this example into the independent EQD lab','Charger cet exemple dans le labo EQD indépendant'),key='demo_open_eqd',on_click=_open_eqd)
    st.caption(tr('This explicit action replaces the independent option/scenario inputs; the shared portfolio is unchanged.',
                  'Cette action explicite remplace les saisies option/scénario indépendantes ; le portefeuille partagé est inchangé.'))
    return dict(Inputs=pd.DataFrame([asdict(d['position'])]),Scenario=pd.DataFrame([asdict(d['scenario'])]),PnL=pd.DataFrame([pnl|{'parts':str(pnl['parts'])}]),Hedge=pd.DataFrame([h]),Greeks=pd.DataFrame([g,d['after']]))


def render_note():
    d=autocallable_demo();s=d['result']['summary'];i=d['inputs']
    metrics([(tr('Model value / 100','Valeur modèle / 100'),metric_value(s['value'])),(tr('Monte Carlo standard error','Erreur standard Monte Carlo'),metric_value(s['mc_error'])),
             (tr('Annual coupon','Coupon annuel'),'8%')])
    st.write(tr('A three-name Phoenix pays conditional quarterly coupons. Missed coupons accumulate in memory. At a scheduled observation, worst-of ≥100% redeems the note early; at maturity, worst-of <60% produces capital loss. Coupon barrier: 70%.',
                'Un Phoenix à trois sous-jacents verse des coupons trimestriels conditionnels. Les coupons manqués sont mémorisés. À une observation, un worst-of ≥100 % rappelle la note ; à échéance, un worst-of <60 % entraîne une perte en capital. Barrière de coupon : 70 %.'))
    fig=go.Figure()
    labels=[tr('Memory recovery / early call','Mémoire récupérée / rappel'),tr('No call / protected capital','Sans rappel / capital protégé'),tr('One severe name / capital loss','Un sous-jacent chute / perte en capital')]
    for path,label in enumerate(labels):
        rows=d['timeline'].query('path == @path and alive_before')
        fig.add_scatter(x=rows.time_years,y=rows.payment,name=label,mode='lines+markers')
    plot(fig.update_layout(xaxis_title=tr('Contractual observation · years','Observation contractuelle · années'),yaxis_title=tr('Investor cash flow / 100','Flux investisseur / 100')),'demo_note_timeline')
    st.caption(tr('Illustrative paths supplied at contractual observations; no continuous barrier monitoring. The initial investment is 100 at time zero and is excluded from the positive payment chart. Paths stop at redemption.',
                  'Trajectoires illustratives aux observations contractuelles ; pas de surveillance continue des barrières. Investissement initial de 100 à la date zéro, exclu des versements positifs du graphique. Les flux s’arrêtent au remboursement.'))
    table(pd.DataFrame({'underlying':d['names'],'initial_fixing':i.initial_spots,'volatility':i.volatilities}),tr('Basket and model assumptions','Panier et hypothèses de modèle'))
    st.caption(tr(f'Maturity {i.maturity_years:g} years · rate {i.risk_free_rate:.1%} continuous · dividend {i.dividend_yield:.1%} · equicorrelation {i.correlation:.0%}.',
                  f'Échéance {i.maturity_years:g} ans · taux {i.risk_free_rate:.1%} continu · dividende {i.dividend_yield:.1%} · équicorrélation {i.correlation:.0%}.'))
    table(d['flows'].assign(scenario=labels),tr('Payoffs and downside cases','Paiements et cas défavorables'))
    table(d['timeline'],tr('Coupon memory and alive status at every observation','Mémoire de coupon et statut à chaque observation'))
    table(pd.DataFrame([d['risk']]),tr('Model sensitivities · common random draws','Sensibilités théoriques · tirages communs'))
    st.caption(tr('3,000 seeded risk-neutral GBM paths, constant vols/correlation, no issuer funding or credit. Per-100 sensitivities are model estimates and can be noisy near barriers; the model value is not an executable quote.',
                  '3 000 trajectoires GBM risque-neutres à graine fixe, vols/corrélation constantes, sans financement ni crédit émetteur. Sensibilités par 100 théoriques, parfois bruitées près des barrières ; valeur non exécutable.'))
    st.button(tr('Load this contract into the independent structured lab','Charger ce contrat dans le labo structuré indépendant'),key='demo_open_note',on_click=_open_structured)
    st.caption(tr('Replaces independent contract inputs only.','Remplace uniquement les paramètres du contrat indépendant.'))
    return dict(Terms=pd.DataFrame([asdict(i)]),Timeline=d['timeline'],Scenario_Cashflows=d['flows'],Sensitivities=pd.DataFrame([d['risk']]))
