from pathlib import Path


def test_app_uses_session_state_navigation_key():
    text = Path("app.py").read_text()

    assert 'key="selected_page"' in text
    assert 'st.session_state["selected_page"]' in text


def test_home_page_contains_quick_launch_buttons():
    text = Path("app_pages/home.py").read_text()

    assert "Open module" in text
    assert "_go_to_page" in text
    assert "st.rerun()" in text


def test_home_page_contains_all_module_targets():
    text = Path("app_pages/home.py").read_text()

    required_pages = [
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
        "Portfolio Risk",
        "Cross-Asset Dashboard",
    ]

    for page in required_pages:
        assert page in text
