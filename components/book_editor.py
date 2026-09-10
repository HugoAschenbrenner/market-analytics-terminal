import pandas as pd
import streamlit as st
from core.state import DEMO_BOOKS, demo_book, replace_book
from core.i18n import t, error_message
from core.models import ASSET_CLASSES, CURRENCIES

def book_selector(state):
    a,b = st.columns([3,1])
    selection = a.selectbox(t("book.selector"), DEMO_BOOKS, index=DEMO_BOOKS.index(state.book.name), format_func=lambda x, lang=state.ui.language:t("book."+x,lang), key="demo_selector")
    if selection != state.book.name:
        state.book = demo_book(selection)
        state.risk.results.clear()
        st.rerun()
    base = b.selectbox(t("base_currency"), CURRENCIES, index=CURRENCIES.index(state.book.base_currency), key="base_currency")
    if base != state.book.base_currency:
        state.book.base_currency = base
        state.book.revision += 1
        state.risk.results.clear()
    st.caption(f'{t(state.book.source)} · {len(state.book.positions)} · {t("book."+state.book.name)}')

def book_editor(state):
    st.caption(t("book.note"))
    with st.expander(t("book.edit"), expanded=True):
        frame = st.data_editor(state.book.positions, num_rows="dynamic", width="stretch", height=340,
            column_config={"asset_class":st.column_config.SelectboxColumn(t("asset_class"), options=ASSET_CLASSES),
                           "currency":st.column_config.SelectboxColumn(t("currency"), options=CURRENCIES)},
            key=f"book_editor_{state.book.revision}_{state.book.name}")
        if st.button(t("book.apply")):
            try:
                from services.analytics import marked_positions
                from copy import deepcopy
                candidate = deepcopy(state)
                replace_book(candidate, frame)
                marked_positions(candidate)
                replace_book(state, frame)
                st.rerun()
            except (ValueError,KeyError,TypeError) as exc:
                st.error(error_message(exc))
    with st.expander(t("book.load")):
        upload = st.file_uploader(t("book.csv"), type="csv")
        if upload is not None and st.button(t("book.apply"), key="apply_csv"):
            try:
                from services.analytics import marked_positions
                from copy import deepcopy
                frame = pd.read_csv(upload)
                candidate = deepcopy(state)
                replace_book(candidate, frame)
                marked_positions(candidate)
                replace_book(state, frame)
                st.rerun()
            except (ValueError,KeyError,TypeError,UnicodeError) as exc:
                st.error(error_message(exc))
        st.download_button(t("book.template"), state.book.positions.to_csv(index=False), "positions.csv", "text/csv")
