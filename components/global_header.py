import html
import streamlit as st
from core.i18n import t
from core.theme import apply_theme

PAGES = ("overview", "markets", "risk", "derivatives", "financing")
ALIASES = {"home":"overview", "cross-asset-dashboard":"overview", "fixed-income-risk":"markets", "portfolio-risk":"risk", "structured-products":"derivatives", "repo-sec-lending":"financing"}

def global_header(state):
    brand, language, theme, status = st.columns([4,1,1,2])
    with brand:
        st.markdown(f'<div class="desk-brand">{t("brand")}</div>', unsafe_allow_html=True)
        st.caption(t("subtitle"))
    lang = language.selectbox(t("language"), ["en","fr"], index=["en","fr"].index(state.ui.language), format_func=str.upper, key="global_language", label_visibility="collapsed")
    mode = theme.selectbox(t("theme"), ["dark","light"], index=["dark","light"].index(state.ui.theme), format_func=lambda x, lang=state.ui.language:t(x,lang), key="global_theme", label_visibility="collapsed")
    if (lang, mode) != (state.ui.language, state.ui.theme):
        state.ui.language, state.ui.theme = lang, mode
        st.query_params["lang"], st.query_params["theme"] = lang, mode
        st.rerun()
    status.caption(f'{t(state.market.source)} · {state.market.as_of}')
    apply_theme(state.ui.theme)
    slug = st.query_params.get("page", "overview")
    slug = ALIASES.get(slug, slug)
    state.ui.page = slug if slug in PAGES else "overview"
    selected = st.segmented_control(t("workspaces"), PAGES, default=state.ui.page,
                                    format_func=lambda p, lang=state.ui.language:t("nav."+p,lang), required=True,
                                    key="workspace", label_visibility="collapsed", width="stretch")
    if selected != state.ui.page:
        state.ui.page = selected
        st.query_params["page"] = selected
        st.rerun()
    st.markdown(f'<div class="workspace-title">{t("nav." + state.ui.page)}</div>',unsafe_allow_html=True)

def footer():
    with st.expander(t("about")):
        st.caption(t("author"))
        st.caption(t("disclaimer"))
        st.link_button("GitHub", "https://github.com/HugoAschenbrenner/market-analytics-terminal")
        st.link_button("LinkedIn", "https://www.linkedin.com/in/hugo-aschenbrenner-pro")
