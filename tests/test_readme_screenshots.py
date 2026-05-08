from pathlib import Path


def test_readme_contains_demo_screenshots_section():
    text = Path("README.md").read_text()

    assert "## Demo Screenshots" in text

    required_images = [
        "docs/screenshots/01_home.png",
        "docs/screenshots/02_fixed_income_risk.png",
        "docs/screenshots/03_repo_sec_lending.png",
        "docs/screenshots/04_structured_products.png",
        "docs/screenshots/05_portfolio_risk.png",
        "docs/screenshots/06_cross_asset_dashboard.png",
    ]

    for image_path in required_images:
        assert image_path in text


def test_demo_screenshot_files_exist():
    required_images = [
        "docs/screenshots/01_home.png",
        "docs/screenshots/02_fixed_income_risk.png",
        "docs/screenshots/03_repo_sec_lending.png",
        "docs/screenshots/04_structured_products.png",
        "docs/screenshots/05_portfolio_risk.png",
        "docs/screenshots/06_cross_asset_dashboard.png",
    ]

    for image_path in required_images:
        assert Path(image_path).exists()
