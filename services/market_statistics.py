"""Observed daily-return analytics, with no filling or estimated market inputs."""
from dataclasses import dataclass
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from core.securities import SECURITIES

@dataclass(frozen=True)
class VolatilityMetrics:
    security_id:str
    window:int
    annualized:float|None
    observations:int
    as_of:object
    series:pd.Series
    basis:str


def daily_levels(history,security,now=None):
    frame=history.frame.copy()
    if security.id=='DE10Y':raise ValueError('Monthly average excluded from daily analytics.')
    column='adjusted_close' if security.asset_class in ('Equities','ETFs') else 'close'
    if column not in frame:raise ValueError('Adjusted history unavailable.')
    values=pd.to_numeric(frame[column],errors='coerce').replace([np.inf,-np.inf],np.nan)
    dates=frame.index if security.unit=='yield' else frame.index.tz_convert(security.timezone)
    values.index=pd.DatetimeIndex(dates.date)
    values=values[~values.index.duplicated(keep='last')].sort_index()
    today=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(security.timezone)).date()
    values=values[values.index.date<today]  # Conservative: omit possibly unfinished local day.
    if security.unit!='yield':values=values.where(values>0)
    return values


def correlation_matrix(histories,lookback=60,now=None):
    if lookback not in (20,60,120,252):raise ValueError('Unsupported lookback')
    levels={};excluded={}
    for id,history in histories.items():
        try:
            values=daily_levels(history,SECURITIES[id],now)
            if values.notna().sum()<lookback+1:raise ValueError('Insufficient complete daily history')
            levels[id]=values
        except ValueError as exc:excluded[id]=str(exc)
    if len(levels)<2:return pd.DataFrame(),0,excluded,None
    # Align levels first: returns then cover exactly the same start/end dates.
    aligned=pd.DataFrame(levels).dropna().tail(lookback+1)
    if len(aligned)<lookback+1:return pd.DataFrame(),max(0,len(aligned)-1),excluded,None
    changes={id:(aligned[id].diff()*100 if SECURITIES[id].unit=='yield' else aligned[id].pct_change(fill_method=None)) for id in aligned}
    changes=pd.DataFrame(changes).iloc[1:]
    return changes.corr(min_periods=lookback),len(changes),excluded,aligned.index[-1]


def realized_volatility(history,window=20,now=None):
    s=SECURITIES[history.security_id]
    if window not in (20,60,120,252):raise ValueError('Unsupported window')
    if s.unit in ('yield','vol_index'):raise ValueError('Return volatility is not a yield or implied-vol index level.')
    prices=daily_levels(history,s,now)
    returns=np.log(prices/prices.shift(1)).replace([np.inf,-np.inf],np.nan)
    periods=365 if s.asset_class=='Crypto' else 252
    series=returns.rolling(window,min_periods=window).std(ddof=1)*np.sqrt(periods)
    value=float(series.iloc[-1]) if len(series) and np.isfinite(series.iloc[-1]) else None
    basis=f'log returns · sample standard deviation · √{periods}'
    return VolatilityMetrics(s.id,window,value,int(returns.tail(window).notna().sum()),prices.index[-1] if len(prices) else None,series.dropna(),basis)


def event_move(history,event_date,now=None):
    """Return over the first complete session on/after the event date; no causal claim."""
    s=SECURITIES[history.security_id];values=daily_levels(history,s,now).dropna()
    day=pd.Timestamp(event_date).tz_localize(None).normalize()
    next_values=values[values.index>=day];previous=values[values.index<day]
    if next_values.empty or previous.empty:return None
    return (float(next_values.iloc[0]/previous.iloc[-1]-1),next_values.index[0])
