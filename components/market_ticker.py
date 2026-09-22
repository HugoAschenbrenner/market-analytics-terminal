from pathlib import Path
import streamlit as st
import streamlit.components.v2 as components
from core.securities import SECURITIES,TICKER_IDS
from core.market_formatting import level,move
from core.v2_theme import TOKENS
from core.monitor_copy import tr
from services.market_monitor import get_market_service

@st.fragment(run_every=300)
def render_ticker():
    from components.global_header import open_security
    data=get_market_service().quotes(TICKER_IDS)
    items=[]
    for id,result in data.items():
        s=SECURITIES[id];q=result.value
        status=tr('unavailable','indisponible') if q is None else f'{q.source} · {q.frequency} · {q.observed_at:%Y-%m-%d %H:%M} UTC · {result.status}'
        items.append(dict(id=id,name=s.name,level=level(s,q.price if q else None),move=move(s,q),sign='positive' if q and q.change is not None and q.change>0 else 'negative' if q and q.change is not None and q.change<0 else '',detail=f'{s.name} · {status}'))
    st.caption(tr('Delayed / indicative · ticker refreshes every 5 min · pages refresh on interaction','Différé / indicatif · ticker actualisé toutes les 5 min · pages actualisées lors des interactions'))
    path=Path(__file__).with_name('monitor')
    comp=components.component('mat_market_ticker',html='<div class="ticker" aria-label="Market ticker"></div>',css=(path/'ticker.css').read_text(),js=(path/'ticker.mjs').read_text())
    result=comp(key='market_ticker',height='content',data={'items':items,'tokens':TOKENS[st.session_state.terminal.ui.theme]},on_clicked_change=lambda:None)
    if result.clicked in SECURITIES:
        open_security(result.clicked);st.rerun(scope='app')
