from pathlib import Path


def test_home_page_contains_project_ownership_layer():
    text = Path("app_pages/home.py").read_text()

    assert "Built by Hugo Aschenbrenner" in text
    assert "SKEMA Business School" in text
    assert "About This Project" in text


def test_home_page_contains_data_policy():
    text = Path("app_pages/home.py").read_text()

    assert "synthetic sample data" in text
    assert "user-provided inputs" in text
    assert "No proprietary client, employer, or confidential market data" in text


def test_sidebar_contains_author_and_links():
    text = Path("app.py").read_text()

    assert "Built by Hugo Aschenbrenner" in text
    assert "HugoAschenbrenner/market-analytics-terminal" in text
    assert "hugo-aschenbrenner-pro" in text


def test_home_page_uses_implemented_status_instead_of_live():
    text = Path("app_pages/home.py").read_text()

    assert "Implemented" in text
