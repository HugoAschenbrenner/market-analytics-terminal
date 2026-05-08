from pathlib import Path


def test_readme_exists_and_mentions_core_modules():
    text = Path("README.md").read_text()

    required_terms = [
        "Fixed Income Risk",
        "Repo & Securities Lending",
        "Structured Products",
        "Portfolio Risk",
        "R Portfolio Analytics Companion",
    ]

    for term in required_terms:
        assert term in text


def test_documentation_files_exist():
    expected_files = [
        "docs/project_overview.md",
        "docs/technical_validation.md",
        "docs/cv_positioning.md",
    ]

    for file_path in expected_files:
        assert Path(file_path).exists()


def test_cv_positioning_contains_interview_pitch():
    text = Path("docs/cv_positioning.md").read_text()

    assert "Interview Pitch" in text
    assert "Market Analytics Terminal" in text
