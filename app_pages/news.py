import streamlit as st
from core.securities import DIRECTORY,SECURITIES,ASSET_GROUPS
from core.monitor_copy import tr,asset_label
from components.market_context import news_panel

def render(state):
    st.subheader(tr('News desk','Fil d’actualités'))
    a,b,c=st.columns([1,1,2]);labels={k:asset_label(k) for k in ASSET_GROUPS[1:]};labels.update({'All':tr('All','Toutes'),'Central Banks':tr('Central banks','Banques centrales')})
    category=a.selectbox(tr('Category','Catégorie'),['All',*ASSET_GROUPS[1:],'Central Banks'],format_func=labels.get,key='news_category')
    available=[s.id for s in DIRECTORY if category=='All' or s.asset_class==category]
    id=b.selectbox(tr('Instrument','Instrument'),available,index=None,format_func=lambda id:f'{id} · {SECURITIES[id].name}',key='news_security')
    query=c.text_input(tr('Search headlines','Rechercher dans les titres'),key='news_query')
    order=st.radio(tr('Order','Ordre'),('newest','relevance'),format_func={ 'newest':tr('Newest','Plus récents'),'relevance':tr('Search matches','Correspondance à la recherche')}.get,horizontal=True,key='news_order')
    if id:keys=[id]
    elif category=='Central Banks':keys=['Fed','ECB']
    elif category=='All':keys=['SPX','NVDA','BNP','NIKKEI','EURUSD','GOLD','Fed','ECB']
    else:keys=available[:6]
    news_panel(keys,'news',query=query,category=category,order=order,limit=20)
    if order=='relevance':st.caption(tr('Ranks literal search matches in title/description; no sentiment or market-impact score.','Classe les correspondances textuelles dans le titre/résumé ; aucun score de sentiment ou d’impact marché.'))
