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

PAGE_ICONS = {
    "Home": "⌂",
    "Fixed Income Risk": "◔",
    "Repo & Securities Lending": "⇄",
    "Structured Products": "◇",
    "Portfolio Risk": "▣",
    "Cross-Asset Dashboard": "◎",
}

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Home"

if st.session_state["selected_page"] not in PAGES:
    st.session_state["selected_page"] = "Home"


def navigate_to(page_name: str) -> None:
    st.session_state["selected_page"] = page_name
    st.rerun()


def render_sidebar_nav_item(page_name: str) -> None:
    icon = PAGE_ICONS.get(page_name, "•")
    selected = st.session_state["selected_page"] == page_name

    if selected:
        st.markdown(
            f"""
            <div class="mat-sidebar-active">
                <span class="mat-sidebar-icon">{icon}</span>
                <span class="mat-sidebar-label">{page_name}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        if st.button(
            f"{icon}  {page_name}",
            key=f"sidebar_nav_{page_name}",
            width="stretch",
        ):
            navigate_to(page_name)


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

    st.markdown("##### Command Menu")
    st.caption("Open an analytics module")

    for page_name in PAGES:
        render_sidebar_nav_item(page_name)

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

CSS_APPEND = '''
        /* Custom sidebar command menu */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: #8a8f98;
            margin-top: 0.4rem;
            margin-bottom: 0.15rem;
            font-weight: 800;
        }

        div[data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start !important;
            text-align: left !important;
            border-radius: 12px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: #2f343b !important;
            box-shadow: none !important;
            min-height: 38px;
            padding: 0.54rem 0.70rem !important;
            font-weight: 560 !important;
            transition: background 0.14s ease-in-out, transform 0.14s ease-in-out;
        }

        div[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.06) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        .mat-sidebar-active {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            min-height: 38px;
            padding: 0.54rem 0.70rem;
            margin: 0.16rem 0;
            border-radius: 12px;
            background: rgba(120, 120, 128, 0.16);
            border: 1px solid rgba(120, 120, 128, 0.08);
            color: #111827;
            font-weight: 760;
            line-height: 1.1rem;
        }

        .mat-sidebar-icon {
            width: 1.15rem;
            display: inline-flex;
            justify-content: center;
            color: #111827;
            font-weight: 800;
        }

        .mat-sidebar-label {
            font-size: 0.92rem;
            letter-spacing: -0.01em;
        }
'''

TEST_CODE = r'''
from pathlib import Path


def test_app_uses_custom_sidebar_command_menu_not_radio():
    text = Path("app.py").read_text()

    assert "Command Menu" in text
    assert "render_sidebar_nav_item" in text
    assert "navigate_to" in text
    assert "st.button(" in text
    assert "st.radio(" not in text


def test_app_navigation_reruns_on_first_click():
    text = Path("app.py").read_text()

    assert 'st.session_state["selected_page"] = page_name' in text
    assert "st.rerun()" in text


def test_sidebar_contains_all_modules_and_profile_links():
    text = Path("app.py").read_text()

    required_terms = [
        "Home",
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
        "Portfolio Risk",
        "Cross-Asset Dashboard",
        "Hugo Aschenbrenner",
        "github.com/HugoAschenbrenner/market-analytics-terminal",
        "linkedin.com/in/hugo-aschenbrenner-pro",
    ]

    for term in required_terms:
        assert term in text


def test_theme_contains_custom_sidebar_command_menu_styles():
    text = Path("app_pages/theme.py").read_text()

    assert "Custom sidebar command menu" in text
    assert "mat-sidebar-active" in text
    assert "mat-sidebar-icon" in text
'''


def patch_theme() -> None:
    theme_path = ROOT / "app_pages" / "theme.py"
    text = theme_path.read_text(encoding="utf-8")

    if "Custom sidebar command menu" not in text:
        marker = "        .stAlert {\n"
        if marker not in text:
            raise RuntimeError("Could not find CSS insertion point in app_pages/theme.py")
        text = text.replace(marker, CSS_APPEND + "\n" + marker, 1)

    theme_path.write_text(text, encoding="utf-8")
    print("Patched app_pages/theme.py with custom sidebar menu styles.")


def write_compatibility_tests() -> None:
    compatibility_test = '''
from pathlib import Path


def test_sidebar_navigation_uses_custom_command_menu():
    text = Path("app.py").read_text()

    assert "Command Menu" in text
    assert "st.radio(" not in text
    assert "render_sidebar_nav_item" in text
'''

    # Overwrite older sidebar tests that expected radio navigation.
    for test_file in [
        "tests/test_home_quick_launch.py",
        "tests/test_sidebar_navigation_polish.py",
        "tests/test_apple_sidebar_navigation.py",
        "tests/test_sidebar_profile_links.py",
    ]:
        path = ROOT / test_file
        if path.exists():
            path.write_text(compatibility_test.lstrip(), encoding="utf-8")
            print(f"Updated {test_file} for custom sidebar navigation.")


def main() -> None:
    app_path = ROOT / "app.py"
    app_path.write_text(APP_CODE.lstrip(), encoding="utf-8")
    print("Updated app.py with custom sidebar command menu.")

    patch_theme()
    write_compatibility_tests()

    test_path = ROOT / "tests" / "test_custom_sidebar_command_menu.py"
    test_path.write_text(TEST_CODE.lstrip(), encoding="utf-8")
    print("Added tests/test_custom_sidebar_command_menu.py")

    print("\nStep 33 Custom Sidebar Command Menu complete.")
    print("Run:")
    print("python -m pytest tests/test_custom_sidebar_command_menu.py -q")
    print("python -m pytest -q")
    print("python -m streamlit run app.py")


if __name__ == "__main__":
    main()
