"""Compact public market browsing; the existing book analytics are kept separately."""
import streamlit as st
from core.securities import DIRECTORY,TICKER_IDS,ASSET_GROUPS
from core.monitor_copy import tr,asset_label
from components.market_ui import quote_table,sessions

def render(state):
    st.markdown('<div class="monitor-heading">'+tr('Across the markets','Vue des marchés')+'</div>',unsafe_allow_html=True)
    labels={g:asset_label(g) for g in ASSET_GROUPS}
    group=st.segmented_control(tr('Asset class','Classe d’actifs'),ASSET_GROUPS,default='Overview',format_func=labels.get,key='market_asset_class',required=True,label_visibility='collapsed')
    ids=list(TICKER_IDS) if group=='Overview' else [s.id for s in DIRECTORY if s.asset_class==group]
    st.caption(tr('Public observations, delayed or indicative. Select an instrument for its chart, sources and analytics.','Observations publiques, différées ou indicatives. Ouvrez un instrument pour son graphique, ses sources et ses analyses.'))
    quotes=quote_table(ids,'market_rows_'+group)
    if group=='Rates':st.caption(tr('US yields: daily Treasury par yield observations. German 10Y: monthly OECD average, not a tradable intraday Bund quote.','Taux US : rendements au pair quotidiens du Trésor. Allemagne 10 ans : moyenne mensuelle OCDE, pas une cotation Bund intrajournalière.'))
    if group=='Commodities':st.caption(tr('Continuous front futures: contract rolls affect historical returns. These are not spot commodity prices.','Futures proches continus : les changements de contrat influencent les rendements. Ces prix ne sont pas des cours au comptant.'))
    with st.expander(tr('Global sessions','Séances mondiales')):sessions()
    from components.market_analytics import correlations,benchmark_curve,fx_crosses
    from components.market_context import news_panel
    view=st.segmented_control(tr('More context','Plus de contexte'),('none','correlation','news','detail'),default='none',format_func={'none':tr('Quotes only','Cotations seules'),'correlation':tr('Correlation','Corrélation'),'news':tr('Headlines','Actualités'),'detail':tr('Curve / cross rates / movers','Courbe / taux croisés / variations')}.get,required=True,key='market_context')
    if view=='correlation':correlations(['SPX','SX5E','NIKKEI','EURUSD','US10Y','GOLD','BTC'] if group=='Overview' else ids,'asset_corr_'+group)
    elif view=='news':news_panel(ids[:6],'asset_news',limit=6)
    elif view=='detail':
        if group=='Rates':benchmark_curve(quotes)
        elif group=='FX':fx_crosses(quotes)
        else:
            from components.global_header import open_security
            movers=sorted(((id,r.value) for id,r in quotes.items() if r.value and r.value.change_pct is not None and r.value.frequency!='monthly average' and r.value.security_id not in ('US2Y','US5Y','US10Y','US30Y')),key=lambda item:abs(item[1].change_pct),reverse=True)[:3]
            st.caption(tr('Largest absolute percentage moves in this selected universe; not an all-market ranking.','Plus fortes variations absolues en pourcentage dans cet univers ; pas un classement de tout le marché.'))
            for id,q in movers:st.button(f'{id} · {q.change_pct:+.2f}%',key='mover_'+id,on_click=open_security,args=(id,))
