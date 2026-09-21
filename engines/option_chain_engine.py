"""European option chains: explicit inputs, IV diagnostics and empirical interpolation.

Volatility/rates are decimals, maturities ACT/365, moneyness K/S. No feed or
surface calibration is implied. Smile interpolation never extrapolates.
"""
from dataclasses import dataclass
from datetime import date
from math import exp, isfinite

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from engines.options_pricing_engine import (
    black_scholes_price, black_scholes_greeks, validate_black_scholes_inputs,
)


@dataclass(frozen=True)
class IVResult:
    volatility: float | None
    status: str
    message: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    price_error: float | None = None
    iterations: int = 0


def solve_implied_volatility(market_price: float, option_type: str, spot: float,
                             strike: float, maturity: float, rate: float,
                             dividend: float = 0.) -> IVResult:
    """Invert existing BSM with Brent's method; failures are explicit results."""
    try:
        inputs = validate_black_scholes_inputs(option_type, spot, strike, maturity, rate, .2, dividend)
        spot, strike, maturity, rate, dividend = (inputs.spot, inputs.strike,
            inputs.maturity_years, inputs.risk_free_rate, inputs.dividend_yield)
        observed = float(market_price)
        if not isfinite(observed):
            raise ValueError('Option price must be finite.')
        prepaid, discounted_strike = spot * exp(-dividend*maturity), strike * exp(-rate*maturity)
        lower = max(0., prepaid-discounted_strike) if inputs.option_type == 'Call' else max(0., discounted_strike-prepaid)
        upper = prepaid if inputs.option_type == 'Call' else discounted_strike
        if not isfinite(upper):
            raise ValueError('Discounted inputs overflow.')
        if observed < lower or observed >= upper:
            return IVResult(None, 'out_of_bounds', 'Price is outside the finite-volatility European bounds.', lower, upper)
        if observed == lower:
            return IVResult(0., 'lower_bound', 'Zero-volatility limit; rounded deep-ITM/OTM quotes may not identify IV.', lower, upper, 0.)
        def objective(vol):
            return (lower if vol == 0 else black_scholes_price(inputs.option_type, spot, strike, maturity, rate, vol, dividend)) - observed
        high = 1.
        while objective(high) < 0 and high < 64:
            high *= 2
        if objective(high) < 0:
            return IVResult(None, 'not_bracketed', 'No root up to 6400% annual volatility.', lower, upper)
        vol, result = brentq(objective, 0., high, xtol=1e-12, rtol=1e-12, full_output=True)
        error = objective(vol)
        return IVResult(float(vol), 'solved', 'Brent root using the existing BSM pricer.', lower, upper, float(error), result.iterations)
    except (ValueError, TypeError, OverflowError, RuntimeError) as exc:
        return IVResult(None, 'invalid_input', str(exc))


def sample_option_chain() -> pd.DataFrame:
    """Fixed 2026-09-09 educational smile; no claim of observed quotations."""
    rows = []
    for days in (30, 91, 182, 365):
        maturity = (pd.Timestamp('2026-09-09') + pd.Timedelta(days=days)).date().isoformat()
        years = days/365
        for moneyness in np.linspace(.65, 1.4, 16):
            vol = .21 - .12*np.log(moneyness) + .18*np.log(moneyness)**2 + .025*(np.sqrt(years)-.5)
            for kind in ('Call', 'Put'):
                rows.append(dict(underlying='DEMO', spot=100., maturity=maturity, strike=100*moneyness,
                    option_type=kind, rate=.035, dividend=.01, implied_volatility=vol,
                    market_price=black_scholes_price(kind, 100., 100*moneyness, years, .035, vol, .01)))
    return pd.DataFrame(rows)


