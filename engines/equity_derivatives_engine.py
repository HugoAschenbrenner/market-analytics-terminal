"""Signed position Greeks and educational, instantaneous hedge comparisons."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from engines.options_pricing_engine import black_scholes_price, black_scholes_greeks
from engines.pnl_explain_engine import pnl_explain
from engines.scenario_engine import MarketScenario


@dataclass(frozen=True)
class OptionPosition:
    option_type: str = 'Call'
    spot: float = 100.
    strike: float = 100.
    maturity: float = .5
    rate: float = .035
    volatility: float = .215
    dividend: float = .01
    quantity: float = 10.
    multiplier: float = 100.

    @property
    def args(self):
        return (self.option_type, self.spot, self.strike, self.maturity, self.rate, self.volatility, self.dividend)

    @property
    def units(self):
        if not np.isfinite([self.quantity,self.multiplier]).all() or self.multiplier <= 0:
            raise ValueError('Quantity must be finite and contract multiplier positive.')
        return self.quantity*self.multiplier


def position_analytics(position: OptionPosition) -> dict:
    p = position
    g = black_scholes_greeks(*p.args)
    units = p.units
    return dict(price=black_scholes_price(*p.args), position_value=black_scholes_price(*p.args)*units,
        position_delta=g['delta']*units, cash_delta=g['delta']*units*p.spot,
        position_gamma=g['gamma']*units, cash_gamma=g['gamma']*units*p.spot**2,
        gamma_pnl_1pct=.5*g['gamma']*units*(.01*p.spot)**2,
        vega_1vol_point=g['vega_1pct']*units, theta_daily=g['theta_daily']*units,
        rho_1pct=g['rho_1pct']*units, **{'unit_'+k:v for k,v in g.items()})


def option_scenario(position: OptionPosition, scenario: MarketScenario) -> dict:
    p = position
    if scenario.elapsed_days >= p.maturity*365:
        raise ValueError('Time passage must be strictly before expiry.')
    if p.volatility+scenario.volatility <= 0:
        raise ValueError('Shocked volatility must remain strictly positive.')
    result = pnl_explain(p.option_type,p.spot,p.strike,p.maturity,p.rate,p.volatility,
        ds=p.spot*scenario.equity,dv=scenario.volatility,days=scenario.elapsed_days,
        dr=float(scenario.rate_at(p.maturity))/10000,units=p.units,dividend=p.dividend,advanced=False)
    parts = {key:result['parts'][key] for key in ('delta','gamma','vega','theta','rates')}
    return dict(parts=parts, approximation=result['approximation'], full=result['full'],
                residual=result['parts']['residual'])


def scenario_matrix(position: OptionPosition, spot_shocks=None, vol_points=None) -> pd.DataFrame:
    spots = np.asarray(spot_shocks if spot_shocks is not None else [-.15,-.10,-.05,0,.05,.10,.15],float)
    vols = np.asarray(vol_points if vol_points is not None else [-10,-5,0,5,10],float)
    if spots.ndim != 1 or vols.ndim != 1 or not len(spots) or not len(vols) or len(spots)*len(vols)>1000 or not np.isfinite([*spots,*vols]).all() or (spots<=-1).any():
        raise ValueError('Finite one-dimensional shock grids of at most 1000 cells are required; spot shocks must exceed -100%.')
    records=[]
    base = black_scholes_price(*position.args)
    for vol in vols:
        for spot in spots:
            valid = position.volatility+vol/100 > 0
            value = (black_scholes_price(position.option_type,position.spot*(1+spot),position.strike,
                position.maturity,position.rate,position.volatility+vol/100,position.dividend)-base)*position.units if valid else None
            records.append(dict(spot_shock=spot,vol_points=vol,pnl=value,status='valid' if valid else 'invalid: volatility must stay positive'))
    return pd.DataFrame(records)


def delta_hedge(position: OptionPosition, scenario: MarketScenario) -> dict:
    """Instantaneous shock: no elapsed time, financing, dividend cash flows or costs."""
    if scenario.elapsed_days:
        raise ValueError('Static hedge comparison requires zero elapsed days.')
    p = position
    analytics = position_analytics(p)
    shares = -analytics['position_delta']
    option_pnl = option_scenario(p,scenario)['full']
    hedge_pnl = shares*p.spot*scenario.equity
    new_g = black_scholes_greeks(p.option_type,p.spot*(1+scenario.equity),p.strike,p.maturity,
        p.rate+float(scenario.rate_at(p.maturity))/10000,p.volatility+scenario.volatility,p.dividend)
    new_option_delta = new_g['delta']*p.units
    return dict(hedge_units=shares,hedge_cash_value=shares*p.spot,
        remaining_gamma=analytics['position_gamma'],remaining_vega=analytics['vega_1vol_point'],remaining_theta=analytics['theta_daily'],
        option_pnl=option_pnl,unhedged_pnl=option_pnl,hedge_pnl=hedge_pnl,net_pnl=option_pnl+hedge_pnl,
        new_option_delta=new_option_delta,new_net_delta=new_option_delta+shares,rebalance_units=-(new_option_delta+shares))


def greek_grid(position: OptionPosition, metric: str = 'gamma') -> pd.DataFrame:
    if metric not in ('delta','gamma','vega_1pct'):
        raise ValueError('Choose delta, gamma or vega_1pct.')
    spots = np.linspace(.7*position.spot,1.3*position.spot,25)
    maturities = np.linspace(max(.005,position.maturity*.02),position.maturity*1.5,20)
    return pd.DataFrame([[black_scholes_greeks(position.option_type,s,position.strike,t,position.rate,
        position.volatility,position.dividend)[metric] for s in spots] for t in maturities],index=maturities,columns=spots)
