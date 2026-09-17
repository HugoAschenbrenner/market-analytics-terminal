"""Visible context and optional plain-language explanations, without calculations."""
import html
import streamlit as st
from core.i18n import t
from core.explanations import METRIC_HELP

PAGE_TERMS = {
    'overview':['nav','es','dv01','vega','worst_loss','liquidity','risk_contribution'],
    'markets':['dv01','cs01','forward','carry','roll','delta','foreign_rho'],
    'risk':['var','es','parametric_var','parametric_es','component_var','risk_contribution','hhi','effective_assets'],
    'derivatives':['option.price','implied.vol','delta','gamma','vega','theta','domestic_rho','vanna','volga','charm','residual','proxy_value','mc_error','autocall_probability','loss_probability','workshop.price','workshop.touch_probability','workshop.debit','workshop.max_loss'],
    'financing':['financing.cash','financing.cost','financing.margin','liquidity'],
}


def source_inventory(state):
    """Use the actual shared-state provenance, never infer freshness from retrieval."""
    rows=[]
    for currency,payload in state.market.curves.items():
        rows.append(dict(item=currency+' · '+t('curve',state.ui.language),source=payload['source'],provider=payload['provider'],as_of=payload['as_of'],use='curve'))
    for ticker in state.market.spots:
        payload=state.market.provenance.get(ticker,{})
        use='vix' if ticker=='VIX' else 'fx' if ticker in ('EURUSD','GBPUSD','USDJPY') else 'quote'
        rows.append(dict(item=ticker,source=payload.get('source','SYNTHETIC'),provider=payload.get('provider','demo'),as_of=payload.get('as_of','—'),use=use))
    return rows


def render_sources(state):
    st.write(t('guide.sources.summary'))
    st.caption(t('guide.sources.snapshot',stamp=state.market.as_of))
    cards=[]
    for row in source_inventory(state):
        label=t(row['source'])+' · '+row['provider']+' · '+row['as_of'].replace('T',' ')
        use=t('guide.source.used',use=t('guide.use.'+row['use']))
        cards.append('<div class="source-card"><strong>'+html.escape(row['item'])+'</strong><small>'+html.escape(label)+'</small><small>'+html.escape(use)+'</small></div>')
    st.markdown('<div class="source-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    st.write(t('guide.sources.assumptions'))
    st.caption(t('guide.sources.rates',rates=' · '.join(f'{k} {v:.2%}' for k,v in state.market.rates.items())))
    st.caption(t('guide.sources.fx',rates=' · '.join(f'{k} {v:.6g}' for k,v in state.market.fx.items())))
    st.caption(t('guide.sources.history'))


def render_workspace_guide(state):
    page=state.ui.page
    st.caption(t('guide.'+page+'.intro'))
    with st.expander(t('guide.open')):
        selected=st.selectbox(t('guide.topic'),['read','sources','changes','terms'],format_func=lambda x,lang=state.ui.language:t('guide.'+x,lang),key='guide_topic')
        if selected=='sources':render_sources(state)
        elif selected=='changes':
            for key in ['refresh','shared','local','stable']:st.write(t('guide.changes.'+key))
        elif selected=='terms':
            term=st.selectbox(t('guide.term'),PAGE_TERMS[page],format_func=lambda x,lang=state.ui.language:t(x,lang),key='guide_term_'+page)
            st.write(t('help.'+term));st.caption(t('guide.units'))
        else:
            st.write(t('guide.'+page+'.read'));st.caption(t('guide.units'))


def explain(key, **values):
    st.caption(t('explain.'+key,**values))


def option_context(row,state):
    source=state.market.provenance.get(row.underlying,{}).get('source','SYNTHETIC')
    explain('option_inputs',underlying=row.underlying,spot=float(row.spot),source=t(source),strike=float(row.strike),years=float(row.maturity),vol=float(row.volatility),rate=state.market.rates[row.currency])
