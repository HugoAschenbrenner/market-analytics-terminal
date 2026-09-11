"""Hypothetical cross-asset shocks. Economic P&L and liquidity remain separate."""
from dataclasses import dataclass,field
import numpy as np
import pandas as pd
from engines.options_pricing_engine import black_scholes_price

@dataclass(frozen=True)
class DeskScenario:
    name: str
    equity: float=0.
    fx: float=0.  # common move in non-base currencies versus the selected base
    rates: tuple=(0.,0.,0.,0.,0.)  # 1,2,5,10,30 years; bp
    credit: float=0.  # bp
    volatility: float=0.  # annual decimal volatility
    correlation: float=0.
    haircut: float=0.
    collateral: float=0.

PRESETS=[DeskScenario('risk_off',-.15,.05,(-25,-35,-40,-35,-20),100,.10,.15,.05,-.10),
         DeskScenario('rates_selloff',-.05,0,(100,100,100,100,100),25,.02,0,.02,-.05),
         DeskScenario('bull_steepener',0,0,(-100,-80,-50,-25,-10)),
         DeskScenario('credit_shock',-.08,0,(0,0,0,0,0),200,.04,0,.04,-.10),
         DeskScenario('vol_spike',-.07,0,(0,0,0,0,0),20,.15,.10),
         DeskScenario('usd_shock',0,-.10),
         DeskScenario('correlation_breakdown',-.03,0,(0,0,0,0,0),0,.02,-.30)]

def evaluate_scenario(marks,market,book,scenario):
    values=[scenario.equity,scenario.fx,*scenario.rates,scenario.credit,scenario.volatility,scenario.correlation,scenario.haircut,scenario.collateral]
    if not np.isfinite(values).all() or min(scenario.equity,scenario.fx,scenario.collateral)<=-1:
        raise ValueError('Invalid scenario shocks')
    rows=[]
    for r in marks.itertuples():
        rates=float(np.interp(r.maturity,[1,2,5,10,30],scenario.rates))
        factors={'equity':0.,'rates':0.,'credit':0.,'volatility':0.,'correlation':0.,'fx':0.}
        if r.asset_class=='Equity': factors['equity']=r.market_value*scenario.equity
        elif r.asset_class=='Bond':
            factors['rates']=-r.dv01*rates+.5*r.convexity*r.market_value*(rates/1e4)**2
            factors['credit']=-r.cs01*scenario.credit
            if r.cs01:
                factors['credit']+=.5*r.convexity*r.market_value*((rates+scenario.credit)**2-rates**2)/1e8
        elif r.asset_class=='Option':
            scale=r.quantity*r.multiplier*market.fx[r.currency]/market.fx[book.base_currency]
            rate=market.rates[r.currency]
            def price(s,v,rr): return black_scholes_price(r.option_type,s,r.strike,r.maturity,rr,v)*scale
            base=price(r.spot,r.volatility,rate)
            spot=price(r.spot*(1+scenario.equity),r.volatility,rate)
            vol=price(r.spot*(1+scenario.equity),max(.0001,r.volatility+scenario.volatility),rate)
            final=price(r.spot*(1+scenario.equity),max(.0001,r.volatility+scenario.volatility),rate+rates/1e4)
            factors.update(equity=spot-base,volatility=vol-spot,rates=final-vol)
        elif r.asset_class=='Structured':
            from dataclasses import replace
            from services.structured import contract_for
            from engines.structured_risk_engine import value_note
            inputs,ratios,product,memory,_=contract_for(r._asdict(),market,book.structured_terms)
            scale=r.quantity*r.multiplier*market.fx[r.currency]/market.fx[book.base_currency]
            def val(i,rr):return value_note(i,tuple(rr),product,memory)['summary']['value']*scale
            base=val(inputs,ratios);shocked=tuple(x*(1+scenario.equity) for x in ratios)
            spot=val(inputs,shocked)
            vi=replace(inputs,volatilities=tuple(max(.001,v+scenario.volatility) for v in inputs.volatilities))
            vol=val(vi,shocked);ri=replace(vi,risk_free_rate=vi.risk_free_rate+rates/1e4);rate_value=val(ri,shocked)
            lower=-1/(len(ratios)-1)+.0001 if len(ratios)>1 else -.99
            ci=replace(ri,correlation=float(np.clip(ri.correlation+scenario.correlation,lower,.9999)))
            final=val(ci,shocked)
            factors.update(equity=spot-base,volatility=vol-spot,rates=rate_value-vol,correlation=final-rate_value)
        if r.currency!=book.base_currency:
            factors['fx']=(r.market_value+sum(factors.values()))*scenario.fx
        rows.append({'id':r.id,'asset_class':r.asset_class,**factors,'pnl':sum(factors.values())})
    frame=pd.DataFrame(rows)
    collateral=marks.loc[marks.id==book.collateral_id,'market_value'].sum()
    stressed_collateral=collateral*(1+scenario.collateral)
    eligible=stressed_collateral*(1-np.clip(book.repo_haircut+scenario.haircut,0,.99))
    liquidity=max(0.,book.repo_cash-eligible) if book.repo_cash else 0.
    return {'positions':frame,'pnl':float(frame.pnl.sum()),'liquidity':float(liquidity),
            'by_factor':frame[['equity','rates','credit','volatility','correlation','fx']].sum(),
            'by_asset_class':frame.groupby('asset_class').pnl.sum()}

def scenario_summary(marks,market,book):
    return pd.DataFrame([{'scenario':s.name,**{k:v for k,v in evaluate_scenario(marks,market,book,s).items() if k in ('pnl','liquidity')}} for s in PRESETS])
