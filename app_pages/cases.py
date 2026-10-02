"""Download and explicitly restore a complete validated analytical case."""
import streamlit as st
from core.board import board_ids
from core.monitor_copy import tr
from services.lab import get_lab
from services.cases import export_case, import_case, apply_case, VIEW_KEYS, MAX_BYTES


def _prepare():
    try:
        st.session_state['case_download']=export_case(
            st.session_state.terminal, get_lab(), st.session_state.get('structured_lab'), board_ids(),
            {k:st.session_state[k] for k in VIEW_KEYS if k in st.session_state}, st.session_state.get('interactive_case'))
        st.session_state.pop('case_error',None)
    except (ValueError,TypeError) as exc:
        st.session_state.pop('case_download',None);st.session_state['case_error']=str(exc)


def _inspect():
    st.session_state.pop('case_pending',None);st.session_state.pop('case_error',None)
    file=st.session_state.get('case_upload')
    if file is None:return
    try:
        if file.size>MAX_BYTES:raise ValueError('Maximum 5 MB.')
        raw=file.getvalue();candidate=import_case(raw)
        st.session_state.case_pending=raw
        st.session_state.case_preview=dict(positions=len(candidate.terminal.book.positions),date=str(candidate.terminal.valuation_date),
                                           currency=candidate.terminal.book.base_currency,created=candidate.created_at)
    except (ValueError,TypeError) as exc:st.session_state.case_error=str(exc)


def _restore():
    raw=st.session_state.get('case_pending')
    if raw is None:return
    try:apply_case(raw,st.session_state,st.query_params)
    except (ValueError,TypeError) as exc:st.session_state.case_error=str(exc)


def render(state):
    st.title(tr('Saved analytical cases','Cas analytiques sauvegardés'))
    st.caption(tr('Save the shared portfolio, independent laboratories, market assumptions, scenarios, risk snapshot, curves, Board and display preferences in one versioned JSON file.',
                  'Sauvegardez portefeuille partagé, laboratoires indépendants, hypothèses de marché, scénarios, instantané de risque, courbes, Board et préférences dans un fichier JSON versionné.'))
    if st.session_state.get('case_restored'):
        st.success(tr('Case restored. Market assumptions remain the saved snapshot until you explicitly refresh them. Current book risk is recalculated; saved attribution tables retain their source.',
                      'Cas restauré. Les hypothèses de marché restent celles du fichier jusqu’à une actualisation explicite. Le risque du portefeuille est recalculé ; les tables d’attribution sauvegardées conservent leur source.'))
    a,b=st.columns(2)
    with a:
        st.subheader(tr('Save current work','Sauvegarder le travail courant'))
        st.write(tr('Apply any pending form edits first. In Interactive Greeks, use “Include in saved case” to capture the browser inputs explicitly; moving sliders stays local and instant.',
                    'Appliquez d’abord les formulaires en cours. Dans Greeks interactifs, utilisez « Inclure dans le cas » pour capturer les paramètres du navigateur ; les curseurs restent locaux et instantanés.'))
        st.button(tr('Prepare case file','Préparer le fichier de cas'),key='case_prepare',on_click=_prepare)
        if 'case_download' in st.session_state:
            st.download_button(tr('Download analytical case','Télécharger le cas analytique'),st.session_state.case_download,'MAT_case_v1.json','application/json',key='case_save')
        st.caption(tr('Keep this file private if you enter non-public positions. Files are downloaded to your device; this feature does not publish or share them.',
                      'Gardez ce fichier privé si vous saisissez des positions confidentielles. Il est téléchargé sur votre appareil ; cette fonction ne le publie ni ne le partage.'))
    with b:
        st.subheader(tr('Restore a case','Restaurer un cas'))
        st.file_uploader(tr('Analytical case JSON · up to 5 MB','Cas analytique JSON · 5 Mo maximum'),type=['json'],key='case_upload',on_change=_inspect)
        if st.session_state.get('case_pending'):
            p=st.session_state.case_preview
            st.write(f"{p['positions']} positions · {p['currency']} · {p['date']}")
            st.caption(tr('Saved: ','Sauvegardé : ')+p['created'])
            st.warning(tr('Restore replaces the current case, including both laboratories and preferences. Download your current case first if you want to keep it.',
                          'La restauration remplace le cas courant, laboratoires et préférences compris. Téléchargez d’abord votre cas courant si vous souhaitez le conserver.'))
            st.button(tr('Restore validated case','Restaurer le cas validé'),key='case_restore',type='primary',on_click=_restore)
    if st.session_state.get('case_error'):st.error(tr('Case rejected; current inputs are unchanged. ','Cas refusé ; les paramètres courants sont inchangés. ')+st.session_state.case_error)
    from components.global_header import navigate
    st.divider()
    for col,page,label in zip(st.columns(4),('overview','equity-derivatives','structured-products','board'),
                              (tr('Portfolio','Portefeuille'),'Equity Derivatives',tr('Structured Products','Produits structurés'),'Board')):
        col.button(label,key='case_go_'+page,on_click=navigate,args=(page,),width='stretch')
