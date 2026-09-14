from pathlib import Path

from PIL import Image


SCREENSHOTS = [
    "docs/screenshots/v2_overview_light.jpg",
    "docs/screenshots/v2_markets_dark.jpg",
    "docs/screenshots/v2_risk_light.jpg",
    "docs/screenshots/v2_derivatives_dark.jpg",
    "docs/screenshots/v2_financing_fr_dark.jpg",
]


def test_readme_contains_demo_screenshots_section():
    text = Path("README.md").read_text()
    assert "## Demo Screenshots" in text
    for image_path in SCREENSHOTS:
        assert image_path in text


def test_demo_screenshot_files_exist():
    for image_path in SCREENSHOTS:
        with Image.open(image_path) as screenshot:
            assert screenshot.format == "JPEG"
            assert screenshot.width >= 600 and screenshot.height >= 400
            screenshot.verify()
