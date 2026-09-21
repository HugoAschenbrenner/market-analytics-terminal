"""Exercise the public entry point and the actual links emitted by both versions."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl

import pytest
from streamlit.testing.v1 import AppTest

from components.version_switch import version_url


class VersionLink(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("class") == "mat-version-link":
            self.link = attrs


def app_for(query=None):
    app = AppTest.from_file(str(Path("app.py").resolve()), default_timeout=40)
    app.query_params.update(query or {})
    app.run()
    assert not app.exception and not app.error
    return app


def switch_link(app):
    parser = VersionLink()
    for markdown in app.markdown:
        parser.feed(markdown.value)
    assert parser.link["target"] == "_self"
    assert parser.link["href"].startswith("?version=")
    return dict(parse_qsl(parser.link["href"][1:]))


@pytest.mark.parametrize("query", [{}, {"version": "v1"}, {"version": "unknown"},
                                   {"page": "markets"}, {"version": "v1", "page": "welcome"}])
def test_root_and_invalid_versions_keep_v1_as_main_page(query):
    app = app_for(query)
    assert "terminal" not in app.session_state
    assert any(h.value == "Multi-Asset Desk Utility Platform" for h in app.title)
    assert switch_link(app)["version"] == "v2"


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_emitted_links_complete_round_trip_and_keep_v2_preferences(language, theme):
    v1 = app_for({"lang": language, "theme": theme})
    v2 = app_for(switch_link(v1))
    assert v2.session_state.terminal.ui.page == "welcome"
    assert v2.session_state.terminal.ui.language == language
    assert v2.session_state.terminal.ui.theme == theme
    v2.button(key="welcome-open-equity-derivatives").click().run()
    assert not v2.exception and not v2.error
    assert v2.query_params["version"] == ["v2"]
    returned = app_for(switch_link(v2))
    assert returned.query_params["page"] == ["home"]
    assert "terminal" not in returned.session_state
    assert switch_link(returned)["lang"] == language
    assert switch_link(returned)["theme"] == theme


def test_version_urls_drop_stale_routes_and_reject_untrusted_preferences():
    assert version_url("v2", '<script>', 'https://example.com') == '?version=v2&page=welcome&lang=en&theme=dark'
    assert version_url("v1", 'fr', 'light') == '?version=v1&page=home&lang=fr&theme=light'
    with pytest.raises(ValueError):
        version_url("https://example.com")
