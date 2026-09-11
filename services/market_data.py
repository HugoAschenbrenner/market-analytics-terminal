"""Bounded public-data reads and explicit synthetic fallback. No credentials required."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone, timedelta
from io import StringIO
import json
import ssl
import certifi
from urllib.request import Request, urlopen
from urllib.parse import quote
import numpy as np
import pandas as pd
import streamlit as st

TENORS = [1,2,5,10,30]
SYMBOLS = {'SPY':'SPY','QQQ':'QQQ','VIX':'^VIX','EURUSD':'EURUSD=X','GBPUSD':'GBPUSD=X','USDJPY':'JPY=X'}

def read_url(url):
    request=Request(url,headers={'User-Agent':'MarketAnalyticsTerminal/2.0','Accept':'text/csv,application/json;q=0.9,*/*;q=0.8'})
    with urlopen(request,timeout=5,context=ssl.create_default_context(cafile=certifi.where())) as response:
        return response.read(5_000_000).decode('utf-8')

def parse_fred_csv(text):
    frame=pd.read_csv(StringIO(text),na_values=['.'])
    frame=frame.rename(columns={frame.columns[0]:'date',**{f'DGS{y}':y for y in TENORS}})
    frame['date']=pd.to_datetime(frame['date'],errors='coerce')
    return clean_curve(frame.set_index('date')[TENORS])

def parse_ecb_csv(text):
    frame=pd.read_csv(StringIO(text))
    frame['date']=pd.to_datetime(frame['TIME_PERIOD'],errors='coerce')
    series=frame['DATA_TYPE_FM'] if 'DATA_TYPE_FM' in frame else frame['KEY'].str.split('.').str[-1]
    frame['tenor']=series.str.extract(r'SR_(\d+)Y')[0].astype(float)
    frame['value']=pd.to_numeric(frame['OBS_VALUE'],errors='coerce')
    return clean_curve(frame.pivot(index='date',columns='tenor',values='value').reindex(columns=TENORS))

def clean_curve(frame):
    frame=frame.apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan)
    frame=frame.loc[~frame.index.isna()].sort_index().dropna()
    frame=frame.loc[frame.index<=pd.Timestamp(date.today())]
    if len(frame)<2 or frame.index.duplicated().any():
        raise ValueError('Invalid curve history')
    if (frame.abs()>100).any().any():
        raise ValueError('Curve units must be annual percent')
    return frame.tail(756)

def synthetic_curve(currency):
    rng=np.random.default_rng(72 if currency=='USD' else 73)
    dates=pd.bdate_range(end=date.today()-timedelta(days=1),periods=504)
    x=np.linspace(-1,1,len(TENORS))
    changes=rng.normal(size=(len(dates),3))@np.vstack([np.ones(5)*.025,x*.012,(x*x-.5)*.01])
    paths=changes.cumsum(axis=0)
    last=np.array([4.1,4.0,3.9,4.1,4.5]) if currency=='USD' else np.array([2.4,2.5,2.7,2.9,3.1])
    return pd.DataFrame(paths-paths[-1]+last,index=dates,columns=TENORS)

def fetch_curve(currency):
    start=(date.today()-timedelta(days=1100)).isoformat()
    if currency=='USD':
        url=f'https://fred.stlouisfed.org/graph/graph.csv?id=DGS1,DGS2,DGS5,DGS10,DGS30&cosd={start}'
        history=parse_fred_csv(read_url(url)); provider='Federal Reserve H.15 / FRED'; basis='constant_maturity'
    else:
        url='https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y+SR_2Y+SR_5Y+SR_10Y+SR_30Y?format=csvdata&startPeriod='+start
        history=parse_ecb_csv(read_url(url)); provider='ECB AAA'; basis='zero_coupon'
    return {'history':history,'source':'PUBLIC','provider':provider,'as_of':history.index[-1].date().isoformat(),'basis':basis,'url':url}

def fetch_quote(symbol):
    payload=json.loads(read_url('https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?range=5d&interval=1d'))
    result=payload['chart']['result'][0]
    prices=result['indicators']['quote'][0]['close']
    latest=float(prices[-1])
    if not np.isfinite(latest) or latest<=0:
        raise ValueError('Invalid latest close')
    prior=prices[-2] if len(prices)>1 else None
    change=(latest/float(prior)-1) if prior is not None and np.isfinite(prior) and prior>0 else None
    return {'price':latest,'change':change,'source':'PUBLIC','provider':'Yahoo Finance',
            'as_of':datetime.fromtimestamp(result['timestamp'][-1],timezone.utc).isoformat(),'basis':'daily_bar_last'}

@st.cache_data(ttl=900,show_spinner=False,max_entries=4)
def load_public_context(refresh=0):
    def safe(kind,key):
        try:
            return fetch_curve(key) if kind=='curve' else fetch_quote(SYMBOLS[key])
        except (OSError,ValueError,TypeError,KeyError,IndexError):
            return None
    tasks=[('curve','USD'),('curve','EUR')]+[('quote',key) for key in SYMBOLS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda task:safe(*task),tasks))
    return dict(zip(tasks,results))

def ensure_market(state,refresh=False):
    if state.market.curves and not refresh:
        return
    public=load_public_context(state.market.revision+int(refresh))
    for currency in ('USD','EUR'):
        result=public.get(('curve',currency))
        if result is None:
            result=state.market.curves.get(currency)
        if result is None:
            history=synthetic_curve(currency)
            result={'history':history,'source':'SYNTHETIC','provider':'demo','as_of':history.index[-1].date().isoformat(),'basis':'constant_maturity' if currency=='USD' else 'zero_coupon'}
        state.market.curves[currency]=result
    defaults={'SPY':550.,'QQQ':475.,'VIX':20.,'EURUSD':1.10,'GBPUSD':1.28,'USDJPY':147.}
    for ticker,value in defaults.items():
        previous=state.market.provenance.get(ticker,{})
        observation=previous if previous.get('source')=='USER INPUT' else public.get(('quote',ticker))
        if observation is None:
            observation=state.market.provenance.get(ticker,{'price':value,'change':None,'source':'SYNTHETIC','provider':'demo','as_of':'2026-09-09','basis':'daily_bar_last'})
        state.market.provenance[ticker]=observation
        state.market.spots[ticker]=observation['price']
    state.market.fx.update(EUR=state.market.spots['EURUSD'],GBP=state.market.spots['GBPUSD'],JPY=1/state.market.spots['USDJPY'])
    sources={item['source'] for item in [*state.market.curves.values(),*state.market.provenance.values()]}
    state.market.source=next(iter(sources)) if len(sources)==1 else 'MIXED'
    state.market.as_of=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    state.market.revision+=1
    state.risk.results.clear()

def curve_overlay(payload,days=0):
    history=payload['history']
    cutoff=history.index[-1]-pd.Timedelta(days=days)
    eligible=history.loc[history.index<=cutoff]
    return None if eligible.empty else eligible.iloc[-1]
