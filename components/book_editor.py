import pandas as pd
import streamlit as st
from core.state import DEMO_BOOKS, demo_book, replace_book, change_base_currency
from core.i18n import t, error_message
from core.models import ASSET_CLASSES, CURRENCIES

def book_selector(state):
    a,b,c = st.columns([3,1,2])
    selection = a.selectbox(t("book.selector"), DEMO_BOOKS, index=DEMO_BOOKS.index(state.book.name), format_func=lambda x, lang=state.ui.language:t("book."+x,lang), key="demo_selector",label_visibility="collapsed")
    if selection != state.book.name:
        state.book = demo_book(selection)
        state.risk.results.clear()
        st.rerun()
    base = b.selectbox(t("base_currency"), CURRENCIES, index=CURRENCIES.index(state.book.base_currency), key="base_currency",label_visibility="collapsed")
    if base != state.book.base_currency:
        change_base_currency(state, base)
    c.caption(f'{t(state.book.source)} · {len(state.book.positions)} · {t("book."+state.book.name)}')

def book_editor(state):
    st.caption(t("book.note"))
    with st.expander(t("book.edit"), expanded=True):
        display=state.book.positions.copy()
        mappings={'asset_class':{x:t(x) for x in ASSET_CLASSES},'mark_mode':{x:t(x) for x in ['Book','Market']}}
        for col,mapping in mappings.items():display[col]=display[col].map(mapping)
        frame = st.data_editor(display, num_rows="dynamic", width="stretch", height=340,
            column_config={**{key:t("field."+key) for key in display.columns},"mark_mode":st.column_config.SelectboxColumn(t("field.mark_mode"),options=list(mappings["mark_mode"].values())),"asset_class":st.column_config.SelectboxColumn(t("asset_class"), options=list(mappings["asset_class"].values())),
                           "currency":st.column_config.SelectboxColumn(t("currency"), options=CURRENCIES)},
            key=f"book_editor_{state.book.revision}_{state.book.name}")
        for col,mapping in mappings.items():frame[col]=frame[col].map({v:k for k,v in mapping.items()})
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
