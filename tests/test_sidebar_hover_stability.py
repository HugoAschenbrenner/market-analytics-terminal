from pathlib import Path


def test_sidebar_navigation_uses_stable_links():
    text = Path("app.py").read_text()

    assert "render_sidebar_nav_link" in text
    assert 'href="?page=' in text
    assert "st.query_params" in text
    assert "st.radio(" not in text
