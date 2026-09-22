"""V2 navigation: market context and existing analytics share one stable router."""
import streamlit as st
from core.i18n import t
from core.v2_theme import apply_theme
from core.monitor_copy import tr
from core.securities import DIRECTORY, SECURITIES

FAMILIES={
    'markets':('welcome','markets','security'),
    'derivatives':('equity-derivatives','structured-products','derivatives'),
    'analytics':('analytics',),
    'portfolio':('overview','risk','financing'),
    'world':('world',),'news':('news',),'board':('board',),
}
PAGES=tuple(p for family in FAMILIES.values() for p in family)
ALIASES={'home':'overview','cross-asset-dashboard':'overview','fixed-income-risk':'analytics','portfolio-risk':'risk','repo-sec-lending':'financing'}

def page_from_query():
    slug=ALIASES.get(st.query_params.get('page','welcome'),st.query_params.get('page','welcome'))
    return slug if slug in PAGES else 'welcome'

def family_for(page):return next(k for k,v in FAMILIES.items() if page in v)

def navigate(page):
    if page not in PAGES:raise ValueError('Unknown workspace')
    st.query_params['page']=page

def open_security(id):
    if id not in SECURITIES:return
    st.query_params['security']=id
    navigate('security')

def _search():
    selected=st.session_state.get('security_search')
    if selected:open_security(selected)
    st.session_state['security_search']=None

def _family_changed():
    family=st.session_state['desk_section']
    navigate('markets' if family=='markets' else FAMILIES[family][0])

def _page_changed():navigate(st.session_state['workspace'])

def page_label(page):
    if page=='world':return tr('World','Monde')
    if page=='news':return tr('News','Actualités')
    if page=='board':return 'Board'
    if page=='markets':return tr('Market monitor','Vue marchés')
    if page=='analytics':return tr('Rates · FX · Cross-asset','Taux · FX · Multi-actifs')
    if page=='security':return tr('Security','Instrument')
    if page=='welcome':return tr('Start here','Découvrir')
    return t('nav.'+page)

def global_header(state):
    state.ui.page=page_from_query()
    apply_theme(state.ui.theme)
    with st.container(key='terminal-header'):
        brand,search,language,theme=st.columns([1.1,2,.4,.5])
        brand.markdown('<div class="desk-brand">MAT <span style="font-weight:400">/ V2</span></div>',unsafe_allow_html=True)
        search.selectbox(tr('Find a security','Chercher un instrument'),[s.id for s in DIRECTORY],index=None,
            format_func=lambda id:f'{id} · {SECURITIES[id].name}',placeholder=tr('Search name or ticker…','Nom ou symbole…'),
            key='security_search',on_change=_search,label_visibility='collapsed')
        lang=language.selectbox(t('language'),['en','fr'],index=['en','fr'].index(state.ui.language),format_func=str.upper,key='global_language',label_visibility='collapsed')
        mode=theme.selectbox(t('theme'),['dark','light'],index=['dark','light'].index(state.ui.theme),format_func=lambda x,lang=state.ui.language:t(x,lang),key='global_theme',label_visibility='collapsed')
        if (lang,mode)!=(state.ui.language,state.ui.theme):
            state.ui.language,state.ui.theme=lang,mode
            st.query_params['lang'],st.query_params['theme']=lang,mode
            st.rerun()
    st.session_state['desk_section']=family_for(state.ui.page)
    family_labels={'markets':tr('Markets','Marchés'),'derivatives':tr('Derivatives','Dérivés'),'analytics':tr('Analytics','Analyses'),'portfolio':tr('Portfolio / Risk','Portefeuille / Risque'),'world':tr('World','Monde'),'news':tr('News','Actualités'),'board':'Board'}
    st.segmented_control(tr('Explore','Explorer'),tuple(FAMILIES),format_func=family_labels.get,key='desk_section',on_change=_family_changed,required=True,label_visibility='collapsed')
    options=FAMILIES[family_for(state.ui.page)]
    st.session_state['workspace']=state.ui.page
    labels={p:page_label(p) for p in options}
    if len(options)>1:
        st.segmented_control(t('workspaces'),options,format_func=labels.get,key='workspace',on_change=_page_changed,required=True,label_visibility='collapsed')
    from components.market_ticker import render_ticker
    render_ticker()
    from components.board_storage import render_board_storage
    render_board_storage()

def footer():
    with st.expander(t('about')):
        st.caption(t('author'));st.caption(t('disclaimer'))
        st.link_button('GitHub','https://github.com/HugoAschenbrenner/market-analytics-terminal')
        st.link_button('LinkedIn','https://www.linkedin.com/in/hugo-aschenbrenner-pro')
