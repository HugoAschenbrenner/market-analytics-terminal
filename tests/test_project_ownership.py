from pathlib import Path






def test_sidebar_contains_author_and_links():
    text = Path("components/global_header.py").read_text() + Path("core/i18n.py").read_text()

    assert "Built by Hugo Aschenbrenner" in text
    assert "HugoAschenbrenner/market-analytics-terminal" in text
    assert "hugo-aschenbrenner-pro" in text
