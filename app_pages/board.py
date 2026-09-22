import json
import streamlit as st
from core.board import board_ids,set_board,add_to_board,remove_from_board,reorder_board
from core.securities import SECURITIES
from core.monitor_copy import tr
from components.market_ui import quote_table,sessions
from components.market_context import news_panel,events_panel
from components.global_header import navigate

def _add():
    id=st.session_state.get('board_add')
    if id:add_to_board(id)
    st.session_state.board_add=None

def _import():
    file=st.session_state.get('board_import')
    if not file:return
    try:
        if file.size>10000:raise ValueError('File too large')
        set_board(json.loads(file.getvalue()))
        st.session_state.board_import_message='ok'
    except (ValueError,TypeError,UnicodeError):st.session_state.board_import_message='invalid'

def render(state):
    st.subheader(tr('Your Board','Votre Board'))
    st.caption(tr('Your personal monitoring list. Instruments only are stored in this browser; the portfolio and lab inputs stay separate.','Votre liste de suivi. Seuls les instruments sont sauvegardés dans ce navigateur ; portefeuille et paramètres des labos restent séparés.'))
    if st.session_state.get('board_storage_error'):st.warning(tr('Browser storage unavailable. Download your configuration to keep it.','Stockage du navigateur indisponible. Téléchargez la configuration pour la conserver.'))
    ids=board_ids()
    labels={id:f'{id} · {s.name}' for id,s in SECURITIES.items()}
    st.selectbox(tr('Add a security','Ajouter un instrument'),[id for id in SECURITIES if id not in ids],index=None,format_func=labels.get,key='board_add',on_change=_add,disabled=len(ids)>=30)
    view=st.segmented_control(tr('Board view','Vue du Board'),('quotes','news','events','sessions','portfolio'),default='quotes',format_func={'quotes':tr('Watchlist','Liste de suivi'),'news':tr('News','Actualités'),'events':tr('Events','Événements'),'sessions':tr('Sessions','Séances'),'portfolio':tr('Portfolio shortcuts','Accès portefeuille')}.get,required=True,key='board_view')
    if view=='quotes':quote_table(ids,'board_quotes')
    elif view=='news':
        selection=st.multiselect(tr('News instruments · up to 12','Instruments des actualités · 12 maximum'),ids,default=ids[:12],max_selections=12,format_func=labels.get,key='board_news_ids')
        news_panel(selection,'board',limit=12)
    elif view=='events':
        selected=st.selectbox(tr('Events for','Événements pour'),ids,index=0 if ids else None,format_func=labels.get,key='board_event_id')
        events_panel(selected)
    elif view=='sessions':sessions()
    else:
        st.write(tr('Current book','Portefeuille courant')+f': {state.book.name} · {len(state.book.positions)} '+tr('positions','positions'))
        st.caption(tr('Opening these workspaces uses your existing book and its labelled market assumptions. Board prices do not silently re-mark positions.','Ces espaces utilisent votre portefeuille et ses hypothèses de marché identifiées. Les prix du Board ne revalorisent pas silencieusement les positions.'))
        for page,label in [('overview',tr('Book overview','Vue portefeuille')),('risk',tr('Risk Lab','Labo risque')),('financing',tr('Repo / lending','Repo / prêt de titres'))]:st.button(label,key='board_go_'+page,on_click=navigate,args=(page,))
    with st.expander(tr('Manage order & configuration','Ordre et configuration')):
        chosen=st.selectbox(tr('Selected instrument','Instrument sélectionné'),ids,index=0 if ids else None,format_func=labels.get,key='board_manage')
        a,b,c=st.columns(3)
        a.button('↑ '+tr('Move up','Monter'),disabled=not chosen or ids.index(chosen)==0,key='board_up',on_click=reorder_board,args=(chosen,-1))
        b.button('↓ '+tr('Move down','Descendre'),disabled=not chosen or ids.index(chosen)==len(ids)-1,key='board_down',on_click=reorder_board,args=(chosen,1))
        c.button(tr('Remove','Retirer'),disabled=not chosen,key='board_remove',on_click=remove_from_board,args=(chosen,))
        st.download_button(tr('Download configuration','Télécharger la configuration'),json.dumps(ids,indent=2),file_name='mat-board.json',mime='application/json')
        st.file_uploader(tr('Restore configuration (.json)','Restaurer la configuration (.json)'),type=['json'],key='board_import',on_change=_import)
        if st.session_state.get('board_import_message')=='invalid':st.warning(tr('Invalid configuration: expected at most 30 supported instrument IDs.','Configuration invalide : 30 identifiants d’instruments supportés au maximum.'))
