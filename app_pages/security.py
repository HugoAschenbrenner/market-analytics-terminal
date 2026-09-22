"""One reusable public security view for every instrument in the directory."""
from components.themed_table import compact_table
import streamlit as st
import plotly.graph_objects as go
from core.securities import SECURITIES,peers
from core.market_formatting import level,move,number,large
from core.monitor_copy import tr,asset_label
from core.charting import chart
from services.market_monitor import get_market_service
from components.market_ui import provenance,security_session

def render(state):
    id=st.query_params.get('security','NVDA')
    if id not in SECURITIES:
        st.info(tr('Unknown instrument. Use the global search.','Instrument inconnu. Utilisez la recherche globale.'));return
    s=SECURITIES[id];service=get_market_service();result=service.quote(id);q=result.value
    st.subheader(f'{s.name} · {s.id}')
    st.caption(f'{asset_label(s.asset_class)} · {s.venue} · {s.currency} · {s.unit}')
    if q:
        with st.container(key='metrics-security'):
            a,b,c,d=st.columns(4);a.metric(tr('Last level','Dernier niveau'),level(s,q.price));b.metric(tr('Change','Variation'),move(s,q));c.metric(tr('Absolute change','Variation absolue'),number(q.change,4 if s.unit=='fx' else 2,True)+(' pp' if s.unit=='yield' else ''));d.metric(tr('Previous observation','Observation précédente'),level(s,q.previous_close))
    st.caption(security_session(s,q))
    provenance(result,s)
    from core.board import add_to_board,board_ids
    st.button(tr('Add to Board','Ajouter au Board') if id not in board_ids() else tr('Already on Board','Déjà dans le Board'),key='security_add_board',disabled=id in board_ids() or len(board_ids())>=30,on_click=add_to_board,args=(id,))
    from components.market_context import news_panel,events_panel,fundamentals_panel
    from components.market_analytics import volatility,correlations
    views=['summary','volatility','correlation','news','events']+(['fundamentals'] if s.asset_class in ('Equities','ETFs') else [])
    labels={'summary':tr('Overview','Vue générale'),'volatility':tr('Volatility','Volatilité'),'correlation':tr('Peers / correlation','Pairs / corrélation'),'news':tr('News','Actualités'),'events':tr('Events','Événements'),'fundamentals':tr('Fundamentals','Fondamentaux')}
    view=st.segmented_control(tr('Security context','Contexte de l’instrument'),views,default='summary',format_func=labels.get,key='security_view',required=True)
    if view=='summary':render_chart(s,service,state)
    elif view=='volatility':volatility(id)
    elif view=='correlation':correlations([id,*peers(s)],'security_corr')
    elif view=='news':news_panel([id]+(['Fed','ECB'] if s.asset_class in ('FX','Rates') else []),'security_news',limit=8)
    elif view=='events':events_panel(id)
    elif view=='fundamentals':fundamentals_panel(id)
    analytical_links(s,q)


