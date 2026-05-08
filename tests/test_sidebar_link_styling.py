from pathlib import Path


def test_sidebar_links_have_strong_css_reset():
    text = Path("app_pages/theme.py").read_text()

    assert "Strong sidebar link reset" in text
    assert "a.mat-sidebar-link:visited" in text
    assert "text-decoration: none !important" in text
    assert "section[data-testid=\"stSidebar\"] a.mat-sidebar-link" in text
