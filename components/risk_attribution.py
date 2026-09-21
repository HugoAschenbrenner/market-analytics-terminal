"""Shared view of transparent Euler attribution; input units are explicitly labelled."""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from components.lab_common import tr,plot,metrics,metric_value,table
from services.lab import get_lab
from engines.risk_factor_engine import covariance_estimate,covariance_attribution,correlation_stress


def render_attribution(observations: pd.DataFrame, weights, confidence=.95, horizon=1, unit='return / observation', source='USER INPUT', covariance=None, estimator='sample'):
    lab=get_lab()
    st.subheader(tr('Gaussian risk attribution & correlation stress','Attribution du risque gaussien et stress de corrélation'))
    blend=st.slider(tr('Correlation blend: −1 independence · +1 all correlations +1','Mélange corrélation : −1 indépendance · +1 toutes à +1'),-1.,1.,float(lab.scenario.correlation),.05,key='lab_corr_blend')
    from dataclasses import replace
    lab.scenario=replace(lab.scenario,correlation=blend)
    if covariance is None:covariance,_=covariance_estimate(observations)
    base=covariance_attribution(covariance,weights,observations.columns,confidence,horizon)
    stress=covariance_attribution(correlation_stress(covariance,blend),weights,observations.columns,confidence,horizon)
    metrics([(tr('Gaussian VaR','VaR gaussienne'),metric_value(base['parametric_var'])),
             (tr('Correlation-stressed VaR','VaR sous stress de corrélation'),metric_value(stress['parametric_var'])),
             (tr('Component VaR sum','Somme des VaR composantes'),metric_value(base['contributions'].component_var.sum()))])
    st.caption(f'{source} · {unit} · {confidence:.1%} · horizon {horizon} '+tr('observations. Zero mean; square-root-of-time scaling; {estimator} covariance. Historical VaR/CVaR remains separate. Marginal risk is per unit of the displayed weight.'.format(estimator=estimator),
        'observations. Moyenne nulle ; échelle racine du temps ; covariance {estimator}. VaR/CVaR historiques séparées. Risque marginal par unité du poids affiché.'.format(estimator=estimator)))
    st.caption(tr('Positive blend moves covariance toward all +1 correlations; negative blend toward independence. Variances stay fixed and the matrix stays positive semidefinite. This is not a uniform additive rho shock.',
        'Mélange positif vers des corrélations toutes à +1 ; négatif vers l’indépendance. Variances fixes et matrice semi-définie positive. Ce n’est pas un choc additif uniforme de rho.'))
    a,b=st.columns(2)
    with a:plot(px.bar(base['contributions'],x='id',y='component_var',labels={'id':tr('Position','Position'),'component_var':tr('Component VaR','VaR composante')}),'lab_risk_contributions')
    with b:
        pca=base['pca']
        fig=px.bar(pca,x='component',y=['variance_explained','portfolio_variance_share'],barmode='group',labels={'value':tr('Variance share','Part de variance'),'component':tr('Component','Composante')})
        names={'variance_explained':tr('Overall explained variance','Variance globale expliquée'),
               'portfolio_variance_share':tr('Portfolio variance share','Part de variance du portefeuille')}
        for trace in fig.data:
            trace.name=names[trace.name]
        fig.update_layout(legend_orientation='v')
        plot(fig,'lab_risk_pca')
    st.caption(tr('PCA uses covariance eigenvectors: overall explained variance differs from the portfolio’s variance allocation. PCA signs are conventional; components are statistical, not named economic factors.',
        'ACP sur les vecteurs propres de covariance : variance globale expliquée distincte de l’allocation de variance du portefeuille. Signes conventionnels ; composantes statistiques, pas facteurs économiques nommés.'))
    table(base['contributions'],tr('Marginal, component & percentage risk','Risques marginal, composante et pourcentage'))
    table(pca,tr('PCA exposures & cumulative explained variance','Expositions ACP et variance expliquée cumulée'))
    lab.risk_tables={'Risk_Attribution':base['contributions'],'Risk_PCA':pca,
        'Risk_Stress':pd.DataFrame([{'confidence':confidence,'horizon':horizon,'unit':unit,'source':source,
            'base_var':base['parametric_var'],'stressed_var':stress['parametric_var'],'correlation_blend':blend}])}
    lab.risk_source=source+' · '+unit
    with st.expander(tr('Export attribution','Exporter l’attribution')):
        from components.lab_report import render_lab_export
        render_lab_export()