def render_chart(s,service,state):
    id=s.id;q=service.quote(id).value
    control,chart_control=st.columns([3,1])
    period=control.segmented_control(tr('Horizon','Horizon'),('1D','5D','1M','6M','YTD','1Y','5Y'),default='1Y',key='security_period',required=True)
    modes=['Line','Area'] if s.unit=='yield' else ['Line','Area','Candlestick','OHLC']
    mode=chart_control.selectbox(tr('Chart','Graphique'),modes,key='security_chart_'+('yield' if s.unit=='yield' else 'price'))
    history=service.history(id,period)
    if history.value is None or history.value.frame.empty:
        st.info(tr('No verified history for this horizon.','Aucun historique vérifié sur cet horizon.'))
    else:
        frame=history.value.frame
        if mode in ('Candlestick','OHLC') and all(c in frame for c in ('open','high','low')):
            from core.v2_theme import TOKENS
            colors=TOKENS[state.ui.theme]
            cls=go.Candlestick if mode=='Candlestick' else go.Ohlc
            fig=go.Figure(cls(x=frame.index,open=frame.open,high=frame.high,low=frame.low,close=frame.close,name=id,increasing_line_color=colors['positive'],decreasing_line_color=colors['negative']))
        else:fig=go.Figure(go.Scatter(x=frame.index,y=frame.close,mode='lines',fill='tozeroy' if mode=='Area' else None,name=id))
        fig.update_layout(xaxis_rangeslider_visible=False,yaxis_title='%' if s.unit=='yield' else 'points' if s.unit in ('index','vol_index') else s.unit if s.asset_class=='Commodities' else s.currency,showlegend=False)
        chart(fig,key='security_price',height=330)
        st.caption(tr('Unadjusted observed prices; UTC timestamps. Intraday views show the latest available session. Daily histories can reflect splits and futures rolls.','Prix observés non ajustés ; horodatage UTC. La vue intrajournalière montre la dernière séance disponible. Les historiques peuvent refléter splits et changements de contrat.'))
        if history.status=='stale':st.warning(tr('Chart uses the last successful history; refresh failed.','Le graphique utilise le dernier historique disponible ; actualisation échouée.'))
    if q and s.unit!='yield':
        with st.expander(tr('Market statistics','Statistiques de marché')):
            pairs=[(tr('Open','Ouverture'),q.stats.get('open')),(tr('High','Plus haut'),q.stats.get('high')),(tr('Low','Plus bas'),q.stats.get('low')),(tr('52W high','Plus haut 52 sem.'),q.stats.get('fiftyTwoWeekHigh')),(tr('52W low','Plus bas 52 sem.'),q.stats.get('fiftyTwoWeekLow'))]
            compact_table([{tr('Metric','Mesure'):k,tr('Value','Valeur'):level(s,v)} for k,v in pairs])
            if s.asset_class in ('Equities','ETFs','Commodities'):
                st.caption(tr('Volume / 63-session average','Volume / moyenne 63 séances')+f': {large(q.stats.get("volume"))} / {large(q.stats.get("averageVolume"))}')


def analytical_links(s,q):
    from components.global_header import navigate,open_security
    from services.security_workflows import open_options,open_fx
    with st.expander(tr('Continue into analytics','Poursuivre dans les analyses')):
        st.caption(tr('Observed security data and book/lab assumptions are separate. Transfers require an explicit action.','Données observées et hypothèses des labos/portefeuilles sont séparées. Un transfert exige une action explicite.'))
        if s.asset_class in ('Equities','Indexes','ETFs') and s.currency in ('USD','EUR','GBP','JPY'):
            st.info(tr('No verified option chain / market IV is attached to this security. Realized volatility is not a substitute for implied volatility. The lab chain remains separately labelled.','Aucune chaîne d’options / IV de marché vérifiée n’est rattachée à cet instrument. La volatilité réalisée ne remplace pas l’implicite. La chaîne du labo conserve son propre libellé.'))
            vol=st.number_input(tr('Model volatility assumption (%)','Hypothèse de volatilité du modèle (%)'),min_value=.1,max_value=300.,value=20.,key='security_assumed_vol')
            st.button(tr('Use this spot in Options Lab · ATM example','Utiliser ce spot dans le labo options · exemple ATM'),key='security_open_options',disabled=q is None,on_click=open_options,args=(s.id,q,vol/100))
        if s.asset_class=='FX':
            st.caption(tr('Transfers the pair and observed spot. Domestic/foreign rates and option volatility remain separate user/model inputs.','Transfère la paire et le spot observé. Taux domestique/étranger et volatilité restent des hypothèses distinctes.'))
            st.button(tr('Open FX analytics with this pair','Ouvrir les analyses FX avec cette paire'),key='security_open_fx',on_click=open_fx,args=(s.id,q))
        st.button(tr('Open advanced analytics','Ouvrir les analyses avancées'),key='security_advanced',on_click=navigate,args=('analytics',))
        st.button(tr('Open Portfolio / Risk','Ouvrir Portefeuille / Risque'),key='security_risk',on_click=navigate,args=('risk',))
