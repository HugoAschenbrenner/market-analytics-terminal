"""All automated app tests are offline; adapters have explicit fixture tests."""
import pytest

@pytest.fixture(autouse=True)
def offline_v2_context(monkeypatch):
    from services import market_data
    monkeypatch.setattr(market_data,'load_public_context',lambda *a,**kw:{})

    from services import market_monitor
    monkeypatch.setattr(market_monitor,'request_text',lambda *a,**kw: (_ for _ in ()).throw(OSError('Offline test')))
    market_monitor.get_market_service.clear()
    from services import market_news
    monkeypatch.setattr(market_news,'request_text',lambda *a,**kw: (_ for _ in ()).throw(OSError('Offline test')))
    monkeypatch.setattr(market_monitor.MarketService,'fundamentals',lambda *a,**kw: __import__('core.market_contracts',fromlist=['DataResult']).DataResult())
