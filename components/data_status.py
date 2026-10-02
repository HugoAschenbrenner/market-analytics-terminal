import html
import streamlit as st
from core.i18n import t
from core.formatting import number
from core.provenance import metadata, observation_status
from core.monitor_copy import tr

STATUS_LABELS = {
    'synthetic': ('Fixed synthetic example', 'Exemple synthétique fixe'),
    'user_input': ('User assumption', 'Hypothèse utilisateur'),
    'available': ('Public observation', 'Observation publique'),
    'unverified': ('Freshness unverified', 'Fraîcheur non vérifiée'),
    'old': ('Old observation', 'Observation ancienne'),
    'stale': ('Last success · refresh failed', 'Dernier succès · actualisation échouée'),
    'unavailable': ('Unavailable', 'Indisponible'),
}


def provenance_text(payload):
    info=metadata(payload)
    status=tr(*STATUS_LABELS.get(observation_status(payload), ('Unverified', 'Non vérifié')))
    return f'{t(info["source"])} · {info["provider"]} · {info["observed_at"]} · {info["frequency"]} · {status}'


def data_status(payload):
    st.caption(provenance_text(payload))
    info=metadata(payload)
    if info['source']=='PUBLIC':
        st.caption(tr('Successful retrieval: ', 'Récupération réussie : ')+(info['retrieved_at'] or '—')+' · '+
                   tr('Context cache: up to 15 min; manual refresh available.', 'Cache du contexte : jusqu’à 15 min ; actualisation manuelle disponible.'))

def market_strip(state):
    observations=[]
    for key in ['SPY','VIX','EURUSD']:
        p=state.market.provenance[key]
        observations.append((key,number(p['price'],2),p))
    us=state.market.curves['USD']; eur=state.market.curves['EUR']
    for label,val,payload in [('US 2Y',us['history'].iloc[-1][2],us),('US 10Y',us['history'].iloc[-1][10],us),('2s10s',(us['history'].iloc[-1][10]-us['history'].iloc[-1][2])*100,us),('EUR 10Y',eur['history'].iloc[-1][10],eur)]:
        observations.append((label,number(val,1 if label=='2s10s' else 2)+(' bp' if label=='2s10s' else '%'),payload))
    items=[]
    for label,value,payload in observations:
        stamp=t(payload['source'])+' · '+payload['as_of'][:10]+' · '+tr(*STATUS_LABELS.get(observation_status(payload), ('Unverified','Non vérifié')))
        detail=provenance_text(payload)
        delta=payload.get('change') if label in ['SPY','VIX','EURUSD'] else None
        change=f' {delta:+.2%}' if delta is not None else ''
        items.append(f'<div class="market-tile"><span>{html.escape(label)}</span><b>{html.escape(value+change)}</b><small title="{html.escape(detail,quote=True)}">{html.escape(stamp)}</small></div>')
    st.markdown('<div class="market-scroll-hint">'+html.escape(t('market.scroll'))+'</div><div class="market-strip" tabindex="0" role="region" aria-label="'+html.escape(t('status'))+'">'+''.join(items)+'</div>',unsafe_allow_html=True)
