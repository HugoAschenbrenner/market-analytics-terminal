"""A light introductory menu that preserves the current shared portfolio."""
import html
import streamlit as st
from core.i18n import t
from components.global_header import navigate

WORKSPACES = ('overview', 'markets', 'risk', 'derivatives', 'financing')


def copy(key, **values):
    return html.escape(t(key, **values))


def render(state):
    with st.container(key='welcome-hero'):
        intro, route = st.columns([1.65, 1], gap='large')
        with intro:
            st.markdown(
                f'<div class="welcome-kicker">{copy("welcome.kicker")}</div>'
                f'<h1 class="welcome-title">{copy("welcome.title")}</h1>'
                f'<p class="welcome-lede">{copy("welcome.intro")}</p>',
                unsafe_allow_html=True,
            )
            st.button(t('welcome.start'), key='welcome-start', type='primary',
                      on_click=navigate, args=('overview',))
            st.caption(t('welcome.ready') if state.book.source == 'SYNTHETIC' else t('welcome.keep'))
        with route:
            steps = ''.join(
                f'<li><strong>{copy(f"welcome.step{i}.title")}</strong>'
                f'<p>{copy(f"welcome.step{i}.body")}</p></li>'
                for i in range(1, 4)
            )
            st.markdown(
                f'<div class="welcome-route"><h2>{copy("welcome.route")}</h2>'
                f'<ol>{steps}</ol></div>', unsafe_allow_html=True,
            )

    st.markdown(
        f'<div class="welcome-current"><span>{copy("welcome.current")}</span>'
        f'<strong>{copy("book." + state.book.name)}</strong>'
        f'<span>{copy("welcome.positions", count=len(state.book.positions), currency=state.book.base_currency)}</span>'
        f'<span>{copy(state.book.source)}</span></div>', unsafe_allow_html=True,
    )
    st.caption(t('welcome.keep'))
    st.header(t('welcome.menu'))
    st.caption(t('welcome.menu_hint'))
    with st.container(key='welcome-menu'):
        columns = st.columns(len(WORKSPACES))
        for index, (column, page) in enumerate(zip(columns, WORKSPACES), 1):
            with column, st.container(key='welcome-card-' + page, height='stretch'):
                st.markdown(
                    f'<span class="welcome-number">0{index}</span>'
                    f'<h3>{copy("welcome." + page + ".title")}</h3>'
                    f'<p class="welcome-question">{copy("welcome." + page + ".question")}</p>'
                    f'<p class="welcome-card-copy">{copy("welcome." + page + ".body")}</p>',
                    unsafe_allow_html=True,
                )
                st.button(t('welcome.' + page + '.open'), key='welcome-open-' + page,
                          width='stretch', on_click=navigate, args=(page,))

    st.header(t('welcome.faq'))
    for topic in ('data', 'book', 'controls', 'metrics'):
        with st.expander(t('welcome.faq.' + topic + '.title')):
            st.write(t('welcome.faq.' + topic + '.body'))
