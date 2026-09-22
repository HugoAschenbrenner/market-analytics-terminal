"""V2 public instrument directory. IDs are stable; provider symbols are not routes."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Security:
    id: str
    name: str
    asset_class: str
    symbol: str
    currency: str = 'USD'
    venue: str = ''
    region: str = 'Americas'
    timezone: str = 'America/New_York'
    unit: str = 'price'
    provider: str = 'Yahoo Finance'
    aliases: str = ''


def _s(id, name, asset, symbol=None, **kwargs):
    return Security(id, name, asset, symbol or id, **kwargs)


DIRECTORY = [
    _s('NVDA','NVIDIA','Equities',venue='Nasdaq'),
    _s('AAPL','Apple','Equities',venue='Nasdaq'),
    _s('MSFT','Microsoft','Equities',venue='Nasdaq'),
    _s('AMZN','Amazon','Equities',venue='Nasdaq'),
    _s('GOOGL','Alphabet','Equities',venue='Nasdaq',aliases='Google'),
    _s('META','Meta Platforms','Equities',venue='Nasdaq'),
    _s('JPM','JPMorgan Chase','Equities',venue='NYSE'),
    _s('BNP','BNP Paribas','Equities','BNP.PA',currency='EUR',venue='Euronext Paris',region='Europe',timezone='Europe/Paris'),
    _s('LVMH','LVMH','Equities','MC.PA',currency='EUR',venue='Euronext Paris',region='Europe',timezone='Europe/Paris'),
    _s('SPX','S&P 500','Indexes','^GSPC',venue='S&P DJI',unit='index',aliases='SP500 S&P500'),
    _s('NDX','Nasdaq 100','Indexes','^NDX',venue='Nasdaq',unit='index'),
    _s('DJI','Dow Jones','Indexes','^DJI',venue='S&P DJI',unit='index'),
    _s('SX5E','Euro Stoxx 50','Indexes','^STOXX50E',currency='EUR',venue='STOXX',region='Europe',timezone='Europe/Berlin',unit='index'),
    _s('CAC','CAC 40','Indexes','^FCHI',currency='EUR',venue='Euronext Paris',region='Europe',timezone='Europe/Paris',unit='index'),
    _s('DAX','DAX','Indexes','^GDAXI',currency='EUR',venue='Xetra',region='Europe',timezone='Europe/Berlin',unit='index'),
    _s('FTSE','FTSE 100','Indexes','^FTSE',currency='GBP',venue='FTSE Russell',region='Europe',timezone='Europe/London',unit='index'),
    _s('NIKKEI','Nikkei 225','Indexes','^N225',currency='JPY',venue='Tokyo',region='Asia-Pacific',timezone='Asia/Tokyo',unit='index'),
    _s('HSI','Hang Seng','Indexes','^HSI',currency='HKD',venue='Hong Kong',region='Asia-Pacific',timezone='Asia/Hong_Kong',unit='index'),
    _s('VIX','Cboe VIX','Volatility','^VIX',venue='Cboe',unit='vol_index',aliases='volatility'),
    *[_s(id,name,'FX',symbol,currency=currency,venue='OTC indicative',unit='fx',region='Global',timezone='UTC',aliases=id)
      for id,name,symbol,currency in [('EURUSD','EUR/USD','EURUSD=X','USD'),('GBPUSD','GBP/USD','GBPUSD=X','USD'),
      ('USDJPY','USD/JPY','JPY=X','JPY'),('USDCHF','USD/CHF','CHF=X','CHF'),('AUDUSD','AUD/USD','AUDUSD=X','USD'),('USDCAD','USD/CAD','CAD=X','CAD')]],
    *[_s(id,name,'Rates',symbol,provider='US Treasury · daily par yield curve',unit='yield',venue='Daily Treasury par yield')
      for id,name,symbol in [('US2Y','US 2Y','DGS2'),('US5Y','US 5Y','DGS5'),('US10Y','US 10Y','DGS10'),('US30Y','US 30Y','DGS30')]],
    _s('DE10Y','Germany 10Y · monthly average','Rates','IRLTLT01DEM156N',currency='EUR',provider='FRED / OECD',unit='yield',venue='Monthly benchmark',region='Europe',timezone='Europe/Berlin',aliases='Bund German 10Y'),
    *[_s(id,name,'Commodities',symbol,venue='Futures · continuous front contract',unit=unit,region='Global')
      for id,name,symbol,unit in [('GOLD','Gold futures','GC=F','USD / troy oz'),('SILVER','Silver futures','SI=F','USD / troy oz'),
      ('BRENT','Brent futures','BZ=F','USD / barrel'),('WTI','WTI futures','CL=F','USD / barrel'),('COPPER','Copper futures','HG=F','USD / lb'),('WHEAT','Wheat futures','ZW=F','US cents / bushel')]],
    *[_s(id,name,'ETFs',venue='NYSE Arca / Nasdaq') for id,name in [('SPY','SPDR S&P 500 ETF'),('QQQ','Invesco QQQ'),('IWM','iShares Russell 2000 ETF'),('TLT','iShares 20+ Year Treasury ETF'),('HYG','iShares High Yield Corporate Bond ETF'),('GLD','SPDR Gold Shares')]],
    _s('BTC','Bitcoin / USD','Crypto','BTC-USD',venue='Composite indicative',region='Global',unit='crypto',timezone='UTC'),
    _s('ETH','Ethereum / USD','Crypto','ETH-USD',venue='Composite indicative',region='Global',unit='crypto',timezone='UTC'),
]
SECURITIES = {s.id:s for s in DIRECTORY}
ASSET_GROUPS = ('Overview','Equities','Indexes','FX','Rates','Commodities','ETFs','Volatility','Crypto')
TICKER_IDS = ('SPX','NDX','SX5E','CAC','DAX','FTSE','NIKKEI','VIX','EURUSD','GBPUSD','USDJPY','US10Y','DE10Y','GOLD','BRENT','WTI','BTC')


def search_securities(query):
    query = re.sub(r'[^a-z0-9]', '', str(query).lower())
    if not query:
        return list(DIRECTORY)
    return sorted((s for s in DIRECTORY if query in re.sub(r'[^a-z0-9]', '', f'{s.id} {s.name} {s.symbol} {s.aliases}'.lower())),
                  key=lambda s: (re.sub(r'[^a-z0-9]', '',s.id.lower()) != query,s.name))


def peers(security, limit=6):
    return [s.id for s in DIRECTORY if s.asset_class==security.asset_class and s.id!=security.id][:limit]
