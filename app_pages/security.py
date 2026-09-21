"""One reusable public security view for every instrument in the directory."""
import streamlit as st
import plotly.graph_objects as go
from core.securities import SECURITIES
from core.market_formatting import level,move,number,large
from core.monitor_copy import tr,asset_label
from core.charting import chart
from services.market_monitor import get_market_service
from components.market_ui import provenance

def render(state):
    id=st.query_params.get('security','NVDA')
    if id not in SECURITIES:
        st.info(tr('Unknown instrument. Use the global search.','Instrument inconnu. Utilisez la recherche globale.'));return
    s=SECURITIES[id];service=get_market_service();result=service.quote(id);q=result.value
    st.subheader(f'{s.name} · {s.id}')
    st.caption(f'{asset_label(s.asset_class)} · {s.venue} · {s.currency} · {s.unit}')
    if q:
        with st.container(key='metrics-security'):
            a,b,c=st.columns(3);a.metric(tr('Last level','Dernier niveau'),level(s,q.price));b.metric(tr('Change','Variation'),move(s,q));c.metric(tr('Previous observation','Observation précédente'),level(s,q.previous_close))
    provenance(result,s)
    period=st.segmented_control(tr('Horizon','Horizon'),('1D','5D','1M','6M','YTD','1Y','5Y'),default='1Y',key='security_period',required=True)
    modes=['Line','Area'] if s.unit=='yield' else ['Line','Area','Candlestick','OHLC']
    mode=st.selectbox(tr('Chart','Graphique'),modes,key='security_chart_'+('yield' if s.unit=='yield' else 'price'))
    history=service.history(id,period)
    if history.value is None or history.value.frame.empty:
        st.info(tr('No verified history for this horizon.','Aucun historique vérifié sur cet horizon.'))
    else:
        frame=history.value.frame
        if mode in ('Candlestick','OHLC') and all(c in frame for c in ('open','high','low')):
            cls=go.Candlestick if mode=='Candlestick' else go.Ohlc
            fig=go.Figure(cls(x=frame.index,open=frame.open,high=frame.high,low=frame.low,close=frame.close,name=id))
        else:fig=go.Figure(go.Scatter(x=frame.index,y=frame.close,mode='lines',fill='tozeroy' if mode=='Area' else None,name=id))
        fig.update_layout(xaxis_rangeslider_visible=False,yaxis_title='%' if s.unit=='yield' else s.currency,showlegend=False)
        chart(fig,key='security_price',height=330)
        st.caption(tr('Unadjusted observed prices; UTC timestamps. Intraday views show the latest available session. Daily histories can reflect splits and futures rolls.','Prix observés non ajustés ; horodatage UTC. La vue intrajournalière montre la dernière séance disponible. Les historiques peuvent refléter splits et changements de contrat.'))
    if q and s.unit!='yield':
        with st.expander(tr('Market statistics','Statistiques de marché')):
            pairs=[(tr('Open','Ouverture'),q.stats.get('open')),(tr('High','Plus haut'),q.stats.get('high')),(tr('Low','Plus bas'),q.stats.get('low')),(tr('52W high','Plus haut 52 sem.'),q.stats.get('fiftyTwoWeekHigh')),(tr('52W low','Plus bas 52 sem.'),q.stats.get('fiftyTwoWeekLow'))]
            st.dataframe([{tr('Metric','Mesure'):k,tr('Value','Valeur'):level(s,v)} for k,v in pairs],hide_index=True,width='stretch')
            if s.asset_class in ('Equities','ETFs','Commodities'):
                st.caption(tr('Volume / 63-session average','Volume / moyenne 63 séances')+f': {large(q.stats.get("volume"))} / {large(q.stats.get("averageVolume"))}')
