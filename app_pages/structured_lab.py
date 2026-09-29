"""Dedicated structured workspace with independent and explicit shared-book modes."""
from components.structured_workspace import render_structured
import streamlit as st
from core.i18n import t
from components.lab_common import tr
from services.structured_lab import get_structured_lab


def render(state):
    st.title(t('nav.structured-products'))
    mode_labels = {'lab': tr('Independent laboratory', 'Laboratoire indépendant'),
                   'book': tr('Shared portfolio', 'Portefeuille partagé')}
    mode = st.segmented_control(
        tr('Contract workspace', 'Espace contrat'), ['lab', 'book'], default='lab',
        format_func=mode_labels.get, key='structured_mode',
    ) or 'lab'
    if mode == 'lab':
        lab = get_structured_lab(state.ui)
        st.caption(tr(
            'Independent inputs · fixed synthetic example dated 9 September 2026 · no market download required. '
            'Edits affect this laboratory only. Values are educational model estimates per 100 of notional.',
            'Paramètres indépendants · exemple synthétique fixe au 9 septembre 2026 · aucun téléchargement requis. '
            'Les modifications restent dans ce laboratoire. Valeurs théoriques pédagogiques pour 100 de nominal.',
        ))
        render_structured(lab, scope='independent')
    else:
        st.caption(tr('Explicit portfolio mode: applying terms changes the selected note in your shared book.',
                      'Mode portefeuille explicite : appliquer les termes modifie la note sélectionnée du portefeuille partagé.'))
        if state.book.positions.query("asset_class=='Structured'").empty:
            st.info(tr('No structured note in this book. Use the independent laboratory above, or add a note in Portfolio.',
                       'Aucune note structurée dans ce portefeuille. Utilisez le laboratoire indépendant ci-dessus ou ajoutez une note dans Portefeuille.'))
            return
        render_structured(state, scope='shared')
