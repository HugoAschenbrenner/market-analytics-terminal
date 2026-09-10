from pathlib import Path


def test_theme_file_exists_and_contains_global_styles():
    text = Path("app_pages/theme.py").read_text()

    assert "apply_global_styles" in text
    assert "stMetric" in text
    assert "stButton" in text


def test_app_imports_and_applies_global_styles():
    text = Path("app.py").read_text()

    assert "from components.global_header import global_header" in text
    assert "global_header(state)" in text
