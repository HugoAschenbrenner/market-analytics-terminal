"""Synthesis of the same laboratory inputs, explicitly separate from book totals."""
import streamlit as st
from components.lab_common import tr,metrics,metric_value
from services.lab import get_lab,option_outputs,curve_outputs


def render_lab_dashboard():
    lab=get_lab()
    st.subheader(tr('Volatility & curve lab · shared analytical snapshot','Labo volatilité et courbe · synthèse analytique partagée'))
    st.caption(tr('These independent examples are not added to portfolio NAV or stress totals. Change their inputs in Equity Derivatives and Curves; this panel recomputes from the same session inputs.',
        'Ces exemples indépendants ne sont pas ajoutés à la VL ni aux stress du portefeuille. Modifiez leurs paramètres dans Equity Derivatives et Courbes ; cette synthèse recalcule depuis les mêmes saisies de session.'))
    try:
        data=option_outputs(lab);smile=data['smile'];position=data['position'];scenario=data['scenario']
        metrics([('ATM IV',metric_value(smile['atm_iv'],True)),(tr('Downside skew · vol pt','Skew baissier · pt vol'),metric_value(None if smile['downside_skew'] is None else smile['downside_skew']*100)),
            ('Vega / vol pt · '+lab.currency,metric_value(position['vega_1vol_point'])),(tr('Option scenario P&L','P&L scénario option'),metric_value(scenario['full']))])
        st.caption(f"{lab.source} · chain {lab.as_of} · {data['maturity']} · "+tr('Position','Position')+f': {lab.position_source} · {lab.currency}')
        st.write(tr(f"Position cash Delta {position['cash_delta']:+,.2f}; Vega {position['vega_1vol_point']:+,.2f} per vol point. The selected scenario gives {scenario['full']:+,.2f}, with a {scenario['residual']:+,.2f} residual versus local Greeks.",
            f"Cash Delta {position['cash_delta']:+,.2f} ; Vega {position['vega_1vol_point']:+,.2f} par point de vol. Le scénario choisi donne {scenario['full']:+,.2f}, avec un résidu de {scenario['residual']:+,.2f} face aux Greeks locaux."))
    except (ValueError,TypeError) as exc:st.warning(tr('EQD inputs need correction: ','Saisies EQD à corriger : ')+str(exc))
    try:
        data=curve_outputs(lab);risk=data['risk'];largest=risk['buckets'].loc[risk['buckets'].dv01.abs().idxmax()]
        metrics([('2s10s · bp',metric_value(data['spreads']['2s10s_bp'])),('Curve DV01 / bp',metric_value(risk['dv01'])),
            (tr('Largest curve bucket','Plus grand pilier de courbe'),f'{largest.tenor:g}Y'),(tr('Curve scenario P&L','P&L scénario courbe'),metric_value(risk['pnl']))])
        st.caption(f"{lab.curve_source} · {lab.currency} · "+tr('Illustrative coupon bond; not the book portfolio.','Obligation illustrative à coupon ; distincte du portefeuille.'))
    except (ValueError,TypeError) as exc:st.warning(str(exc))
    if lab.risk_tables:
        r=lab.risk_tables['Risk_Stress'].iloc[0];contributors=lab.risk_tables['Risk_Attribution']
        largest=contributors.loc[contributors.component_var.idxmax()]
        st.caption(tr('Last computed risk attribution','Dernière attribution de risque calculée')+f" · {lab.risk_source} · Gaussian VaR {r.base_var:.6g} · {r.confidence:.1%} / {r.horizon} observations · "+tr('largest contributor','plus grand contributeur')+f' {largest.id}: {largest.component_var:.6g}')
    else:
        st.caption(tr('Open Portfolio Risk attribution to include its calculated results here.','Ouvrez l’attribution de Portfolio Risk pour inclure ses résultats ici.'))
