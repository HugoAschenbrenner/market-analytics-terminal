from pathlib import Path


def test_app_uses_stable_sidebar_links_not_buttons_or_radio():
    text = Path("app.py").read_text()

    assert "render_sidebar_nav_link" in text
    assert 'href="?page=' in text
    assert "st.radio(" not in text
    assert "render_sidebar_nav_item" not in text


def test_app_uses_query_params_for_navigation():
    text = Path("app.py").read_text()

    assert "st.query_params" in text
    assert "PAGE_SLUGS" in text
    assert "SLUG_TO_PAGE" in text


def test_sidebar_contains_all_module_slugs():
    text = Path("app.py").read_text()

    required_slugs = [
        "home",
        "fixed-income-risk",
        "repo-sec-lending",
        "structured-products",
        "portfolio-risk",
        "cross-asset-dashboard",
    ]

    for slug in required_slugs:
        assert slug in text


def test_theme_contains_stable_sidebar_link_styles():
    text = Path("app_pages/theme.py").read_text()

    assert "Stable Apple-style sidebar links" in text
    assert ".mat-sidebar-link" in text
    assert "transform: none !important" in text
