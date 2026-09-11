from pathlib import Path




def test_app_imports_and_applies_global_styles():
    text = Path("app.py").read_text()

    assert "from components.global_header import global_header" in text
    assert "global_header(state)" in text