def analyze_option_chain(data: pd.DataFrame, as_of: date | str, mode: str = 'price') -> dict:
    """Analyze one underlying; rejected rows remain in a separate diagnostic table."""
    required = {'underlying', 'spot', 'maturity', 'strike', 'option_type',
                'market_price' if mode == 'price' else 'implied_volatility'}
    if mode not in ('price', 'iv') or not required.issubset(data.columns) or data.empty or len(data) > 2000:
        raise ValueError('Supply 1–2000 rows with underlying, spot, maturity, strike, option_type and market_price or implied_volatility.')
    valuation = pd.Timestamp(as_of).normalize()
    if pd.isna(valuation):
        raise ValueError('A valid valuation date is required.')
    frame = data.copy()
    for name, default in [('rate', .035), ('dividend', .01)]:
        if name not in frame:
            frame[name] = default
    for name in ('underlying', 'spot', 'rate', 'dividend'):
        if frame[name].nunique(dropna=False) != 1:
            raise ValueError(f'One chain must use a single {name}; separate underlyings and input conventions.')
    accepted, rejected, seen = [], [], set()
    for index, row in frame.iterrows():
        diagnostic = None
        try:
            expiry = pd.Timestamp(row.maturity).normalize()
            years = (expiry-valuation).days / 365
            inputs = validate_black_scholes_inputs(row.option_type, row.spot, row.strike, years, row.rate, .2, row.dividend)
            if pd.isna(expiry) or pd.isna(row.underlying) or not str(row.underlying).strip():
                raise ValueError('Expiry and underlying are required.')
            key = (expiry, inputs.strike, inputs.option_type)
            if key in seen:
                raise ValueError('Duplicate maturity/strike/type quote.')
            seen.add(key)
            args = (inputs.option_type, inputs.spot, inputs.strike, years, inputs.risk_free_rate)
            diagnostic = solve_implied_volatility(row.market_price, *args, inputs.dividend_yield) if mode == 'price' else None
            vol = diagnostic.volatility if diagnostic else float(row.implied_volatility)
            if vol is None or not isfinite(vol) or vol <= 0:
                raise ValueError(diagnostic.message if diagnostic else 'IV must be a strictly positive decimal.')
            price = black_scholes_price(*args, vol, inputs.dividend_yield)
            greeks = black_scholes_greeks(*args, vol, inputs.dividend_yield)
            accepted.append(dict(underlying=str(row.underlying), spot=inputs.spot, maturity=expiry.date().isoformat(),
                time_to_maturity=years, strike=inputs.strike, moneyness=inputs.strike/inputs.spot,
                option_type=inputs.option_type, rate=inputs.risk_free_rate, dividend=inputs.dividend_yield,
                market_price=float(row.market_price) if mode == 'price' else None, model_price=price,
                implied_volatility=vol, iv_method=diagnostic.status if diagnostic else 'user_iv',
                delta=greeks['delta'], gamma=greeks['gamma'], vega_1vol_point=greeks['vega_1pct'],
                theta_daily=greeks['theta_daily'], rho_1pct=greeks['rho_1pct']))
        except (ValueError, TypeError, OverflowError) as exc:
            rejected.append({'row': str(index), 'reason': str(exc),
                'iv_status': diagnostic.status if diagnostic else 'invalid_input',
                'lower_price_bound': diagnostic.lower_bound if diagnostic else None,
                'upper_price_bound': diagnostic.upper_bound if diagnostic else None})
    return {'chain': pd.DataFrame(accepted), 'rejected': pd.DataFrame(rejected, columns=['row', 'reason', 'iv_status', 'lower_price_bound', 'upper_price_bound']),
            'as_of': valuation.date().isoformat(), 'mode': mode}


def empirical_smile(chain: pd.DataFrame) -> pd.DataFrame:
    """Put below forward, call at/above forward; no averaging disparate IV quotes."""
    if chain.empty:
        return chain.copy()
    forward = chain.spot * np.exp((chain.rate-chain.dividend)*chain.time_to_maturity)
    preferred = np.where(chain.strike < forward, 'Put', 'Call')
    frame = chain.assign(preferred=chain.option_type.eq(preferred))
    return frame.sort_values('preferred', ascending=False).drop_duplicates(['maturity','strike']).sort_values(['time_to_maturity','strike']).drop(columns='preferred')


def interpolate_iv(frame: pd.DataFrame, column: str, target: float) -> tuple[float | None, str]:
    if frame.empty:
        return None, 'unavailable: no observations'
    points = frame.groupby(column).implied_volatility.mean().sort_index()
    x = points.index.to_numpy(float)
    if target < x[0]-1e-12 or target > x[-1]+1e-12:
        return None, 'unavailable: target outside observations (no extrapolation)'
    exact = np.flatnonzero(np.isclose(x, target, rtol=0, atol=1e-12))
    if len(exact):
        return float(points.iloc[exact[0]]), 'observed'
    return float(np.interp(target, x, points)), f'linear interpolation in {column}'


def smile_metrics(chain: pd.DataFrame) -> dict:
    if chain.empty or chain.maturity.nunique() != 1:
        raise ValueError('Select one non-empty maturity.')
    smile = empirical_smile(chain)
    values, methods = {}, {}
    for name, frame, column, target in [
        ('atm_iv', smile, 'moneyness', 1.), ('downside_iv', smile, 'moneyness', .9),
        ('upside_iv', smile, 'moneyness', 1.1),
        ('put25_iv', chain[chain.option_type.eq('Put')], 'delta', -.25),
        ('call25_iv', chain[chain.option_type.eq('Call')], 'delta', .25)]:
        values[name], methods[name] = interpolate_iv(frame, column, target)
    for name, a, b in [('downside_skew', 'downside_iv', 'atm_iv'), ('upside_wing', 'upside_iv', 'atm_iv'),
                       ('risk_reversal_25', 'call25_iv', 'put25_iv'), ('put_skew_25', 'put25_iv', 'call25_iv')]:
        values[name] = values[a]-values[b] if values[a] is not None and values[b] is not None else None
    return {**values, 'methods': methods}


def term_structure(chain: pd.DataFrame) -> dict:
    records = []
    for maturity, frame in chain.groupby('maturity', sort=True):
        iv, method = interpolate_iv(empirical_smile(frame), 'moneyness', 1.)
        records.append(dict(maturity=maturity, time_to_maturity=frame.time_to_maturity.iloc[0], atm_iv=iv, method=method))
    frame = pd.DataFrame(records).sort_values('time_to_maturity')
    frame['change_vol_points'] = frame.atm_iv.diff()*100
    usable = frame.dropna(subset=['atm_iv'])
    if len(usable) < 2:
        shape = 'insufficient maturities'
    else:
        differences = np.diff(usable.atm_iv)
        shape = 'approximately flat' if np.ptp(usable.atm_iv) <= .005 else 'upward-sloping' if (differences >= -.001).all() else 'downward-sloping' if (differences <= .001).all() else 'mixed / humped'
    return {'data': frame, 'shape': shape}
