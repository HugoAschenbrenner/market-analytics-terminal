from pathlib import Path


def test_home_page_has_no_placeholder_statuses():
    text = Path("app_pages/home.py").read_text()

    assert "Planned" not in text
    assert "Next build priority" not in text


def test_home_page_mentions_completed_modules():
    text = Path("app_pages/home.py").read_text()

    required_modules = [
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
        "Portfolio Risk",
        "Cross-Asset Dashboard",
    ]

    for module in required_modules:
        assert module in text
