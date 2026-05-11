from pathlib import Path


def test_runtime_streamlit_code_does_not_use_width_stretch():
    runtime_files = [Path("app.py")] + sorted(Path("app_pages").glob("*.py"))

    offenders = []

    for path in runtime_files:
        text = path.read_text()
        if 'width="stretch"' in text or "width='stretch'" in text:
            offenders.append(str(path))

    assert offenders == []
