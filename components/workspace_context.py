"""Compact, consistently ordered valuation context, without recalculations."""
import streamlit as st
from components.lab_common import tr


def context(subject, valuation_date, currency, source, assumptions):
    with st.container(key='valuation-context'):
        st.caption(f'{subject} · {valuation_date} · {currency} · {source}')
        st.caption(assumptions)


def book_context(state):
    mode=getattr(state.market,'mode','mixed')
    context(f'{state.book.name} · {len(state.book.positions)} '+tr('positions','positions'),
            str(state.valuation_date),state.book.base_currency,state.market.source,
            tr('Saved market assumptions · public refresh is explicit.', 'Hypothèses de marché sauvegardées · actualisation publique explicite.') if mode=='saved' else
            tr('Shared book · model assumptions and dated public observations are detailed in the source guide.',
               'Portefeuille partagé · hypothèses de modèle et observations publiques datées détaillées dans le guide des sources.'))
