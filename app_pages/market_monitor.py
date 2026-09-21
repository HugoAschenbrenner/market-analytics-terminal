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
    quote_table(ids,'market_rows_'+group)
    if group=='Rates':st.caption(tr('US yields: daily constant-maturity observations. German 10Y: monthly OECD average, not a tradable intraday Bund quote.','Taux US : observations quotidiennes à maturité constante. Allemagne 10 ans : moyenne mensuelle OCDE, pas une cotation Bund intrajournalière.'))
    if group=='Commodities':st.caption(tr('Continuous front futures: contract rolls affect historical returns. These are not spot commodity prices.','Futures proches continus : les changements de contrat influencent les rendements. Ces prix ne sont pas des cours au comptant.'))
    with st.expander(tr('Global sessions','Séances mondiales')):sessions()
