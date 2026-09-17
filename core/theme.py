"""Shared accessible surfaces and responsive layout for the custom UI theme."""
import streamlit as st

TOKENS = {
    "dark": dict(background="#09111c", surface="#111d2c", surface_secondary="#18283b", border="#38516b", text_primary="#e7eef7", text_secondary="#a7bad0", positive="#38c6a3", negative="#ff7b89", warning="#eabc63", accent="#65c0f3", grid="#23364b", chart_background="#111d2c", violet="#b5a0ff"),
    "light": dict(background="#f1f4f8", surface="#ffffff", surface_secondary="#e7eef6", border="#bbc9d9", text_primary="#16293f", text_secondary="#506580", positive="#067359", negative="#be3046", warning="#925c00", accent="#0067a6", grid="#e0e7ef", chart_background="#ffffff", violet="#7252bd"),
}


def apply_theme(theme):
    c = TOKENS[theme]
    variables = ";".join(f"--{key.replace('_', '-')}: {value}" for key, value in c.items())
    st.markdown(f"""<style>
    :root {{{variables};color-scheme:{theme}}}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{background:var(--background);color:var(--text-primary)}}
    [data-testid="stHeader"] {{display:none}}
    .block-container {{padding:1rem clamp(.8rem,2.4vw,3rem) 2rem;max-width:1920px}}
    h1,h2,h3,p,label,[data-testid="stWidgetLabel"],[data-testid="stMetricValue"] {{color:var(--text-primary)!important}}
    h1 {{font-size:1.65rem!important}} h2 {{font-size:1.2rem!important}} h3 {{font-size:1rem!important}}
    .stApp {{font-family:Inter,Arial,sans-serif}}
    [data-testid="stVerticalBlock"] {{gap:.7rem}}
    [data-testid="stColumn"], [data-testid="stElementContainer"] {{min-width:0}}
    [data-testid="stCaptionContainer"] {{opacity:1!important}}
    [data-testid="stCaptionContainer"] p {{color:var(--text-secondary)!important;font-size:.8rem;line-height:1.45}}
    [data-testid="stMetric"] {{height:100%;background:var(--surface);border-top:2px solid var(--accent);padding:.7rem .8rem}}
    [data-testid="stMetricValue"] {{font-size:clamp(1.3rem,2vw,1.8rem);line-height:1.25}}
    [data-testid="stTooltipHoverTarget"] svg, [data-testid="stTooltipIcon"] svg, [data-testid="stMetricLabel"] svg {{color:var(--text-secondary)!important;stroke:currentColor!important}}
    [data-testid="stMetricLabel"] {{height:auto;min-height:2.6rem;overflow:visible}}
    [data-testid="stMetricLabel"] p {{white-space:normal!important;overflow:visible!important;text-overflow:clip!important;line-height:1.3}}
    [class*="st-key-metrics-"] [data-testid="stHorizontalBlock"] {{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));gap:.65rem}}
    [class*="st-key-metrics-"] [data-testid="stColumn"] {{width:100%!important;min-width:0!important}}
    [data-baseweb="select"] > div, [data-baseweb="input"], [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] button, .stButton button,
    .stDownloadButton button, [data-baseweb="popover"], [role="listbox"], [role="option"],
    [role="combobox"], [data-testid="stSelectbox"] [role="group"],
    [data-testid="stNumberInputContainer"], [data-testid="stTextInputRootElement"] {{background:var(--surface)!important;color:var(--text-primary)!important;border-color:var(--border)!important;border-radius:5px!important}}
    [data-testid="stSelectbox"] button, [data-testid="stSelectbox"] button svg, [data-testid="stSelectbox"] svg {{color:var(--text-secondary)!important}}
    input::placeholder,textarea::placeholder {{color:var(--text-secondary)!important;opacity:1}}
    [role="option"][data-focused="true"], [role="option"]:hover,
    [role="option"][aria-selected="true"], [role="radio"][aria-checked="true"] {{background:var(--surface-secondary)!important;color:var(--accent)!important}}
    [role="radio"][aria-checked="true"] {{box-shadow:inset 0 -2px var(--accent)}}
    button:disabled,input:disabled {{color:var(--text-secondary)!important;opacity:.65}}
    button:focus-visible, input:focus-visible,[tabindex="0"]:focus-visible {{outline:2px solid var(--accent)!important;outline-offset:2px}}
    [data-testid="stTooltipContent"], [role="tooltip"] {{background:var(--surface-secondary)!important;color:var(--text-primary)!important;border:1px solid var(--border);max-width:min(340px,calc(100vw - 32px));overflow-wrap:anywhere}}
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {{border-color:var(--border)!important}}
    [data-testid="stExpander"] details {{background:var(--surface);color:var(--text-primary)}}
    summary {{min-height:42px;color:var(--text-primary)!important}}
    [role="tab"], [role="radio"] {{color:var(--text-primary)!important;min-height:40px;flex-shrink:0}}
    [role="tablist"] {{overflow-x:auto;scrollbar-width:thin;gap:1rem;max-width:100%}}
    [data-testid="stTabsScrollLeft"], [data-testid="stTabsScrollRight"] {{background:var(--surface)!important;color:var(--accent)!important;border:1px solid var(--border);border-radius:4px}}
    [role="tab"][aria-selected="true"] {{color:var(--accent)!important;border-color:var(--accent)!important}}
    [role="radio"] {{background:var(--surface)!important;border-color:var(--border)!important}}
    [role="radio"] p {{white-space:normal;line-height:1.2}}
    [data-testid="stMarkdownContainer"] a {{color:var(--accent)}}
    [data-testid="stMarkdownContainer"] .katex-display {{overflow-x:auto;overflow-y:hidden;padding:.3rem 0}}
    .desk-brand {{font-size:.85rem;font-weight:700;letter-spacing:.1em;color:var(--accent)}}
    .workspace-title {{font-size:.85rem;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.06em}}
    .market-strip {{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:.4rem}}
    .market-tile {{border:1px solid var(--border);background:var(--surface);padding:.55rem .65rem;display:flex;flex-direction:column;gap:.2rem;min-width:0}}
    .market-tile span {{font-size:.75rem;color:var(--text-secondary)}}
    .market-tile b {{font-size:.9rem;font-weight:600;white-space:nowrap}}
    .market-tile small {{font-size:.65rem;color:var(--text-secondary)}}
    .market-scroll-hint {{display:none}}
    .risk-line {{border-left:2px solid var(--warning);padding:.5rem .8rem;margin:.4rem 0;background:var(--surface)}}
    .guide-intro {{color:var(--text-secondary);font-size:.86rem;line-height:1.5;margin:0}}
    .source-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(270px,100%),1fr));gap:.5rem}}
    .source-card {{border-left:3px solid var(--accent);padding:.5rem .7rem;margin:.5rem 0;background:var(--surface-secondary);overflow-wrap:anywhere}}
    .source-card strong {{font-size:.9rem}} .source-card small {{display:block;color:var(--text-secondary);font-size:.78rem}}
    .workshop-table-wrap {{overflow-x:auto;border:1px solid var(--border);border-radius:6px}}
    .workshop-table {{width:100%;border-collapse:collapse;font-size:.85rem;color:var(--text-primary);background:var(--surface)}}
    .workshop-table th,.workshop-table td {{padding:.65rem .8rem;border-bottom:1px solid var(--border);text-align:right;overflow-wrap:break-word}}
    .workshop-table th {{background:var(--surface-secondary);font-weight:600}}
    .workshop-table th:first-child,.workshop-table td:first-child {{text-align:left}}
    .workshop-table tr:last-child td {{border-bottom:0}}
    .st-key-welcome-hero {{margin-top:.7rem;padding:clamp(1rem,2.8vw,2.5rem);border:1px solid var(--border);border-radius:14px;background:linear-gradient(135deg,var(--surface),var(--surface-secondary))}}
    .welcome-kicker {{font-size:.72rem;font-weight:700;letter-spacing:.13em;color:var(--accent);margin-bottom:.75rem}}
    .welcome-title {{font-size:clamp(2rem,3.5vw,3.6rem)!important;line-height:1.08;letter-spacing:-.035em;max-width:22ch;padding:0 0 1rem!important}}
    .welcome-lede {{font-size:1.05rem;line-height:1.65;max-width:56ch;margin-bottom:1rem}}
    .st-key-welcome-hero .stButton button {{background:var(--accent)!important;border-color:var(--accent)!important;min-height:46px;padding:.6rem 1rem}}
    .st-key-welcome-hero .stButton button, .st-key-welcome-hero .stButton button p {{color:var(--surface)!important;font-weight:600}}
    .welcome-route {{border-left:1px solid var(--border);padding-left:clamp(1rem,2vw,2rem)}}
    .welcome-route h2 {{margin:0 0 1rem;padding:0}}
    .welcome-route ol {{padding-left:1.35rem;margin:0}}
    .welcome-route li {{padding-left:.3rem;margin-bottom:1rem}}
    .welcome-route li::marker {{color:var(--accent);font-weight:700}}
    .welcome-route strong {{font-size:.95rem}}
    .welcome-route p {{color:var(--text-secondary)!important;font-size:.87rem;line-height:1.5;margin:.2rem 0 0}}
    .welcome-current {{display:flex;flex-wrap:wrap;gap:.5rem 1.2rem;align-items:center;padding:1rem 0 .2rem;font-size:.82rem}}
    .welcome-current span {{color:var(--text-secondary)}}
    .welcome-current strong {{color:var(--text-primary)}}
    .st-key-welcome-menu [data-testid="stHorizontalBlock"] {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}}
    .st-key-welcome-menu [data-testid="stColumn"] {{width:100%!important;min-width:0!important}}
    [class*="st-key-welcome-card-"] {{height:100%;padding:1.15rem;border:1px solid var(--border);border-radius:10px;background:var(--surface)}}
    [class*="st-key-welcome-card-"]:hover {{border-color:var(--accent)}}
    [class*="st-key-welcome-card-"] [data-testid="stElementContainer"]:last-child {{margin-top:auto}}
    .welcome-number {{display:block;font-size:.75rem;letter-spacing:.08em;color:var(--accent);margin-bottom:.65rem}}
    [class*="st-key-welcome-card-"] h3 {{font-size:1.1rem!important;padding:0 0 .4rem}}
    .welcome-question {{font-weight:600;font-size:.9rem;line-height:1.4}}
    .welcome-card-copy {{color:var(--text-secondary)!important;font-size:.86rem;line-height:1.6}}
    [class*="st-key-welcome-card-"] .stButton button {{min-height:44px;text-align:left}}
    @media(max-width:1100px) {{.st-key-welcome-menu [data-testid="stHorizontalBlock"] {{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
    @media(max-width:900px) {{
      .st-key-welcome-hero [data-testid="stHorizontalBlock"] {{display:grid;grid-template-columns:minmax(0,1fr);gap:1.5rem}}
      .st-key-welcome-hero [data-testid="stColumn"] {{width:100%!important;min-width:0!important}}
      .welcome-route {{border-left:0;border-top:1px solid var(--border);padding:1rem 0 0}}
    }}
    @media(max-width:640px) {{
      .st-key-welcome-menu [data-testid="stHorizontalBlock"] {{grid-template-columns:minmax(0,1fr)}}
      .welcome-current {{gap:.35rem .8rem}}
      .welcome-title {{font-size:2rem!important}}
      .welcome-lede {{font-size:.95rem}}
    }}
    @media(max-width:1100px) {{
      .st-key-terminal-header [data-testid="stHorizontalBlock"] {{display:grid;grid-template-columns: minmax(0,3fr) minmax(90px,1fr) minmax(105px,1fr)}}
      .st-key-terminal-header [data-testid="stColumn"] {{width:100%!important;min-width:0!important}}
      .st-key-terminal-header [data-testid="stColumn"]:nth-child(4) {{grid-column:1/-1}}
      .market-strip {{grid-template-columns:repeat(4,minmax(0,1fr))}}
    }}
    @media(max-width:640px) {{
      .block-container {{padding:.8rem .8rem 1.5rem}}
      [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{flex:1 1 100%!important;width:100%!important}}
      .st-key-terminal-header [data-testid="stHorizontalBlock"] {{grid-template-columns:1fr 1fr;gap:.4rem .7rem}}
      .st-key-terminal-header [data-testid="stColumn"]:first-child {{grid-column:1/-1}}
      .st-key-book-selector [data-testid="stHorizontalBlock"] {{display:grid;grid-template-columns:minmax(0,2fr) minmax(90px,1fr);gap:.4rem .7rem}}
      .st-key-book-selector [data-testid="stColumn"] {{width:100%!important;min-width:0!important}}
      .st-key-book-selector [data-testid="stColumn"]:nth-child(3) {{grid-column:1/-1}}
      [class*="st-key-metrics-"] [data-testid="stHorizontalBlock"] {{grid-template-columns:repeat(2,minmax(0,1fr))}}
      .market-strip {{display:grid;grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:150px;overflow-x:auto;scroll-snap-type:x proximity;padding-bottom:.4rem;scrollbar-width:thin}}
      .market-tile {{scroll-snap-align:start}}
      .market-scroll-hint {{display:block;color:var(--text-secondary);font-size:.75rem;margin:0 0 .3rem}}
      [data-testid="stMetric"] {{padding:.6rem .65rem}}
      [role="tablist"] {{gap:.9rem}}
      .js-plotly-plot {{touch-action:pan-y}}
    }}
    @media(prefers-reduced-motion:reduce) {{*,*::before,*::after {{scroll-behavior:auto!important;transition:none!important}}}}
    </style>""", unsafe_allow_html=True)
