"""Reusable market rows, provenance and sessions; no provider calls in formatting."""
import html
from pathlib import Path
import streamlit.components.v2 as components
from core.v2_theme import TOKENS
import streamlit as st
from core.securities import SECURITIES
from core.market_formatting import level,move
from core.market_sessions import SESSIONS,session_state
from core.monitor_copy import tr
from services.market_monitor import get_market_service,observation_is_old


def status_text(result,security):
    q=result.value
    if not q:return tr('Unavailable · no substitute price','Indisponible · aucun prix de substitution')
    status=tr('Last success · refresh failed','Dernier succès · actualisation échouée') if result.status=='stale' else tr('Old observation','Observation ancienne') if observation_is_old(security,q) else tr('Delayed / indicative','Différé / indicatif')
    if security.unit=='yield':
        frequency=tr('Monthly average','Moyenne mensuelle') if security.id=='DE10Y' else tr('Daily published yield','Taux quotidien publié')
        return f'{frequency} · {q.observed_at:%Y-%m-%d}'+(' · '+status if result.status=='stale' or observation_is_old(security,q) else '')
    return f'{status} · {q.observed_at:%Y-%m-%d %H:%M} UTC'


def quote_table(ids,key):
    from components.global_header import open_security
    service=get_market_service();quotes=service.quotes(ids)
    rows=[]
    for id,result in quotes.items():
        s=SECURITIES[id];q=result.value
        rows.append({tr('Instrument','Instrument'):f'{id} · {s.name}',tr('Level','Niveau'):level(s,q.price if q else None),tr('Move','Variation'):move(s,q),tr('Recent path','Évolution récente'):None,tr('Unit','Unité'):'%' if s.unit=='yield' else s.name if s.unit=='fx' else s.unit if s.asset_class=='Commodities' else s.currency if s.unit in ('price','crypto') else 'points',tr('Observation / status','Observation / statut'):status_text(result,s)})
    if not rows:
        st.info(tr('No instruments selected.','Aucun instrument sélectionné.'));return quotes
    path=Path(__file__).with_name('monitor')
    component=components.component('mat_market_table',html='<div class="market-table"></div>',css=(path/'table.css').read_text(),js=(path/'table.mjs').read_text())
    rendered=[]
    for (id,result),row in zip(quotes.items(),rows):
        change=result.value.change if result.value else None
        history=service.raw_chart(id)
        spark=history.value[0].close.tail(30).dropna().astype(float).tolist() if history.value else []
        rendered.append(dict(id=id,cells=list(row.values()),spark=spark,sign='positive' if change is not None and change>0 else 'negative' if change is not None and change<0 else ''))
    event=component(key=key,height='content',data={'headers':list(rows[0]),'rows':rendered,'sparkLabel':tr('Last 30 available observations; independent scale','30 dernières observations disponibles ; échelle indépendante'),'tokens':TOKENS[st.session_state.terminal.ui.theme]},on_selected_change=lambda:None)
    if event.selected in quotes:
        open_security(event.selected);st.rerun()
    st.caption(tr('Select a row to open its security page. Moves compare with the previous observation; yields use basis points.','Sélectionnez une ligne pour ouvrir sa fiche. La variation compare les deux dernières observations ; les taux sont en points de base.'))
    return quotes


@st.fragment(run_every=60)
def sessions():
    cards=[]
    for session in SESSIONS:
        data=session_state(session);hours=' / '.join(f'{a:%H:%M}–{b:%H:%M}' for a,b in data['periods']) or tr('No regular session today','Pas de séance régulière aujourd’hui')
        state=tr('Scheduled open','Ouverture prévue') if data['scheduled_open'] else tr('Outside regular session','Hors séance régulière')
        action=tr('close','clôture') if data['scheduled_open'] else tr('open','ouverture')
        cards.append(f'<div class="session-item"><b>{html.escape(session.city)} · {data["local"]:%H:%M}</b>{state}<br><small>{hours}<br>{action} ≈ {data["minutes"]//60}h {data["minutes"]%60:02d}m</small></div>')
    st.markdown('<div class="session-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    st.caption(tr('Regular cash-market schedules in local time, including DST and lunch breaks. NYSE holidays/early closes verified for 2026–2028. Other holidays, auctions and exceptional closures are unverified; states are scheduled, not live exchange status.','Horaires locaux des marchés au comptant, avec changements d’heure et pauses. Jours fériés/clôtures anticipées NYSE vérifiés pour 2026–2028. Autres jours fériés, enchères et fermetures exceptionnelles non vérifiés : état prévu, pas temps réel.'))


def provenance(result,security):
    if not result.value:
        st.info(status_text(result,security));return
    q=result.value
    st.caption(f'{q.source} · {q.frequency} · {status_text(result,security)}')
    if result.retrieved_at:
        st.caption(tr('Retrieved','Récupéré')+f' {result.retrieved_at:%Y-%m-%d %H:%M} UTC · '+tr('Cache: 5 min for prices, 1 h for yields. No synthetic fallback.','Cache : 5 min pour les prix, 1 h pour les taux. Aucun repli synthétique.'))


def security_session(security,quote):
    from datetime import datetime,timezone
    from zoneinfo import ZoneInfo
    now=datetime.now(timezone.utc)
    if security.unit=='yield':
        return tr('Published yield observation · no intraday trading session','Observation de rendement publiée · pas de séance de négociation intrajournalière')
    if security.asset_class=='Crypto':return tr('Continuous 24/7 market · provider quotes may lag','Marché continu 24/7 · cotations du fournisseur potentiellement retardées')
    if security.asset_class=='FX':
        local=now.astimezone(ZoneInfo('America/New_York'))
        opened=local.weekday()<4 or local.weekday()==4 and local.hour<17 or local.weekday()==6 and local.hour>=17
        return tr('Indicative OTC FX schedule: ','Horaire indicatif du FX OTC : ')+(tr('open','ouvert') if opened else tr('weekend closure','fermeture du week-end'))
    schedule=quote.session if quote else {}
    try:
        start=datetime.fromtimestamp(schedule['start'],timezone.utc);end=datetime.fromtimestamp(schedule['end'],timezone.utc)
        if start.astimezone(ZoneInfo(security.timezone)).date()==now.astimezone(ZoneInfo(security.timezone)).date():
            return tr('Provider regular session: ','Séance régulière selon le fournisseur : ')+(tr('open','ouverte') if start<=now<end else tr('closed','fermée'))
    except (KeyError,TypeError,ValueError,OverflowError):pass
    return tr('Exchange session not verified · see global schedules','Séance de l’instrument non vérifiée · voir les horaires mondiaux')
