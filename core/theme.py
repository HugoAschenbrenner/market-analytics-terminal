import streamlit as st

TOKENS = {
    "dark": dict(background="#09111c", surface="#111d2c", surface_secondary="#18283b", border="#2b4056", text_primary="#e7eef7", text_secondary="#9aaec5", positive="#38c6a3", negative="#ff6b7b", warning="#eabc63", accent="#58b8ed", grid="#23364b", chart_background="#111d2c"),
    "light": dict(background="#f1f4f8", surface="#ffffff", surface_secondary="#e7eef6", border="#c7d2df", text_primary="#16293f", text_secondary="#506580", positive="#087e62", negative="#be3046", warning="#a66a00", accent="#0067a6", grid="#e0e7ef", chart_background="#ffffff"),
}

def apply_theme(theme):
    c = TOKENS[theme]
    variables = ";".join(f"--{key.replace('_', '-')}: {value}" for key, value in c.items())
    st.markdown(f"""<style>
    :root {{{variables}}}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{background:var(--background); color:var(--text-primary)}}
    [data-testid="stHeader"] {{display:none}}
    .block-container {{padding:1.1rem 1.8rem 2rem; max-width:1600px}}
    h1,h2,h3,p,label,[data-testid="stWidgetLabel"], [data-testid="stMetricValue"] {{color:var(--text-primary)!important}}
    h1 {{font-size:1.65rem!important; letter-spacing:-.03em}} h2 {{font-size:1.2rem!important}} h3 {{font-size:1rem!important}}
    [data-testid="stMetric"] {{background:var(--surface); border-top:2px solid var(--accent); padding:.6rem .8rem}}
    [data-testid="stMetricValue"] {{font-size:1.6rem}} [data-testid="stMetricLabel"] {{color:var(--text-secondary)}}
    [data-testid="stCaptionContainer"] p {{color:var(--text-secondary)!important; font-size:.76rem}}
    [data-baseweb="select"] > div, [data-baseweb="input"], [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] button, .stButton button,
    .stDownloadButton button, [data-baseweb="popover"] {{background:var(--surface)!important; color:var(--text-primary)!important; border-color:var(--border)!important; border-radius:3px!important}}
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {{border-color:var(--border)!important}}
    [data-baseweb="tab-list"] {{gap:1.2rem}} [data-baseweb="tab"] {{color:var(--text-secondary)!important}}
    [aria-selected="true"] {{color:var(--accent)!important}}
    .desk-brand {{font-size:.8rem; font-weight:700; letter-spacing:.13em; color:var(--accent)}}
    .desk-nav {{display:flex; gap:1.5rem; border-bottom:1px solid var(--border); padding:.3rem 0 .7rem; margin-bottom:1rem}}
    .desk-nav a {{color:var(--text-secondary);text-decoration:none;font-size:.88rem}}
    .desk-nav a.active {{color:var(--accent);font-weight:700}}
    .risk-line {{border-left:2px solid var(--warning); padding:.3rem .8rem; margin:.4rem 0; background:var(--surface)}}
    @media(max-width:700px) {{[data-testid="stHeader"] {{display:none}}
    .block-container {{padding:1rem}} .desk-nav {{gap:.8rem;flex-wrap:wrap}}}}
    </style>""", unsafe_allow_html=True)
