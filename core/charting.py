import streamlit as st
from core.theme import TOKENS
from core.state import get_state

def style_figure(fig, theme="dark", height=290):
    c = TOKENS[theme]
    fig.update_layout(template="plotly_dark" if theme == "dark" else "plotly_white", height=height,
                      margin=dict(l=12,r=12,t=35,b=20), paper_bgcolor=c["chart_background"], plot_bgcolor=c["chart_background"],
                      font=dict(color=c["text_primary"], family="Inter, Arial, sans-serif", size=11),
                      colorway=[c["accent"],c["positive"],c["warning"],c["negative"],"#9b8bed"],
                      hoverlabel=dict(bgcolor=c["surface"],font_color=c["text_primary"]),
                      legend=dict(orientation="h", y=-.15))
    fig.update_xaxes(gridcolor=c["grid"], zerolinecolor=c["border"])
    fig.update_yaxes(gridcolor=c["grid"], zerolinecolor=c["border"])
    return fig

def chart(fig, key=None, height=290):
    from core.i18n import t
    from core.models import ASSET_CLASSES
    for trace in fig.data:
        if trace.name in ASSET_CLASSES:trace.name=t(trace.name)
    st.plotly_chart(style_figure(fig, get_state().ui.theme, height), width="stretch", key=key, theme=None,
                    config={"displayModeBar":False})
