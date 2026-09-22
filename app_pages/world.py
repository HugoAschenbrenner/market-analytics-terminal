import streamlit as st
from core.monitor_copy import tr
from components.market_ui import sessions,quote_table
from components.market_context import news_panel,events_panel

REGIONS={
 'Americas':(['SPX','US10Y','WTI'],['SPX','DJI']),
 'Europe':(['SX5E','EURUSD','BRENT'],['SX5E','CAC']),
 'Asia-Pacific':(['NIKKEI','HSI','USDJPY'],['NIKKEI','HSI']),
}
def render(state):
    st.subheader(tr('World · regions and macro context','Monde · régions et contexte macro'))
    st.caption(tr('Regional feeds and observed benchmarks. Headlines are not a geopolitical risk index or a causal explanation of price moves.','Flux régionaux et indicateurs observés. Les titres ne constituent ni un indice de risque géopolitique ni une explication causale des prix.'))
    labels={'Americas':tr('Americas','Amériques'),'Europe':'Europe','Asia-Pacific':tr('Asia-Pacific','Asie-Pacifique')}
    region=st.segmented_control(tr('Region','Région'),tuple(REGIONS),default='Americas',format_func=labels.get,required=True,key='world_region')
    ids,feeds=REGIONS[region]
    view=st.segmented_control(tr('Context','Contexte'),('headlines','sessions','events'),default='headlines',format_func={'headlines':tr('Regional briefing','Brief régional'),'sessions':tr('Global sessions','Séances mondiales'),'events':tr('Economic calendar','Calendrier économique')}.get,required=True,key='world_view')
    if view=='sessions':sessions()
    elif view=='events':events_panel()
    else:
        quote_table(ids,'world_quotes_'+region)
        policy={'Americas':'Fed','Europe':'ECB'}.get(region)
        if policy:
            st.markdown('#### '+tr('Central bank releases','Publications de la banque centrale'))
            news_panel([policy],'world_policy',region=region,limit=3)
        st.markdown('#### '+tr('Regional market headlines','Actualités des marchés régionaux'))
        news_panel(feeds,'world',region=region,limit=5)
