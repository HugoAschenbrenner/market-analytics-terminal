"""All automated app tests are offline; adapters have explicit fixture tests."""
import pytest

@pytest.fixture(autouse=True)
def offline_v2_context(monkeypatch):
    from services import market_data
    monkeypatch.setattr(market_data,'load_public_context',lambda *a,**kw:{})
