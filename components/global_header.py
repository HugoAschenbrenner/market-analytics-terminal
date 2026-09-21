import html
import streamlit as st
from core.i18n import t
from core.theme import apply_theme

PAGES = ("welcome", "overview", "equity-derivatives", "structured-products", "markets", "risk", "financing")
ALIASES = {"home":"overview", "cross-asset-dashboard":"overview", "fixed-income-risk":"markets", "portfolio-risk":"risk", "repo-sec-lending":"financing"}

def page_from_query():
    slug = st.query_params.get("page", "welcome")
    slug = ALIASES.get(slug, slug)
    return slug if slug in (*PAGES, "derivatives") else "welcome"

def navigate(page):
    """Button callback: update navigation before the header widget is rebuilt."""
    if page not in (*PAGES, "derivatives"):
        raise ValueError("Unknown workspace")
    st.session_state['workspace'] = page
    st.query_params['page'] = page

def global_header(state):
    state.ui.page = page_from_query()
    with st.container(key="terminal-header"):
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
        if state.ui.page == 'equity-derivatives':
            from services.lab import get_lab
            lab = get_lab()
            status.caption(f'{t(lab.source)} · {lab.as_of}')
        else:
            status.caption(t('welcome.status') if state.ui.page == 'welcome' else f'{t(state.market.source)} · {state.market.as_of}')
    apply_theme(state.ui.theme)
    if state.ui.page == 'derivatives':
        st.session_state['_legacy_derivatives_visible'] = True
    options = (*PAGES, "derivatives") if st.session_state.get('_legacy_derivatives_visible') else PAGES
    selected = st.segmented_control(t("workspaces"), options, default=state.ui.page,
                                    format_func=lambda p, lang=state.ui.language:t("nav."+p,lang), required=True,
                                    key="workspace", label_visibility="collapsed", width="stretch")
    if selected != state.ui.page:
        state.ui.page = selected
        st.query_params["page"] = selected
        st.rerun()
    if state.ui.page != 'welcome':
        st.markdown(f'<div class="workspace-title">{t("nav." + state.ui.page)}</div>',unsafe_allow_html=True)

def footer():
    with st.expander(t("about")):
        st.caption(t("author"))
        st.caption(t("disclaimer"))
        st.link_button("GitHub", "https://github.com/HugoAschenbrenner/market-analytics-terminal")
        st.link_button("LinkedIn", "https://www.linkedin.com/in/hugo-aschenbrenner-pro")
