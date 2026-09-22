from datetime import datetime,timezone
import numpy as np
import pandas as pd
import pytest
from core.market_contracts import HistoricalPrices
from core.securities import SECURITIES
from services.market_statistics import correlation_matrix,realized_volatility,daily_levels,event_move

NOW=datetime(2026,8,1,tzinfo=timezone.utc)
def history(id,values,dates=None,adjusted=None):
    dates=dates if dates is not None else pd.date_range('2025-01-01',periods=len(values),tz='UTC')+pd.Timedelta(hours=19)
    return HistoricalPrices(id,pd.DataFrame({'close':values,'adjusted_close':values if adjusted is None else adjusted},index=dates),'fixture','1d',True)

def test_correlations_use_returns_and_yield_bp_changes():
    changes=np.linspace(-.01,.012,100)**3*1000
    prices=100*np.cumprod(1+changes)
    yields=4+np.cumsum(changes)*100
    matrix,n,_,_=correlation_matrix({'AAPL':history('AAPL',prices),'US10Y':history('US10Y',yields)},60,NOW)
    assert n==60 and matrix.loc['AAPL','US10Y']==pytest.approx(1)

def test_split_adjustment_removes_false_crash_from_realized_vol():
    observed=np.r_[np.full(30,100.),np.full(30,50.)]
    result=realized_volatility(history('NVDA',observed,adjusted=np.full(60,50.)),20,NOW)
    assert result.annualized==0

def test_missing_adjusted_data_is_not_replaced_with_raw_prices():
    result=realized_volatility(history('NVDA',np.arange(60)+100,adjusted=np.full(60,np.nan)),20,NOW)
    assert result.annualized is None

def test_correlations_require_full_common_window_and_omit_monthly_yields():
    matrix,n,excluded,_=correlation_matrix({'AAPL':history('AAPL',np.arange(22)+100),'MSFT':history('MSFT',np.arange(20)+100),'DE10Y':history('DE10Y',np.arange(60))},20,NOW)
    assert matrix.empty and 'DE10Y' in excluded and 'MSFT' in excluded

def test_crypto_annualization_and_no_current_day():
    dates=pd.date_range('2026-06-01',periods=61,tz='UTC')
    values=100*np.exp(np.cumsum(np.sin(np.arange(61))*.01))
    result=realized_volatility(history('BTC',values,dates),20,NOW)
    expected=np.diff(np.log(values))[-20:].std(ddof=1)*np.sqrt(365)
    assert result.annualized==pytest.approx(expected)
    assert result.as_of.date()<NOW.date()

def test_same_interval_alignment_skips_a_missing_common_date():
    a=history('AAPL',np.exp(np.arange(50)*.01+np.sin(np.arange(50))*.05))
    b=history('MSFT',a.frame.close.values*2,a.frame.index).frame.drop(a.frame.index[35])
    matrix,n,_,_=correlation_matrix({'AAPL':a,'MSFT':HistoricalPrices('MSFT',b,'fixture','1d',True)},20,NOW)
    assert n==20 and matrix.loc['AAPL','MSFT']==pytest.approx(1)

def test_event_move_has_no_future_or_missing_reference():
    h=history('AAPL',[100,110,105])
    assert event_move(h,'2025-01-02',NOW)[0]==pytest.approx(.1)
    assert event_move(h,'2027-01-01',NOW) is None
