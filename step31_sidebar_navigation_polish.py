from pathlib import Path

ROOT = Path(".")

APP_CODE = r'''
import streamlit as st

from app_pages.theme import apply_global_styles
from app_pages import (
    cross_asset_dashboard,
    fixed_income,
    home,
    portfolio_risk,
    repo_sec_lending,
    structured_products,
)

st.set_page_config(
    page_title="Market Analytics Terminal",
    page_icon="📊",
    layout="wide",
)

apply_global_styles()

PAGES = {
    "Home": home.render,
    "Fixed Income Risk": fixed_income.render,
    "Repo & Securities Lending": repo_sec_lending.render,
    "Structured Products": structured_products.render,
    "Portfolio Risk": portfolio_risk.render,
    "Cross-Asset Dashboard": cross_asset_dashboard.render,
}

PAGE_LABELS = {
    "Home": "⌂  Home",
    "Fixed Income Risk": "◔  Fixed Income Risk",
    "Repo & Securities Lending": "⇄  Repo & Securities Lending",
    "Structured Products": "◇  Structured Products",
    "Portfolio Risk": "▣  Portfolio Risk",
    "Cross-Asset Dashboard": "◎  Cross-Asset Dashboard",
}

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Home"

if st.session_state["selected_page"] not in PAGES:
    st.session_state["selected_page"] = "Home"

with st.sidebar:
    st.title("Market Analytics Terminal")
    st.caption("Personal multi-asset analytics project")

    st.caption("Built by Hugo Aschenbrenner")
    st.caption("SKEMA MSc Financial Markets & Investments")

    st.link_button(
        "GitHub",
        "https://github.com/HugoAschenbrenner/market-analytics-terminal",
        width="stretch",
    )
    st.link_button(
        "LinkedIn",
        "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
        width="stretch",
    )

    st.divider()

    st.markdown("##### Desk Modules")
    st.caption("Navigate across analytics engines")

    current_page = st.session_state["selected_page"]
    current_index = list(PAGES.keys()).index(current_page)

    sidebar_selection = st.radio(
        "Desk Modules",
        list(PAGES.keys()),
        index=current_index,
        format_func=lambda page: PAGE_LABELS.get(page, page),
        label_visibility="collapsed",
    )

    st.session_state["selected_page"] = sidebar_selection

    st.divider()

    st.markdown("### Build standard")
    st.caption("Input → Calculation → Scenario → Interpretation → Export")

    st.divider()

    st.caption(
        "Educational/proxy analytics only. Not investment advice, "
        "not a trading bot, and not bank-grade pricing."
    )

selected_page = st.session_state["selected_page"]
PAGES[selected_page]()
'''

SIDEBAR_CSS = '''
        /* Premium sidebar module navigation */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            margin-top: 0.35rem;
            margin-bottom: 0.20rem;
            font-weight: 800;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.32rem;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 14px;
            padding: 0.68rem 0.75rem;
            margin: 0;
            transition: all 0.16s ease-in-out;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: rgba(59, 130, 246, 0.45);
            background: rgba(239, 246, 255, 0.90);
            transform: translateX(2px);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(180deg, #eff6ff 0%, #eaf2ff 100%);
            border-color: rgba(59, 130, 246, 0.55);
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.12);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 0.92rem;
            font-weight: 570;
            color: #1f2937;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
            color: #0f3d91;
            font-weight: 750;
        }
'''

TEST_CODE = r'''
from pathlib import Path


def test_sidebar_uses_polished_module_labels():
    text = Path("app.py").read_text()

    assert "PAGE_LABELS" in text
    assert "Desk Modules" in text
    assert "format_func=lambda page" in text
    assert "label_visibility=\"collapsed\"" in text


def test_sidebar_keeps_profile_links_at_top():
    text = Path("app.py").read_text()

    profile_index = text.index("Built by Hugo Aschenbrenner")
    nav_index = text.index("Desk Modules")

    assert profile_index < nav_index
    assert "https://github.com/HugoAschenbrenner/market-analytics-terminal" in text
    assert "https://www.linkedin.com/in/hugo-aschenbrenner-pro" in text


def test_theme_contains_sidebar_navigation_styles():
    text = Path("app_pages/theme.py").read_text()

    assert "Premium sidebar module navigation" in text
    assert "radiogroup" in text
    assert "translateX" in text
'''


def patch_theme() -> None:
    theme_path = ROOT / "app_pages" / "theme.py"
    text = theme_path.read_text(encoding="utf-8")

    if "Premium sidebar module navigation" in text:
        print("Sidebar CSS already present.")
        return

    marker = "        .stAlert {\n"
    if marker not in text:
        raise RuntimeError("Could not find CSS insertion point in app_pages/theme.py")

    text = text.replace(marker, SIDEBAR_CSS + "\n" + marker, 1)
    theme_path.write_text(text, encoding="utf-8")
    print("Patched app_pages/theme.py with sidebar navigation CSS.")


def main() -> None:
    app_path = ROOT / "app.py"
    app_path.write_text(APP_CODE.lstrip(), encoding="utf-8")
    print("Updated app.py with polished sidebar navigation.")

    patch_theme()

    test_path = ROOT / "tests" / "test_sidebar_navigation_polish.py"
    test_path.write_text(TEST_CODE.lstrip(), encoding="utf-8")
    print("Added tests/test_sidebar_navigation_polish.py")

    print("\nStep 31 Sidebar Navigation Polish complete.")
    print("Run:")
    print("python -m pytest tests/test_sidebar_navigation_polish.py -q")
    print("python -m pytest -q")
    print("python -m streamlit run app.py")


if __name__ == "__main__":
    main()
