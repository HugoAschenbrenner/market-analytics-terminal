"""Same-site version links with a clean route and explicit session boundary."""
from html import escape
from urllib.parse import urlencode

import streamlit as st

from core.theme import TOKENS


def version_url(version: str, language: str = "en", theme: str = "dark") -> str:
    if version not in ("v1", "v2"):
        raise ValueError("Unknown terminal version")
    language = language if language in ("en", "fr") else "en"
    theme = theme if theme in ("light", "dark") else "dark"
    return "?" + urlencode({
        "version": version,
        "page": "welcome" if version == "v2" else "home",
        "lang": language,
        "theme": theme,
    })


def render_version_switch(version: str, language: str | None = None, theme: str | None = None) -> None:
    language = language or st.query_params.get("lang", "en")
    theme = theme or st.query_params.get("theme", "dark")
    french = language == "fr"
    if version == "v1":
        label = "V1 · Version principale" if french else "V1 · Main version"
        action = "Découvrir la V2 →" if french else "Discover V2 →"
        description = ("Explorez la nouvelle interface. La V1 reste l’accueil du site." if french
                       else "Explore the new interface. V1 remains the default home page.")
        target = "v2"
    else:
        label = "V2 · Nouvelle interface" if french else "V2 · New interface"
        action = "← Retour à la V1" if french else "← Back to V1"
        description = ("Retrouvez à tout moment les modules de la version principale." if french
                       else "Return to the main version’s modules at any time.")
        target = "v1"
    session_note = ("Le changement de version ouvre une nouvelle session : exportez vos travaux avant de changer." if french
                    else "Switching versions starts a new session: export your work before switching.")
    colors = TOKENS[theme if version == "v2" and theme in TOKENS else "light"]
    # A full same-tab navigation isolates each interface's widget state and CSS.
    # Relative URLs also work under Streamlit Cloud's application iframe path.
    st.markdown(f"""
<style>
.mat-version-switch {{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding:.8rem 1rem;margin:.25rem 0 1rem;border:1px solid {colors['border']};border-radius:10px;background:{colors['surface']};color:{colors['text_primary']};}}
.mat-version-switch strong {{display:block;font-size:.85rem;}}
.mat-version-switch small {{display:block;line-height:1.5;color:{colors['text_secondary']};}}
.mat-version-switch a.mat-version-link {{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.5rem 1rem;border:1px solid {colors['accent']};border-radius:6px;color:{colors['accent']};text-decoration:none;font-weight:650;white-space:nowrap;}}
.mat-version-switch a.mat-version-link:hover {{background:{colors['surface_secondary']};text-decoration:underline;}}
.mat-version-switch a.mat-version-link:focus-visible {{outline:3px solid {colors['accent']};outline-offset:3px;}}
@media(max-width:600px) {{.mat-version-switch a.mat-version-link {{width:100%;white-space:normal;text-align:center;}}}}
</style>
<nav class="mat-version-switch" aria-label="Terminal version">
  <div><strong>{escape(label)}</strong><small>{escape(description)}</small><small>{escape(session_note)}</small></div>
  <a class="mat-version-link" href="{escape(version_url(target, language, theme), quote=True)}" target="_self">{escape(action)}</a>
</nav>
""", unsafe_allow_html=True)
