"""Compact observed correlations and volatility, linked to the preserved labs."""
import html
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
import plotly.graph_objects as go
from core.securities import SECURITIES
from core.monitor_copy import tr
from core.market_formatting import number
from core.v2_theme import TOKENS
from core.charting import chart
from services.market_monitor import get_market_service
from services.market_statistics import correlation_matrix,realized_volatility


def correlations(ids,key):
    from components.global_header import open_security
    st.subheader(tr('How markets move together','Comment les marchés évoluent ensemble'))
    lookback=st.segmented_control(tr('Matched daily changes','Variations quotidiennes communes'),(20,60,120,252),default=60,format_func=lambda n:f'{n}d' if n!=252 else '1Y · 252d',required=True,key=key+'_window')
    ids=list(dict.fromkeys(ids))[:9];service=get_market_service()
    with ThreadPoolExecutor(max_workers=6) as pool:results=dict(zip(ids,pool.map(lambda id:service.history(id,'5Y' if lookback==252 else '1Y'),ids)))
    histories={id:r.value for id,r in results.items() if r.value is not None}
    matrix,n,excluded,as_of=correlation_matrix(histories,lookback)
    if matrix.empty:
        st.info(tr(f'Need {lookback+1} common complete observations for at least two instruments. No matrix has been estimated.',f'Il faut {lookback+1} observations complètes communes pour au moins deux instruments. Aucune matrice estimée.'))
    else:
        c=TOKENS[st.session_state.terminal.ui.theme]
        # Static semantic HTML stays small; separate instrument buttons route
        # without a full reload, preserving book/lab state.
        header=''.join(f'<th>{html.escape(id)}</th>' for id in matrix.columns)
        rows=''
        for id,row in matrix.iterrows():
            cells=''.join(f'<td style="color:{c["positive"] if value>=0 else c["negative"]}">{number(value,2)}</td>' for value in row)
            rows+=f'<tr><th>{html.escape(id)}</th>{cells}</tr>'
        st.markdown(f'<div class="workshop-table-wrap"><table class="workshop-table"><thead><tr><th></th>{header}</tr></thead><tbody>{rows}</tbody></table></div>',unsafe_allow_html=True)
        st.caption(tr('Pearson correlation','Corrélation de Pearson')+f' · n={n} · {as_of:%Y-%m-%d}')
    labels={id:f'{id} · {SECURITIES[id].name}' for id in ids}
    selected=st.selectbox(tr('Explore an instrument','Explorer un instrument'),ids,index=None,format_func=labels.get,key=key+'_security')
    if st.button(tr('Open security','Ouvrir la fiche'),key=key+'_open',disabled=selected is None):
        open_security(selected);st.rerun()
    st.caption(tr('Price returns (adjusted close for equities/ETFs); yields use changes in basis points, since a yield is not an asset price. Levels are aligned first, with no forward filling; today is excluded. Different closing times and futures rolls can affect correlations. 252 means matched observations, not exactly one calendar year.','Rendements des prix (clôtures ajustées pour actions/ETF) ; variations en points de base pour les taux, qui ne sont pas des prix. Dates communes, aucun remplissage et journée courante exclue. Horaires de clôture et roulements de futures influencent les corrélations. 252 désigne des observations communes, pas exactement un an.'))
    missing=[id for id in ids if id not in histories or id in excluded]
    stale=[id for id,r in results.items() if r.status=='stale']
    if missing:st.caption(tr('Excluded / unavailable: ','Exclus / indisponibles : ')+', '.join(missing))
    if stale:st.warning(tr('Using last successful histories: ','Derniers historiques disponibles : ')+', '.join(stale))


def volatility(id):
    s=SECURITIES[id]
    st.subheader(tr('Realized volatility','Volatilité réalisée'))
    if s.unit in ('yield','vol_index'):
        st.info(tr('A yield or VIX level is not an equity return volatility. Use yield-change correlations or the advanced analytics.','Un taux ou le niveau du VIX ne représente pas une volatilité de rendement actions. Consultez les corrélations de variations de taux ou les analyses avancées.'));return
    window=st.segmented_control(tr('Daily observations','Observations quotidiennes'),(20,60,120,252),default=20,required=True,key='rv_window')
    result=get_market_service().history(id,'5Y')
    if result.value is None:
        st.info(tr('Verified history unavailable.','Historique vérifié indisponible.'));return
    metrics=realized_volatility(result.value,window)
    st.metric(tr('Annualized historical volatility','Volatilité historique annualisée'),number(metrics.annualized*100 if metrics.annualized is not None else None)+'%')
    if not metrics.series.empty:
        chart(go.Figure(go.Scatter(x=metrics.series.tail(252).index,y=metrics.series.tail(252)*100,mode='lines',name='RV')).update_layout(yaxis_title='%',showlegend=False),key='security_rv',height=230)
    st.caption(f'{result.value.source} · {metrics.basis} · n={metrics.observations} · {metrics.as_of}')
    st.caption(tr('Backward-looking dispersion of log returns; current incomplete day excluded. This is not implied volatility or a forecast.','Dispersion passée des rendements logarithmiques ; journée courante exclue. Ce n’est ni une volatilité implicite ni une prévision.'))
    if result.status=='stale':st.warning(tr('Last successful history; refresh failed.','Dernier historique disponible ; actualisation échouée.'))


def benchmark_curve(quotes):
    ids=['US2Y','US5Y','US10Y','US30Y']
    available={id:r.value for id,r in quotes.items() if id in ids and r.value}
    if len(available)<2:return
    dates={q.observed_at.date() for q in available.values()}
    if len(dates)!=1:
        st.info(tr('Curve points have different dates; no same-day curve/spread is calculated.','Dates différentes entre les points ; aucune courbe ni spread du même jour calculé.'));return
    ids=[id for id in ids if id in available]
    fig=go.Figure(go.Scatter(x=[int(id[2:-1]) for id in ids],y=[available[id].price for id in ids],mode='lines+markers',name='US Treasury'))
    fig.update_layout(xaxis_title=tr('Maturity (years)','Maturité (années)'),yaxis_title='%',showlegend=False)
    chart(fig,key='market_treasury_curve',height=220)
    if all(id in available for id in ('US2Y','US10Y')):st.metric('US 2s10s',number((available['US10Y'].price-available['US2Y'].price)*100,1,True)+' bp')
    st.caption(tr('US Treasury par yields, not zero-coupon discount rates. Common observation date: ','Rendements au pair du Trésor US, pas des taux zéro-coupon. Date commune : ')+str(next(iter(dates))))


def fx_crosses(quotes):
    import pandas as pd
    rates={'USD':1.};dates=[]
    for id,result in quotes.items():
        if not result.value:continue
        q=result.value;dates.append(q.observed_at.date())
        if id.endswith('USD'):rates[id[:3]]=q.price
        elif id.startswith('USD') and q.price>0:rates[id[3:]]=1/q.price
    if len(set(dates))>1:
        st.info(tr('FX dates differ; cross-rate matrix withheld.','Dates FX différentes ; matrice de taux croisés non calculée.'));return
    if len(rates)<2:return
    matrix=pd.DataFrame({quote:{base:rates[base]/rates[quote] for base in rates} for quote in rates})
    st.dataframe(matrix.style.format('{:.4f}'),width='stretch')
    st.caption(tr('Indicative derived cross rates: one unit of row currency in column currency. Same observation date, potentially different quote times; not executable bid/ask prices.','Taux croisés indicatifs calculés : une unité de devise en ligne exprimée dans la devise en colonne. Même date, heures de cotation potentiellement différentes ; pas des prix bid/ask exécutables.'))
