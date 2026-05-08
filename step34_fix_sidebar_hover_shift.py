from pathlib import Path

ROOT = Path(".")
THEME_PATH = ROOT / "app_pages" / "theme.py"
TEST_PATH = ROOT / "tests" / "test_sidebar_hover_stability.py"

CSS_FIX = '''
        /* Sidebar hover stability fix: no layout shift */
        div[data-testid="stSidebar"] .stButton > button,
        div[data-testid="stSidebar"] .stButton > button:hover,
        div[data-testid="stSidebar"] .stButton > button:focus,
        div[data-testid="stSidebar"] .stButton > button:active {
            transform: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stSidebar"] .stLinkButton > a,
        div[data-testid="stSidebar"] .stLinkButton > a:hover,
        div[data-testid="stSidebar"] .stLinkButton > a:focus,
        div[data-testid="stSidebar"] .stLinkButton > a:active {
            transform: none !important;
            box-shadow: none !important;
        }

        .mat-sidebar-active,
        .mat-sidebar-active:hover {
            transform: none !important;
            box-shadow: none !important;
        }
'''

TEST_CODE = '''
from pathlib import Path


def test_sidebar_hover_has_no_transform_shift():
    text = Path("app_pages/theme.py").read_text()

    assert "Sidebar hover stability fix" in text
    assert "transform: none !important" in text
    assert "mat-sidebar-active:hover" in text
'''

text = THEME_PATH.read_text(encoding="utf-8")

if "Sidebar hover stability fix" not in text:
    marker = "        .stAlert {\n"
    if marker not in text:
        raise RuntimeError("Could not find CSS insertion point in theme.py")
    text = text.replace(marker, CSS_FIX + "\n" + marker, 1)

THEME_PATH.write_text(text, encoding="utf-8")
TEST_PATH.write_text(TEST_CODE.lstrip(), encoding="utf-8")

print("Patched sidebar hover stability.")
print("Run:")
print("python -m pytest tests/test_sidebar_hover_stability.py -q")
print("python -m pytest -q")
print("python -m streamlit run app.py")
