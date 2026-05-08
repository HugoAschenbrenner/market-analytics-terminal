from pathlib import Path


def test_home_contains_executive_demo_layer():
    text = Path("app_pages/home.py").read_text()

    required_terms = [
        "Executive Snapshot",
        "What This Terminal Can Answer",
        "Top 3 Risk Insights",
        "Recommended next check",
    ]

    for term in required_terms:
        assert term in text


def test_home_executive_layer_preserves_ownership_and_data_policy():
    text = Path("app_pages/home.py").read_text()

    assert "Built by Hugo Aschenbrenner" in text
    assert "SKEMA Business School" in text
    assert "No proprietary client, employer, or confidential market data" in text


def test_home_executive_layer_has_risk_questions():
    text = Path("app_pages/home.py").read_text()

    required_questions = [
        "Where is duration risk concentrated",
        "How much margin call",
        "What is the payoff profile",
        "Which asset contributes most",
        "Which cross-asset stress scenario",
    ]

    for question in required_questions:
        assert question in text


def test_home_executive_insights_link_to_modules():
    text = Path("app_pages/home.py").read_text()

    required_pages = [
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
    ]

    for page in required_pages:
        assert page in text

    assert "Open module" in text
    assert "st.rerun()" in text
