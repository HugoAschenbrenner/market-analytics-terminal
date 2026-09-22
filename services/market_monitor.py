"""V2 public market service: bounded reads, shared cache, stale last-success fallback.

This intentionally never imports the synthetic book-context adapter. Quotes,
daily charts and daily analytics share the same per-security raw chart request.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from io import StringIO
from threading import RLock
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import json
import ssl
import certifi
import numpy as np
import pandas as pd
import streamlit as st
from core.securities import SECURITIES
from core.market_contracts import Quote, HistoricalPrices, DataResult, Fundamentals
from core.market_formatting import finite

UTC=timezone.utc


def request_text(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (Market Analytics Terminal research)','Accept':'application/json,text/csv,application/xml;q=0.9,*/*;q=0.8'})
    with urlopen(req,timeout=6,context=ssl.create_default_context(cafile=certifi.where())) as response:
        content=response.read(5_000_001)
    if len(content)>5_000_000:raise ValueError('Provider response too large')
    return content.decode('utf-8-sig')


class MarketCache:
    """Single-flight per key, bounded in-memory cache shared across sessions.

    Successful observations survive failures without changing their timestamps.
    Failed attempts are cached for one minute. There are no automatic retries.
    """
    def __init__(self, clock=None, capacity=256):
        self.clock=clock or (lambda:datetime.now(UTC))
        self.capacity=capacity
        self.entries={}
        self.lock=RLock()
        self.stripes=[RLock() for _ in range(32)]

    def get(self,key,loader,ttl=300):
        with self.stripes[hash(key)%len(self.stripes)]:
            now=self.clock()
            with self.lock:old=self.entries.get(key)
            wait=60 if old and old.status in ('stale','unavailable') else ttl
            if old and (now-old.attempted_at).total_seconds()<wait:
                return replace(old,status='cached' if old.status in ('fresh','cached') else old.status)
            try:
                value=loader()
                if value is None:raise ValueError('No observation')
                result=DataResult(value,'fresh',now,now)
            except Exception:
                # Boundary around untrusted provider payloads; never expose their
                # response bodies, exceptions or credentials in the application.
                result=DataResult(old.value if old else None,'stale' if old and old.value is not None else 'unavailable',
                                  old.retrieved_at if old else None,now,'Provider unavailable; last successful data retained.' if old and old.value is not None else 'No verified observation available.')
            with self.lock:
                if key not in self.entries and len(self.entries)>=self.capacity:
                    self.entries.pop(min(self.entries,key=lambda k:self.entries[k].attempted_at))
                self.entries[key]=result
            return result


def parse_chart(payload,security,interval='1d'):
    results=payload.get('chart',{}).get('result')
    if not results:raise ValueError('Empty chart')
    data=results[0];meta=data.get('meta',{})
    timestamps=data.get('timestamp',[])
    raw=data.get('indicators',{}).get('quote',[{}])[0]
    frame=pd.DataFrame({col:raw.get(col,[None]*len(timestamps)) for col in ('open','high','low','close','volume')},index=pd.to_datetime(timestamps,unit='s',utc=True))
    frame=frame.apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan).sort_index()
    frame=frame.loc[~frame.index.duplicated(keep='last')]
    frame=frame.loc[(frame.close>0)&(frame.index<=pd.Timestamp.now(tz='UTC')+pd.Timedelta(minutes=5))]
    adjusted=data.get('indicators',{}).get('adjclose',[{}])[0].get('adjclose')
    if adjusted is not None:
        adj=pd.Series(adjusted,index=pd.to_datetime(timestamps,unit='s',utc=True))
        adj=adj.loc[~adj.index.duplicated(keep='last')]
        frame['adjusted_close']=pd.to_numeric(adj,errors='coerce').reindex(frame.index)
        frame.loc[frame.adjusted_close<=0,'adjusted_close']=np.nan
    else:frame['adjusted_close']=np.nan
    if frame.empty:raise ValueError('No valid price history')
    return frame,meta,data.get('events',{})


def parse_fred(text,security):
    frame=pd.read_csv(StringIO(text),na_values=['.'])
    series=pd.Series(pd.to_numeric(frame[security.symbol],errors='coerce').to_numpy(),index=pd.to_datetime(frame.iloc[:,0],utc=True,errors='coerce'))
    series=series[~series.index.isna()].replace([np.inf,-np.inf],np.nan).dropna().sort_index()
    series=series[~series.index.duplicated(keep='last')]
    series=series[(series.index<=pd.Timestamp.now(tz='UTC'))&(series.abs()<=100)]
    if series.empty:raise ValueError('No yield observations')
    return pd.DataFrame({'close':series,'adjusted_close':series}),{},{}


def chart_quote(security,chart):
    frame,meta,_=chart
    price=meta.get('regularMarketPrice');epoch=meta.get('regularMarketTime')
    observed=datetime.fromtimestamp(epoch,UTC) if finite(epoch) else frame.index[-1].to_pydatetime()
    if not finite(price) or price<=0 or observed>datetime.now(UTC)+timedelta(minutes=5):
        price=float(frame.close.iloc[-1]);observed=frame.index[-1].to_pydatetime()
    if security.unit=='yield':
        price=float(frame.close.iloc[-1]);observed=frame.index[-1].to_pydatetime()
    local_dates=frame.index.tz_convert(security.timezone).date if security.unit!='yield' else frame.index.date
    current_date=observed.astimezone(__import__('zoneinfo').ZoneInfo(security.timezone)).date() if security.unit!='yield' else observed.date()
    earlier=frame.loc[local_dates<current_date,'close']
    # chartPreviousClose describes the beginning of a requested range, not
    # necessarily yesterday. Never use it for a five-year daily move.
    previous=float(earlier.iloc[-1]) if len(earlier) else meta.get('previousClose',meta.get('regularMarketPreviousClose'))
    if not finite(previous):previous=None
    stats={k:meta.get(k) for k in ('fiftyTwoWeekHigh','fiftyTwoWeekLow','regularMarketVolume','exchangeName','fullExchangeName')}
    for key in ('open','high','low','volume'):
        stats[key]=float(frame[key].iloc[-1]) if key in frame and finite(frame[key].iloc[-1]) else None
    stats['averageVolume']=float(frame.volume.tail(63).mean()) if 'volume' in frame else None
    freq='monthly average' if security.id=='DE10Y' else 'daily observation' if security.unit=='yield' else 'delayed / indicative'
    return Quote(security.id,float(price),float(previous) if finite(previous) else None,observed,
                 meta.get('currency',security.currency),meta.get('source',security.provider),freq,stats,meta.get('currentTradingPeriod',{}).get('regular',{}))


class MarketService:
    def __init__(self,cache=None):
        self.cache=cache or MarketCache()
        self.fundamental_pool=ThreadPoolExecutor(max_workers=2)
        self.fundamental_jobs={}
        self.fundamental_lock=RLock()

    def treasury(self,id,period):
        from engines.rates_market_data_engine import parse_treasury_yield_curve_xml
        year=datetime.now(UTC).year
        years=range(year-(5 if period=='5Y' else 1),year+1)
        def get_year(year):
            url='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?'+urlencode({'data':'daily_treasury_yield_curve','field_tdr_date_value':year})
            def load():
                records=parse_treasury_yield_curve_xml(request_text(url))
                if not records:raise ValueError('Empty Treasury history')
                return records
            return self.cache.get(('treasury',year),load,ttl=3600 if year==datetime.now(UTC).year else 86400)
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(get_year,years))
        records=[row for result in results for row in (result.value or [])]
        if not records:return DataResult(message='Treasury history unavailable.')
        tenor=id[2:]
        frame=pd.DataFrame(records)
        if tenor not in frame:return DataResult(message='Treasury tenor unavailable.')
        values=pd.Series(pd.to_numeric(frame[tenor],errors='coerce').to_numpy(),index=pd.to_datetime(frame['date'],utc=True))
        values=values.sort_index().dropna();values=values[~values.index.duplicated(keep='last')]
        values=values[(values.index<=pd.Timestamp.now(tz='UTC'))&(values.abs()<=100)]
        if values.empty:return DataResult(message='Treasury observations unavailable.')
        status='stale' if any(r.status in ('unavailable','stale') for r in results) else 'cached' if all(r.status=='cached' for r in results) else 'fresh'
        dates=[r.retrieved_at for r in results if r.retrieved_at]
        return DataResult((pd.DataFrame({'close':values,'adjusted_close':values}),{'source':'US Treasury · daily par yield curve'},{}),status,min(dates),datetime.now(UTC))

    def raw_chart(self,id,period='1Y'):
        security=SECURITIES[id]
        if security.unit=='yield' and id.startswith('US'):return self.treasury(id,period)
        # One full daily resource serves quotes, charts and return analytics.
        intraday=period in ('1D','5D') and security.unit!='yield'
        interval='5m' if intraday else '1d'
        def load():
            if security.unit=='yield':
                url='https://fred.stlouisfed.org/graph/graph.csv?'+urlencode({'id':security.symbol,'cosd':(datetime.now(UTC)-timedelta(days=6*366)).date().isoformat()})
                return parse_fred(request_text(url),security)
            params=urlencode({'range':'5d' if intraday else '5y','interval':interval,'events':'div,splits','includeAdjustedClose':'true'})
            url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(security.symbol,safe='')+'?'+params
            return parse_chart(json.loads(request_text(url)),security,interval)
        return self.cache.get(('chart',id,interval),load,ttl=3600 if security.unit=='yield' else 300)

    def quote(self,id):
        result=self.raw_chart(id)
        if result.value is None:return result
        try:return replace(result,value=chart_quote(SECURITIES[id],result.value))
        except (ValueError,TypeError,IndexError,OverflowError):return DataResult(message='Invalid quote from provider.')

    def quotes(self,ids):
        ids=tuple(dict.fromkeys(id for id in ids if id in SECURITIES))
        with ThreadPoolExecutor(max_workers=6) as pool:
            return dict(zip(ids,pool.map(self.quote,ids)))

    def history(self,id,period='1Y'):
        result=self.raw_chart(id,period)
        if result.value is None:return result
        frame=result.value[0].copy()
        interval='5m' if period in ('1D','5D') and SECURITIES[id].unit!='yield' else '1d'
        now=pd.Timestamp.now(tz='UTC')
        if period=='1D' and interval=='5m':
            dates=frame.index.tz_convert(SECURITIES[id].timezone).date
            frame=frame.loc[dates==dates[-1]]
        elif period=='YTD':frame=frame.loc[frame.index>=pd.Timestamp(year=now.year,month=1,day=1,tz='UTC')]
        elif period=='5Y':frame=frame.loc[frame.index>=now-pd.DateOffset(years=5)]
        else:frame=frame.loc[frame.index>=now-pd.Timedelta(days={'5D':8,'1D':5,'1M':31,'6M':183,'1Y':366}.get(period,366))]
        return replace(result,value=HistoricalPrices(id,frame,result.value[1].get('source',SECURITIES[id].provider),interval,'adjusted_close' in frame and frame.adjusted_close.notna().any()))

    def fundamentals(self,id):
        def fetch():
            if SECURITIES[id].asset_class not in ('Equities','ETFs'):raise ValueError('Not applicable')
            import yfinance as yf
            info=yf.Ticker(SECURITIES[id].symbol).get_info()
            keys=('longBusinessSummary','country','sector','industry','marketCap','trailingPE','forwardPE','trailingEps','dividendYield','beta','totalRevenue','netIncomeToCommon','earningsTimestamp','exDividendDate','financialCurrency','trailingAnnualDividendRate')
            fields={k:info[k] for k in keys if info.get(k) is not None}
            if not fields:raise ValueError('Empty fundamentals')
            return Fundamentals(id,fields,'Yahoo Finance via yfinance; provider reporting periods')
        def load():
            # Bound UI waiting and background concurrency without altering the
            # yfinance singleton/session configuration used by frozen V1.
            with self.fundamental_lock:
                if id not in self.fundamental_jobs:
                    for key,job in list(self.fundamental_jobs.items()):
                        if job.done():self.fundamental_jobs.pop(key)
                    if len(self.fundamental_jobs)>=2:raise ValueError('Fundamentals busy')
                    self.fundamental_jobs[id]=self.fundamental_pool.submit(fetch)
                future=self.fundamental_jobs[id]
            value=future.result(timeout=8)
            with self.fundamental_lock:self.fundamental_jobs.pop(id,None)
            return value
        return self.cache.get(('fundamentals',id),load,ttl=21600)


@st.cache_resource(show_spinner=False)
def get_market_service():return MarketService()


def observation_is_old(security,quote,now=None):
    now=now or datetime.now(UTC)
    days=65 if security.id=='DE10Y' else 5 if security.unit=='yield' else 3
    return (now-quote.observed_at).total_seconds()>days*86400
