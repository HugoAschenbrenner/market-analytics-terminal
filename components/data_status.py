import streamlit as st
from core.i18n import t
from core.formatting import number

def data_status(payload):
    st.caption(f'{t(payload["source"])} · {payload["provider"]} · {payload["as_of"]}')

def market_strip(state):
    observations=[]
    for key in ['SPY','VIX','EURUSD']:
        p=state.market.provenance[key]
        observations.append((key,number(p['price'],2),p))
    us=state.market.curves['USD']; eur=state.market.curves['EUR']
    for label,val,payload in [('US 2Y',us['history'].iloc[-1][2],us),('US 10Y',us['history'].iloc[-1][10],us),('2s10s',(us['history'].iloc[-1][10]-us['history'].iloc[-1][2])*100,us),('EUR 10Y',eur['history'].iloc[-1][10],eur)]:
        observations.append((label,number(val,1 if label=='2s10s' else 2)+(' bp' if label=='2s10s' else '%'),payload))
    for col,(label,value,payload) in zip(st.columns(len(observations)),observations):
        col.metric(label,value)
        col.caption(f'{t(payload["source"])} · {payload["as_of"][:10]}')
