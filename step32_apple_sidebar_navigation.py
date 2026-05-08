from pathlib import Path

ROOT = Path(".")

SIDEBAR_CSS = '''
        /* Apple-style sidebar navigation */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #8a8f98;
            margin-top: 0.45rem;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.18rem;
            margin-top: 0.25rem;
        }

        /* Hide the raw radio dots */
        div[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
            display: none !important;
        }

        /* Base item */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px !important;
            padding: 0.52rem 0.62rem !important;
            margin: 0 !important;
            min-height: 38px;
            transition: background 0.14s ease-in-out, border-color 0.14s ease-in-out, transform 0.14s ease-in-out;
            box-shadow: none !important;
            cursor: pointer;
        }

        /* Text */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 0.91rem !important;
            font-weight: 520 !important;
            color: #2f343b !important;
            line-height: 1.1rem !important;
        }

        /* Hover: very light Apple-like grey */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.04) !important;
            transform: none !important;
        }

        /* Selected item: Apple Finder-style subtle capsule */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: rgba(120, 120, 128, 0.16) !important;
            border-color: rgba(120, 120, 128, 0.08) !important;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18) !important;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
            color: #111827 !important;
            font-weight: 700 !important;
        }

        /* Sidebar links: flatter, Apple-like */
        div[data-testid="stSidebar"] .stLinkButton > a {
            border-radius: 10px !important;
            border: 1px solid rgba(120, 120, 128, 0.14) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            box-shadow: none !important;
            font-weight: 600 !important;
        }

        div[data-testid="stSidebar"] .stLinkButton > a:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.20) !important;
            transform: none !important;
            box-shadow: none !important;
        }
'''

TEST_CODE = r'''
from pathlib import Path


def test_theme_contains_apple_sidebar_navigation_styles():
    text = Path("app_pages/theme.py").read_text()

    assert "Apple-style sidebar navigation" in text
    assert "display: none !important" in text
    assert "rgba(120, 120, 128" in text


def test_app_keeps_sidebar_radio_navigation_logic():
    text = Path("app.py").read_text()

    assert "st.radio(" in text
    assert "format_func=lambda page" in text
    assert "PAGE_LABELS" in text


def test_sidebar_labels_are_still_present():
    text = Path("app.py").read_text()

    required_labels = [
        "Home",
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
        "Portfolio Risk",
        "Cross-Asset Dashboard",
    ]

    for label in required_labels:
        assert label in text
'''


def patch_theme() -> None:
    theme_path = ROOT / "app_pages" / "theme.py"
    text = theme_path.read_text(encoding="utf-8")

    # Remove previous premium sidebar nav blocks if they exist, by appending a stronger override.
    # The override is intentionally placed near the end of the CSS block so it wins.
    if "Apple-style sidebar navigation" not in text:
        marker = "        .stAlert {\n"
        if marker not in text:
            raise RuntimeError("Could not find CSS insertion point in app_pages/theme.py")
        text = text.replace(marker, SIDEBAR_CSS + "\n" + marker, 1)

    theme_path.write_text(text, encoding="utf-8")
    print("Patched app_pages/theme.py with Apple-style sidebar navigation.")


def write_tests() -> None:
    test_path = ROOT / "tests" / "test_apple_sidebar_navigation.py"
    test_path.write_text(TEST_CODE.lstrip(), encoding="utf-8")
    print("Added tests/test_apple_sidebar_navigation.py")


def main() -> None:
    patch_theme()
    write_tests()

    print("\nStep 32 Apple-style sidebar navigation complete.")
    print("Run:")
    print("python -m pytest tests/test_apple_sidebar_navigation.py -q")
    print("python -m pytest -q")
    print("python -m streamlit run app.py")


if __name__ == "__main__":
    main()
