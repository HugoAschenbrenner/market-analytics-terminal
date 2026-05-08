from pathlib import Path

APP_PATH = Path("app.py")
TEST_PATH = Path("tests/test_sidebar_profile_links.py")

text = APP_PATH.read_text(encoding="utf-8")

old_project_block = '''    st.divider()

    st.markdown("### Project")
    st.caption("Built by Hugo Aschenbrenner")
    st.caption("SKEMA MSc Financial Markets & Investments")
    st.link_button(
        "GitHub repository",
        "https://github.com/HugoAschenbrenner/market-analytics-terminal",
        width="stretch",
    )
    st.link_button(
        "LinkedIn profile",
        "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
        width="stretch",
    )
'''

top_profile_block = '''    st.caption("Built by Hugo Aschenbrenner")
    st.caption("SKEMA MSc Financial Markets & Investments")

    st.link_button(
        "GitHub",
        "https://github.com/HugoAschenbrenner/market-analytics-terminal",
        width="stretch",
    )
    st.link_button(
        "LinkedIn",
        "https://www.linkedin.com/in/hugo-aschenbrenner-pro",
        width="stretch",
    )

    st.divider()
'''

if old_project_block in text:
    text = text.replace(old_project_block, "", 1)

anchor = '    st.caption("Personal multi-asset analytics project")\n\n'

if top_profile_block not in text:
    if anchor not in text:
        raise RuntimeError("Could not find sidebar caption anchor.")
    text = text.replace(anchor, anchor + top_profile_block, 1)

APP_PATH.write_text(text, encoding="utf-8")

TEST_PATH.write_text(
    '''
from pathlib import Path


def test_sidebar_profile_links_are_near_top():
    text = Path("app.py").read_text()

    profile_index = text.index("Built by Hugo Aschenbrenner")
    radio_index = text.index("st.radio(")

    assert profile_index < radio_index


def test_sidebar_contains_github_and_linkedin_links():
    text = Path("app.py").read_text()

    assert "https://github.com/HugoAschenbrenner/market-analytics-terminal" in text
    assert "https://www.linkedin.com/in/hugo-aschenbrenner-pro" in text
    assert '"GitHub"' in text
    assert '"LinkedIn"' in text
'''.lstrip(),
    encoding="utf-8",
)

print("Moved GitHub and LinkedIn links near the top of the sidebar.")
